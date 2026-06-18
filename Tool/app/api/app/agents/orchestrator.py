"""Agent orchestration — runs the governed advisory pipeline.

Order: anomaly → remediation (proposal only) → narrative → circular parsing.
Persists every AgentRun and creates a RemediationProposal that remains 'proposed'
until a Checker approves it. Nothing here mutates calculation inputs or runs.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..calc.types import CarResult
from ..models import CircularChange, Narrative, RemediationProposal
from ..services import audit_service, report_instance_service
from . import (
    anomaly_agent, base, circular_parsing_agent, narrative_agent, remediation_agent,
)


def run_governed_pipeline(db: Session, instance_id: int, result: CarResult,
                          findings: list[dict], actor: str = "system") -> dict:
    summary: dict = {"agent_runs": [], "remediation_proposal_id": None, "narrative_ids": []}

    # 1. anomaly
    anomaly = anomaly_agent.run(result, findings)
    anomaly_run = base.persist(db, instance_id, anomaly)
    summary["agent_runs"].append(anomaly_run.id)

    # 2. remediation (only if an anomaly element was identified)
    has_failure = any(f["status"] == "fail" for f in findings)
    if has_failure and anomaly.output.get("element_code"):
        rem_result, proposal = remediation_agent.run(result, anomaly.output)
        rem_run = base.persist(db, instance_id, rem_result)
        summary["agent_runs"].append(rem_run.id)
        if proposal:
            rp = RemediationProposal(
                agent_run_id=rem_run.id, instance_id=instance_id,
                element_code=proposal["element_code"],
                current_value=float(proposal["current_value"]),
                proposed_value=float(proposal["proposed_value"]),
                rationale=proposal["rationale"], status="proposed",
            )
            db.add(rp)
            db.flush()
            summary["remediation_proposal_id"] = rp.id
            report_instance_service.set_status(db, instance_id, "REMEDIATION", actor=actor)

    # 3. narrative (EN + AR drafts) — overwrite in place, one row per language.
    # Re-creating the narrative refreshes the existing draft (version = revision
    # count) instead of stacking new versions; status resets to 'draft' for re-approval.
    narr_result, narr = narrative_agent.run(result)
    narr_run = base.persist(db, instance_id, narr_result)
    summary["agent_runs"].append(narr_run.id)
    for lang in ("en", "ar"):
        n = (db.query(Narrative).filter(Narrative.instance_id == instance_id,
                                        Narrative.language == lang)
             .order_by(Narrative.version.desc()).first())
        if n is None:
            n = Narrative(instance_id=instance_id, language=lang, version=1)
            db.add(n)
        else:
            n.version = (n.version or 1) + 1
        n.body = narr[lang]
        n.citations = narr["citations"]
        n.confidence = narr["confidence"]
        n.status = "draft"
        db.flush()
        summary["narrative_ids"].append(n.id)

    # 4. circular parsing for CAR-affecting change-log entries
    circulars = (db.query(CircularChange)
                 .filter((CircularChange.affected_reports.like("%Capital Adequacy%")) |
                         (CircularChange.affected_reports.like("%All%"))).all())
    for c in circulars:
        cres = circular_parsing_agent.run({
            "regulator": c.regulator, "standard": c.standard, "description": c.description,
            "affected_elements": c.affected_elements,
        })
        crun = base.persist(db, instance_id, cres)
        summary["agent_runs"].append(crun.id)
        c.impact_analysis = cres.output

    audit_service.log(db, actor=actor, action="run_agent_pipeline", entity_type="report_instance",
                      entity_id=instance_id, instance_id=instance_id, after=summary)
    db.flush()
    return summary
