"""Exception workbench — joins validation failures with AI diagnosis + the
governed remediation trail (root cause, recommendation, maker rationale,
checker decision, comments)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import AgentRun, RemediationProposal, ValidationResult
from ..registry.car_sa01 import elements as reg


def _schedule_of(elements: list[str]) -> str:
    for code in elements:
        e = reg.REGISTRY.get(code)
        if e:
            return e.sheet_name
    return "Summary"


def assemble(db: Session, instance_id: int) -> dict:
    fails = (db.query(ValidationResult)
             .filter(ValidationResult.instance_id == instance_id,
                     ValidationResult.status == "fail").all())
    anomaly = (db.query(AgentRun)
               .filter(AgentRun.instance_id == instance_id, AgentRun.agent_type == "anomaly")
               .order_by(AgentRun.id.desc()).first())
    remediation_run = (db.query(AgentRun)
                       .filter(AgentRun.instance_id == instance_id,
                               AgentRun.agent_type == "remediation")
                       .order_by(AgentRun.id.desc()).first())
    proposals = (db.query(RemediationProposal)
                 .filter(RemediationProposal.instance_id == instance_id)
                 .order_by(RemediationProposal.id.desc()).all())

    root_cause = anomaly.reasoning_summary if anomaly else ""
    recommendation = remediation_run.proposed_action if remediation_run else ""

    def proposal_for(elements: list[str]) -> RemediationProposal | None:
        for p in proposals:
            if p.element_code in elements:
                return p
        return None

    seen_rules: set[str] = set()
    items = []
    for v in fails:
        if v.rule_code in seen_rules:
            continue
        seen_rules.add(v.rule_code)
        p = proposal_for(v.elements or [])
        items.append({
            "rule_code": v.rule_code, "issue": v.message,
            "impacted_schedule": _schedule_of(v.elements or []),
            "impacted_elements": v.elements or [],
            "remediation_hint": v.remediation_hint,
            "ai_root_cause": root_cause, "ai_recommendation": recommendation,
            "proposal": _proposal_dict(p) if p else None,
        })
    return {"exceptions": items, "open": len(items),
            "proposals": [_proposal_dict(p) for p in proposals]}


def _proposal_dict(p: RemediationProposal) -> dict:
    return {"id": p.id, "element_code": p.element_code,
            "current_value": float(p.current_value), "proposed_value": float(p.proposed_value),
            "rationale": p.rationale, "status": p.status,
            "maker_rationale": p.maker_rationale, "checker": p.checker,
            "checker_comment": p.checker_comment}
