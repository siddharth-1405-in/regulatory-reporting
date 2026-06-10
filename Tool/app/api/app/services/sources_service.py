"""Source systems — named enterprise vendors feeding the CAR data foundation."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..models import SourceSystem
from ..registry.car_sa01 import elements as reg
from ..registry.car_sa01 import sources as sources_reg


def ensure_sources(db: Session) -> None:
    existing = {s.code for s in db.query(SourceSystem).all()}
    now = datetime.now(timezone.utc)
    for s in sources_reg.catalogue_dicts():
        if s["code"] in existing:
            continue
        db.add(SourceSystem(
            code=s["code"], name=s["name"], vendor=s["vendor"], category=s["category"],
            used_in_car=s["used_in_car"], steward=s["steward"], coverage=s["coverage"],
            status="connected" if s["used_in_car"] else "available",
            last_ingest_at=now - timedelta(hours=s["freshness_hours"]) if s["used_in_car"] else None,
        ))
    db.flush()


def catalogue(db: Session) -> list[dict]:
    ensure_sources(db)
    rows = db.query(SourceSystem).all()
    out = []
    for s in rows:
        out.append({
            "code": s.code, "name": s.name, "vendor": s.vendor, "category": s.category,
            "status": s.status, "used_in_car": s.used_in_car, "steward": s.steward,
            "coverage": s.coverage,
            "last_ingest_at": s.last_ingest_at.isoformat() if s.last_ingest_at else None,
            "car_elements": sources_reg.car_element_count(s.code),
        })
    # connected/used first, then available
    return sorted(out, key=lambda x: (not x["used_in_car"], x["name"]))


def datasets_for(db: Session, source_code: str) -> list[dict]:
    """CAR elements primarily sourced from the given system."""
    out = []
    for e in reg.INPUT_ELEMENTS:
        src = sources_reg.source_for(e.element_code)
        if src["source_code"] == source_code:
            out.append({"element_code": e.element_code, "label": e.label,
                        "sheet_name": e.sheet_name, "source_field": src["source_field"],
                        "domain": e.source_domain})
    return out
