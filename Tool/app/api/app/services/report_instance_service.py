"""Report instance lifecycle + input value access."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from ..models import ElementValue, ReportInstance, ReportPack
from . import audit_service

STATUS_ORDER = [
    "DRAFT", "INGESTED", "CERTIFYING", "CALCULATED", "VALIDATED",
    "REMEDIATION", "SIGNED_OFF", "EXPORTED",
]


def get_or_create_pack(db: Session) -> ReportPack:
    pack = db.query(ReportPack).filter(ReportPack.code == "CAR-SA-01").one_or_none()
    if pack is None:
        pack = ReportPack(code="CAR-SA-01", name="SAMA Capital Adequacy Return", regulator="SAMA")
        db.add(pack)
        db.flush()
    return pack


def create_instance(db: Session, *, period_label: str, period_end: date,
                    bank_name: str, actor: str = "system") -> ReportInstance:
    pack = get_or_create_pack(db)
    inst = ReportInstance(pack_id=pack.id, period_label=period_label,
                          period_end=period_end, bank_name=bank_name, status="DRAFT")
    db.add(inst)
    db.flush()
    audit_service.log(db, actor=actor, action="create_instance",
                      entity_type="report_instance", entity_id=inst.id,
                      instance_id=inst.id, after={"period": period_label, "bank": bank_name})
    return inst


def get(db: Session, instance_id: int) -> ReportInstance | None:
    return db.get(ReportInstance, instance_id)


def list_instances(db: Session) -> list[ReportInstance]:
    return db.query(ReportInstance).order_by(ReportInstance.created_at.desc()).all()


def set_status(db: Session, instance_id: int, status: str, actor: str = "system") -> None:
    inst = db.get(ReportInstance, instance_id)
    if inst is None:
        return
    before = inst.status
    inst.status = status
    audit_service.log(db, actor=actor, action="set_status", entity_type="report_instance",
                      entity_id=instance_id, instance_id=instance_id,
                      before={"status": before}, after={"status": status})
    db.flush()


def load_raw_inputs(db: Session, instance_id: int) -> dict[str, Decimal]:
    """Latest RAW (system-of-record) value per element_code, ignoring overrides."""
    rows = db.query(ElementValue).filter(ElementValue.instance_id == instance_id).all()
    latest: dict[str, ElementValue] = {}
    for r in rows:
        cur = latest.get(r.element_code)
        if cur is None or r.version > cur.version:
            latest[r.element_code] = r
    return {code: Decimal(str(r.raw_value)) for code, r in latest.items()}


def load_inputs(db: Session, instance_id: int) -> dict[str, Decimal]:
    """Effective input per element. Values are never manually overridden in the
    Data Foundation; the engine always uses the raw system-of-record value, which
    is corrected only through re-ingestion or rule-parameter edits."""
    return load_raw_inputs(db, instance_id)
