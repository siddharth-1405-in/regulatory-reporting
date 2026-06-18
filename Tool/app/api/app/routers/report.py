"""Report Pack API — auto-recompute, schedule sign-off, exceptions."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..registry.car_sa01 import rules as rules_reg
from ..services import (
    calc_service, exceptions_service, remediation_service, report_signoff_service,
)
from ..services.data_layer_service import RolePermissionError

router = APIRouter(prefix="/api/instances/{iid}/report")


class SignoffRequest(BaseModel):
    role: str = "Checker"
    actor: str = "checker"
    comment: str = ""


class MakerActionRequest(BaseModel):
    proposal_id: int
    rationale: str
    alternate_value: float | None = None
    role: str = "Maker"
    actor: str = "maker"


class CheckerDecisionRequest(BaseModel):
    proposal_id: int
    decision: str  # approve | reject
    comment: str = ""
    role: str = "Checker"
    actor: str = "checker"


@router.get("/status")
def status(iid: int, db: Session = Depends(get_db)):
    # auto-recompute the live draft (no explicit Run action)
    calc_service.ensure_current(db, iid, actor="system")
    db.commit()
    run = calc_service.latest_run(db, iid)
    return {
        "report_status": report_signoff_service.report_status(db, iid),
        "metrics": run.results["metrics"] if run else None,
        "flags": run.results["flags"] if run else None,
        "last_computed": run.created_at.isoformat() if run else None,
        "schedules": report_signoff_service.schedule_view(db, iid),
    }


@router.get("/schedule/{key}")
def schedule(iid: int, key: str, db: Session = Depends(get_db)):
    """Per-element detail for a schedule, with business meaning + plain-English rule."""
    calc_service.ensure_current(db, iid, actor="system")
    run = calc_service.latest_run(db, iid)
    db.commit()
    if not run:
        return {"key": key, "lines": [], "available": False}
    name_map = {"S1": "Schedule 1", "S2": "Schedule 2", "S3": "Schedule 3",
                "S4": "Schedule 4", "S5": "Schedule 5", "S6": "Schedule 6"}
    sched_name = name_map.get(key)
    lines = []
    if sched_name and sched_name in run.results["schedules"]:
        for l in run.results["schedules"][sched_name]["lines"]:
            rule = rules_reg.rule_for(l["element_code"])
            lines.append({**l, "business_meaning": rules_reg.business_meaning(l["element_code"]),
                          "computation": rule.get("plain_english", "")})
        totals = run.results["schedules"][sched_name]["totals"]
    else:
        totals = {}
    return {"key": key, "lines": lines, "totals": totals,
            "values": run.results["values"], "available": True}


@router.post("/schedule/{key}/signoff")
def signoff(iid: int, key: str, body: SignoffRequest, db: Session = Depends(get_db)):
    try:
        res = report_signoff_service.signoff(db, iid, key, body.role, body.actor, body.comment)
    except RolePermissionError as e:
        raise HTTPException(409, str(e))
    db.commit()
    return res


@router.get("/exceptions")
def exceptions(iid: int, db: Session = Depends(get_db)):
    calc_service.ensure_current(db, iid, actor="system")
    db.commit()
    return exceptions_service.assemble(db, iid)


@router.post("/exceptions/maker-action")
def maker_action(iid: int, body: MakerActionRequest, db: Session = Depends(get_db)):
    if body.role not in ("Maker", "Admin"):
        raise HTTPException(403, "Maker action requires Maker role")
    try:
        res = remediation_service.maker_action(db, body.proposal_id, body.actor,
                                               body.rationale, body.alternate_value)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return res


@router.post("/exceptions/checker-decision")
def checker_decision(iid: int, body: CheckerDecisionRequest, db: Session = Depends(get_db)):
    if body.role not in ("Checker", "Admin"):
        raise HTTPException(403, "Checker decision requires Checker role")
    try:
        if body.decision == "approve":
            res = remediation_service.approve(db, body.proposal_id, checker=body.actor, comment=body.comment)
        else:
            remediation_service.reject(db, body.proposal_id, checker=body.actor, reason=body.comment)
            res = {"status": "rejected"}
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return res
