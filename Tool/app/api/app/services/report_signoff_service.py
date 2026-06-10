"""Report-side sign-off — schedule (S1–S6) then Summary attestation.

Distinct from Data Foundation certification: data certification gates which
VALUES enter the report; this layer is the report-owner's attestation that each
schedule is correct. A schedule can be signed off only once its underlying data
domains are certified; if certified data later changes (domain invalidated), an
already-signed schedule is shown as 'reopened' until re-attested.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..models import RemediationProposal, ScheduleSignoff, ValidationResult
from . import audit_service, certification_service
from .data_layer_service import RolePermissionError, _require

SCHEDULES = [
    ("Cover", "Cover", []),
    ("S1", "S1 — Regulatory Capital Composition", ["Finance"]),
    ("S2", "S2 — Credit Risk Risk-Weighted Assets", ["Risk"]),
    ("S3", "S3 — Market Risk Capital Charge (Standardised Approach)", ["Risk"]),
    ("S4", "S4 — Operational Risk Capital Charge (Standardised Approach)", ["Finance"]),
    ("S5", "S5 — Capital Buffers & Combined Capital Requirement", ["Finance", "Risk"]),
    ("S6", "S6 — Reconciliation to Published Financial Statements", ["Finance"]),
    ("Summary", "Summary — Capital Adequacy Ratios", ["Finance", "Risk"]),
]
SCHEDULE_KEYS = [k for k, _, _ in SCHEDULES]
LABELS = {k: lbl for k, lbl, _ in SCHEDULES}
DOMAINS = {k: d for k, _, d in SCHEDULES}
_SUB_SCHEDULES = ["S1", "S2", "S3", "S4", "S5", "S6"]


def _now():
    return datetime.now(timezone.utc)


def ensure_signoffs(db: Session, instance_id: int) -> None:
    existing = {s.schedule_key for s in
                db.query(ScheduleSignoff).filter(ScheduleSignoff.instance_id == instance_id).all()}
    for key in SCHEDULE_KEYS:
        if key not in existing:
            db.add(ScheduleSignoff(instance_id=instance_id, schedule_key=key, status="pending"))
    db.flush()


def _data_certified(db: Session, instance_id: int, domains: list[str]) -> bool:
    if not domains:
        return True
    statuses = certification_service.status_map(db, instance_id)
    return all(statuses.get(d) == "Certified" for d in domains)


def _row(db: Session, instance_id: int, key: str) -> ScheduleSignoff:
    return (db.query(ScheduleSignoff)
            .filter(ScheduleSignoff.instance_id == instance_id,
                    ScheduleSignoff.schedule_key == key).one_or_none())


def _effective_status(db: Session, instance_id: int, row: ScheduleSignoff) -> str:
    if row.status == "signed_off" and not _data_certified(db, instance_id, DOMAINS[row.schedule_key]):
        return "reopened"
    return row.status


def schedule_view(db: Session, instance_id: int) -> list[dict]:
    ensure_signoffs(db, instance_id)
    rows = {s.schedule_key: s for s in
            db.query(ScheduleSignoff).filter(ScheduleSignoff.instance_id == instance_id).all()}
    eff = {k: _effective_status(db, instance_id, rows[k]) for k in SCHEDULE_KEYS}
    out = []
    for key in SCHEDULE_KEYS:
        r = rows[key]
        data_ok = _data_certified(db, instance_id, DOMAINS[key])
        if key == "Summary":
            subs_ok = all(eff[s] == "signed_off" for s in _SUB_SCHEDULES)
            can = data_ok and subs_ok
            blocked = "" if can else ("Sign off all schedules first" if not subs_ok else "Underlying data not certified")
        else:
            can = data_ok
            blocked = "" if can else f"Certify {', '.join(DOMAINS[key])} data first"
        out.append({
            "key": key, "label": LABELS[key], "status": eff[key],
            "can_signoff": can and eff[key] != "signed_off", "blocked_reason": blocked,
            "domains": DOMAINS[key],
            "signed_by": r.signed_by, "signed_at": r.signed_at.isoformat() if r.signed_at else None,
            "comment": r.comment,
        })
    return out


def signoff(db: Session, instance_id: int, key: str, role: str, actor: str, comment: str = "") -> dict:
    _require(role, {"Checker", "Admin"}, "sign off the report")
    ensure_signoffs(db, instance_id)
    view = {v["key"]: v for v in schedule_view(db, instance_id)}
    if key not in view:
        raise ValueError("unknown schedule")
    if not view[key]["can_signoff"]:
        raise RolePermissionError(view[key]["blocked_reason"] or "Cannot sign off yet")
    r = _row(db, instance_id, key)
    r.status = "signed_off"
    r.signed_by = actor
    r.signed_at = _now()
    r.comment = comment
    db.flush()
    audit_service.log(db, actor=actor, action="schedule_signoff", entity_type="schedule_signoff",
                      entity_id=key, instance_id=instance_id, after={"comment": comment})
    return {"key": key, "status": "signed_off"}


def report_status(db: Session, instance_id: int) -> str:
    ensure_signoffs(db, instance_id)
    summary = _row(db, instance_id, "Summary")
    if summary and _effective_status(db, instance_id, summary) == "signed_off":
        return "Signed Off"
    open_rem = (db.query(RemediationProposal)
                .filter(RemediationProposal.instance_id == instance_id,
                        RemediationProposal.status == "proposed").count())
    if open_rem:
        return "Remediation"
    fails = (db.query(ValidationResult)
             .filter(ValidationResult.instance_id == instance_id,
                     ValidationResult.status == "fail").count())
    if fails:
        return "Exception"
    return "Draft"
