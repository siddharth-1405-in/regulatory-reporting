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


def _pct(x) -> str:
    try:
        return f"{float(x) * 100:.2f}%"
    except Exception:
        return "—"


def _money(x) -> str:
    try:
        return f"{float(x):,.0f}"
    except Exception:
        return "—"


# Schedule 5 is fully derived (no input elements). Its rows are built from the
# flat values dict produced by calc_schedule_5_buffers, with display formatting
# and plain-English meaning, so it renders like any other schedule in the UI.
_S5_RATE_LINES = [
    ("S5_BUFFER_CCB", "Capital Conservation Buffer (CCB)",
     "Fixed SAMA conservation buffer, as a % of total RWA."),
    ("S5_BUFFER_CCYB", "Countercyclical Capital Buffer (CCyB)",
     "Jurisdictional countercyclical buffer in force, as a % of total RWA."),
    ("S5_BUFFER_DSIB", "D-SIB Surcharge",
     "Domestic systemically-important bank surcharge, as a % of total RWA."),
    ("S5_BUFFER_OTHER", "Other SAMA-prescribed buffers",
     "Any further SAMA-prescribed buffer, as a % of total RWA."),
]


def _schedule5_view(run) -> dict:
    v = run.results.get("values", {})
    flags = run.results.get("flags", {})

    def g(code):
        try:
            return float(v.get(code))
        except Exception:
            return None

    lines = []
    for code, label, comp in _S5_RATE_LINES:
        lines.append({
            "element_code": code, "label": label, "result": g(code),
            "display": _pct(g(code)), "kind": "rate", "derived": True,
            "business_meaning": "Regulatory capital buffer, met with CET1 on top of the 4.50% Pillar 1 minimum.",
            "computation": comp})
    lines.append({
        "element_code": "S5_COMBINED_BUFFER", "label": "Combined Buffer Requirement",
        "result": g("S5_COMBINED_BUFFER"), "display": _pct(g("S5_COMBINED_BUFFER")),
        "kind": "rate", "derived": True, "emphasis": True,
        "business_meaning": "Sum of all applicable buffers that must be met with CET1, above the 4.50% Pillar 1 minimum.",
        "computation": "CCB + CCyB + D-SIB + other buffers."})
    lines.append({
        "element_code": "S5_COMBINED_BUFFER_AMOUNT", "label": "Combined Buffer Requirement (amount)",
        "result": g("S5_COMBINED_BUFFER_AMOUNT"), "display": _money(g("S5_COMBINED_BUFFER_AMOUNT")),
        "kind": "amount", "derived": True,
        "business_meaning": "Combined buffer requirement translated into an absolute CET1 amount.",
        "computation": "Combined buffer rate × total RWA."})
    lines.append({
        "element_code": "S5_CET1_AVAILABLE_FOR_BUFFERS", "label": "CET1 available to meet buffers",
        "result": g("S5_CET1_AVAILABLE_FOR_BUFFERS"), "display": _pct(g("S5_CET1_AVAILABLE_FOR_BUFFERS")),
        "kind": "ratio", "derived": True,
        "business_meaning": "CET1 ratio in excess of the 4.50% Pillar 1 CET1 minimum, available to meet buffers.",
        "computation": "CET1 ratio − 4.50% Pillar 1 CET1 minimum."})
    lines.append({
        "element_code": "S5_CET1_SURPLUS", "label": "CET1 surplus / (deficit) over combined requirement",
        "result": g("S5_CET1_SURPLUS"), "display": _pct(g("S5_CET1_SURPLUS")),
        "kind": "ratio", "derived": True, "emphasis": True,
        "business_meaning": "Headroom (or shortfall) of CET1 over the combined buffer — the binding test for capital distributions.",
        "computation": "CET1 available for buffers − combined buffer requirement."})
    for code, label, minimum, comp in [
        ("S5_CET1_SURPLUS_P1", "CET1 surplus over Pillar 1 minimum", "4.50%", "CET1 ratio − 4.50%."),
        ("S5_TIER1_SURPLUS_P1", "Tier 1 surplus over Pillar 1 minimum", "6.00%", "Tier 1 ratio − 6.00%."),
        ("S5_TOTAL_SURPLUS_P1", "Total capital surplus over Pillar 1 minimum", "8.00%", "Total capital ratio − 8.00%."),
    ]:
        lines.append({
            "element_code": code, "label": label, "result": g(code), "display": _pct(g(code)),
            "kind": "ratio", "derived": True,
            "business_meaning": f"Headroom of the ratio over its {minimum} Basel III / SAMA Pillar 1 minimum.",
            "computation": comp})
    return {
        "key": "S5", "lines": lines, "totals": {}, "values": v, "available": True,
        "distribution_band": flags.get("distribution_band"),
        "max_dividend_payout": flags.get("max_dividend_payout"),
    }


@router.get("/schedule/{key}")
def schedule(iid: int, key: str, db: Session = Depends(get_db)):
    """Per-element detail for a schedule, with business meaning + plain-English rule."""
    calc_service.ensure_current(db, iid, actor="system")
    run = calc_service.latest_run(db, iid)
    db.commit()
    if not run:
        return {"key": key, "lines": [], "available": False}
    if key == "S5":
        return _schedule5_view(run)
    name_map = {"S1": "Schedule 1", "S2": "Schedule 2", "S3": "Schedule 3",
                "S4": "Schedule 4", "S6": "Schedule 6"}
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
