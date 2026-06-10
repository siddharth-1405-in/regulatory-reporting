"""Remediation approval — the Checker gate.

An agent's RemediationProposal cannot change report state on its own. A Checker
approves it here, which: applies the corrected value, re-certifies the owning
domain (the Checker is attesting to the corrected figure), and recalculates the
return. Rejection leaves the figure unchanged.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from ..models import AgentRun, RemediationProposal
from . import (
    audit_service, calc_service, certification_service, ingestion_service,
    ownership_service,
)


def _now():
    return datetime.now(timezone.utc)


def list_for_instance(db: Session, instance_id: int) -> list[RemediationProposal]:
    return (db.query(RemediationProposal)
            .filter(RemediationProposal.instance_id == instance_id)
            .order_by(RemediationProposal.id.desc()).all())


def maker_action(db: Session, proposal_id: int, maker: str, rationale: str,
                 alternate_value: float | None = None) -> dict:
    """Maker either accepts the AI recommendation or proposes an alternate
    value/action. Stays pending until a Checker decides."""
    rp = db.get(RemediationProposal, proposal_id)
    if rp is None or rp.status != "proposed":
        raise ValueError("proposal not actionable")
    rp.maker_rationale = rationale
    rp.maker = maker
    if alternate_value is not None:
        rp.proposed_value = float(alternate_value)
    db.flush()
    audit_service.log(db, actor=maker, action="exception_maker_action",
                      entity_type="remediation_proposal", entity_id=rp.id,
                      instance_id=rp.instance_id,
                      after={"rationale": rationale, "alternate": alternate_value})
    return {"id": rp.id, "maker_rationale": rp.maker_rationale,
            "proposed_value": float(rp.proposed_value)}


def approve(db: Session, proposal_id: int, checker: str, comment: str = "") -> dict:
    rp = db.get(RemediationProposal, proposal_id)
    if rp is None:
        raise ValueError("proposal not found")
    if rp.status != "proposed":
        raise ValueError(f"proposal already {rp.status}")

    rp.status = "approved"
    rp.checker = checker
    rp.checker_comment = comment
    rp.decided_at = _now()
    # link agent run status
    run = db.get(AgentRun, rp.agent_run_id)
    if run:
        run.status = "approved"
        run.approved_by = checker

    audit_service.log(db, actor=checker, action="approve_remediation",
                      entity_type="remediation_proposal", entity_id=rp.id,
                      instance_id=rp.instance_id,
                      before={"value": float(rp.current_value)},
                      after={"value": float(rp.proposed_value)})

    # apply the corrected value (invalidates the owning domain's certification)
    ingestion_service.update_value(db, instance_id=rp.instance_id,
                                   element_code=rp.element_code,
                                   value=Decimal(str(rp.proposed_value)), actor=checker)

    # Checker attests to the corrected figure -> re-certify the owning domain
    domain = ownership_service.domain_for_element(rp.element_code)
    if domain:
        certification_service.certify(db, rp.instance_id, domain, actor=checker)

    # recalculate with the gate enforced
    run, result, findings = calc_service.run_calculation(db, rp.instance_id, actor=checker)
    db.flush()
    return {"calc_run_id": run.id, "buffer_status": result.flags.get("buffer_status"),
            "failing_rules": [f["rule_code"] for f in findings if f["status"] == "fail"]}


def reject(db: Session, proposal_id: int, checker: str, reason: str = "") -> None:
    rp = db.get(RemediationProposal, proposal_id)
    if rp is None or rp.status != "proposed":
        raise ValueError("proposal not actionable")
    rp.status = "rejected"
    rp.checker = checker
    rp.checker_comment = reason
    rp.decided_at = _now()
    run = db.get(AgentRun, rp.agent_run_id)
    if run:
        run.status = "rejected"
        run.approved_by = checker
    audit_service.log(db, actor=checker, action="reject_remediation",
                      entity_type="remediation_proposal", entity_id=rp.id,
                      instance_id=rp.instance_id, after={"reason": reason})
    db.flush()
