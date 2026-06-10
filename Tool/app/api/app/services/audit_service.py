"""Append-only audit log. Every material state change routes through here."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..models import AuditLog


def _jsonable(v: Any) -> Any:
    from decimal import Decimal
    if isinstance(v, dict):
        return {k: _jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    if isinstance(v, Decimal):
        return float(v)
    return v


def log(db: Session, *, actor: str, action: str, entity_type: str,
        entity_id: str | int = "", instance_id: int | None = None,
        before: dict | None = None, after: dict | None = None) -> AuditLog:
    entry = AuditLog(
        actor=actor, action=action, entity_type=entity_type,
        entity_id=str(entity_id), instance_id=instance_id,
        before=_jsonable(before or {}), after=_jsonable(after or {}),
    )
    db.add(entry)
    db.flush()
    return entry


def for_instance(db: Session, instance_id: int) -> list[AuditLog]:
    return (db.query(AuditLog)
            .filter(AuditLog.instance_id == instance_id)
            .order_by(AuditLog.ts.desc()).all())
