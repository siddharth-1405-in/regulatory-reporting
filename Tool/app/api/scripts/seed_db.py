"""Seed a realistic CAR-SA-01 demo instance with the Schedule 2 anomaly.

Run:  python -m scripts.seed_db
Creates the schema (if needed), seeds the report pack, ownership assignments and
circular change log from the reference workbooks, then a Q4-2025 instance loaded
with synthetic data containing the seeded Schedule 2 corporate-exposure error.
Certifies Finance + Risk, runs the deterministic calculation, and (if the agents
module is available) runs the governed agents leaving a remediation proposal
pending Checker approval.
"""
from __future__ import annotations

from datetime import date

from openpyxl import load_workbook

from app.core.config import OWNERSHIP_MATRIX
from app.core.db import Base, SessionLocal, engine
from app.models import CanonicalElement, CircularChange, ReportInstance
from app.registry.car_sa01 import elements as reg
from app.registry.car_sa01.sample_data import apply_schedule2_anomaly, baseline_inputs
from app.services import (
    calc_service, certification_service, data_layer_service, dq_service,
    ingestion_service, ownership_service, report_instance_service,
    report_signoff_service, sources_service,
)


def seed_canonical_elements(db):
    if db.query(CanonicalElement).count():
        return
    for e in reg.ALL_ELEMENTS:
        db.add(CanonicalElement(element_code=e.element_code, label=e.label,
                                sheet_name=e.sheet_name, section_name=e.section_name,
                                source_domain=e.source_domain, source_type=e.source_type,
                                lineage_level=e.lineage_level))
    db.flush()


def seed_circular_changes(db):
    if db.query(CircularChange).count():
        return
    wb = load_workbook(OWNERSHIP_MATRIX, data_only=True)
    ws = wb["Regulatory Change Log"]
    rows = list(ws.iter_rows(values_only=True))
    header_idx = next(i for i, r in enumerate(rows)
                      if r and "Change Description" in [str(c) for c in r if c])
    hdr = [str(c).strip() if c else "" for c in rows[header_idx]]
    col = {n: i for i, n in enumerate(hdr)}
    for r in rows[header_idx + 1:]:
        if not r or not r[col["Regulator"]]:
            continue
        db.add(CircularChange(
            regulator=str(r[col["Regulator"]]),
            standard=str(r[col["Standard / Circular"]] or ""),
            description=str(r[col["Change Description"]] or ""),
            affected_reports=str(r[col["Affected Reports"]] or ""),
            affected_elements=str(r[col["Affected Data Elements"]] or ""),
            action_required=str(r[col["Action Required"]] or ""),
            owner=str(r[col["Owner"]] or ""),
            target_date=str(r[col["Target Date"]] or ""),
            status=str(r[col["Status"]] or "Not Started"),
        ))
    db.flush()


def main(reset: bool = True):
    if reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        report_instance_service.get_or_create_pack(db)
        seed_canonical_elements(db)
        ownership_service.seed_assignments(db)
        sources_service.ensure_sources(db)
        seed_circular_changes(db)

        inst = report_instance_service.create_instance(
            db, period_label="Q4 2025", period_end=date(2025, 12, 31),
            bank_name="Tadawul National Bank (demo)", actor="seed")

        # synthetic data WITH the seeded Schedule 2 anomaly
        data = apply_schedule2_anomaly(baseline_inputs())
        finance = {c: v for c, v in data.items()
                   if ownership_service.domain_for_element(c) == "Finance"}
        risk = {c: v for c, v in data.items()
                if ownership_service.domain_for_element(c) == "Risk"}

        ingestion_service.ingest_values(db, instance_id=inst.id, domain="Finance",
                                        source_label="GL / Core Banking (synthetic)",
                                        values=finance, actor="finance.maker")
        ingestion_service.ingest_values(db, instance_id=inst.id, domain="Risk",
                                        source_label="Risk Engine (synthetic)",
                                        values=risk, actor="risk.maker")
        report_instance_service.set_status(db, inst.id, "INGESTED", actor="seed")

        all_inputs = report_instance_service.load_inputs(db, inst.id)
        dq_service.run(db, inst.id, all_inputs)

        # Leave the instance in the maker→checker STARTING state: data is ingested
        # and quality-checked, but NOT yet certified. Element governance starts at
        # 'draft' (ready for submission); the calculation gate is closed. The demo
        # then drives the full governed workflow end to end:
        #   Maker submits → Checker signs off → domain certifies → the draft
        #   auto-computes (calc + governed agents) and the seeded Schedule 2 anomaly
        #   surfaces the buffer breach + a pending remediation proposal.
        data_layer_service.ensure_governance(db, inst.id)      # draft rows
        report_signoff_service.ensure_signoffs(db, inst.id)
        db.commit()

        summary = data_layer_service.status_summary(db, inst.id)
        print("\n=== CAR-SA-01 demo instance seeded (Draft - pending sign-off) ===")
        print(f"  instance_id    : {inst.id}  ({inst.period_label})")
        print(f"  element status : {summary}")
        print("  next step      : Data Foundation -> Maker 'Submit for sign-off' ->")
        print("                   Checker 'Sign-off' -> report auto-computes")
        print("                   (Schedule 2 anomaly -> buffer breach -> remediation).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
