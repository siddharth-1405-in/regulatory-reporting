"""Ingestion of domain input data + value mutation with certification impact."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from ..models import ElementValue, IngestionBatch
from ..registry.car_sa01 import elements as reg
from . import audit_service, certification_service


def ingest_values(db: Session, *, instance_id: int, domain: str, source_label: str,
                  values: dict[str, Decimal], actor: str = "system") -> IngestionBatch:
    """Write a batch of input values for a domain (versioned). Invalidates any
    certifications affected by the changed elements (governance invariant)."""
    batch = IngestionBatch(instance_id=instance_id, domain=domain,
                           source_label=source_label, row_count=len(values))
    db.add(batch)

    changed: list[str] = []
    for code, val in values.items():
        if code not in reg.REGISTRY:
            continue
        prev = (db.query(ElementValue)
                .filter(ElementValue.instance_id == instance_id,
                        ElementValue.element_code == code)
                .order_by(ElementValue.version.desc()).first())
        version = (prev.version + 1) if prev else 1
        db.add(ElementValue(instance_id=instance_id, element_code=code,
                            raw_value=float(val), version=version, updated_by=actor))
        changed.append(code)

    db.flush()
    audit_service.log(db, actor=actor, action="ingest", entity_type="ingestion_batch",
                      entity_id=batch.id, instance_id=instance_id,
                      after={"domain": domain, "elements": changed[:50], "count": len(changed)})
    certification_service.invalidate_for_elements(db, instance_id, changed, actor=actor)
    return batch


def update_value(db: Session, *, instance_id: int, element_code: str, value: Decimal,
                 actor: str) -> None:
    """Single-cell edit (e.g. applying an approved remediation)."""
    prev = (db.query(ElementValue)
            .filter(ElementValue.instance_id == instance_id,
                    ElementValue.element_code == element_code)
            .order_by(ElementValue.version.desc()).first())
    version = (prev.version + 1) if prev else 1
    before = float(prev.raw_value) if prev else None
    db.add(ElementValue(instance_id=instance_id, element_code=element_code,
                        raw_value=float(value), version=version, updated_by=actor))
    db.flush()
    audit_service.log(db, actor=actor, action="update_value", entity_type="element_value",
                      entity_id=element_code, instance_id=instance_id,
                      before={"value": before}, after={"value": float(value)})
    certification_service.invalidate_for_elements(db, instance_id, [element_code], actor=actor)
