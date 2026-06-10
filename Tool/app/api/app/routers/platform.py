"""Platform-level API — command center metrics and report pack registry."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..models import RemediationProposal, ReportInstance, ValidationResult
from ..services import (
    calc_service, certification_service, report_signoff_service, sources_service,
)

router = APIRouter(prefix="/api/platform")

# Report pack registry — CAR-SA-01 is the active pack; others are recognised
# from the ownership matrix / regulatory landscape but not yet implemented.
PACKS = [
    {"code": "CAR-SA-01", "name": "Capital Adequacy Return", "regulator": "SAMA",
     "frequency": "Quarterly", "status": "active", "schedules": 6},
    {"code": "LCR", "name": "Liquidity Coverage Ratio", "regulator": "SAMA/CBUAE",
     "frequency": "Daily", "status": "planned", "schedules": 0},
    {"code": "NSFR", "name": "Net Stable Funding Ratio", "regulator": "SAMA/CBUAE",
     "frequency": "Monthly", "status": "planned", "schedules": 0},
    {"code": "LE", "name": "Large Exposures Return", "regulator": "SAMA/CBUAE",
     "frequency": "Monthly", "status": "planned", "schedules": 0},
    {"code": "ORR", "name": "Operational Risk Return", "regulator": "SAMA/CBUAE",
     "frequency": "Quarterly", "status": "planned", "schedules": 0},
    {"code": "SHARIA", "name": "Sharia Compliance Report", "regulator": "SSB/AAOIFI",
     "frequency": "Monthly", "status": "planned", "schedules": 0},
]


@router.get("/packs")
def packs():
    return PACKS


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    instances = db.query(ReportInstance).order_by(ReportInstance.created_at.desc()).all()
    rows = []
    uncertified_data = ready_for_preview = signed_off = in_remediation = 0
    req_domains = sorted(certification_service.ownership_service.required_domains())

    for inst in instances:
        run = calc_service.latest_run(db, inst.id)
        fails = (db.query(ValidationResult)
                 .filter(ValidationResult.instance_id == inst.id,
                         ValidationResult.status == "fail").count())
        allowed, blocking = certification_service.is_calc_allowed(db, inst.id)
        open_rem = (db.query(RemediationProposal)
                    .filter(RemediationProposal.instance_id == inst.id,
                            RemediationProposal.status == "proposed").count())
        flags = run.results.get("flags") if run else None
        rstatus = report_signoff_service.report_status(db, inst.id)

        certs = certification_service.status_map(db, inst.id)
        data_ready = round(100 * sum(1 for d in req_domains if certs.get(d) == "Certified")
                           / max(1, len(req_domains)))
        scheds = report_signoff_service.schedule_view(db, inst.id)
        report_ready = round(100 * sum(1 for s in scheds if s["status"] == "signed_off")
                             / max(1, len(scheds)))

        if not allowed:
            uncertified_data += 1
        if run is not None and fails == 0 and rstatus != "Signed Off":
            ready_for_preview += 1
        if rstatus == "Signed Off":
            signed_off += 1
        if rstatus == "Remediation" or open_rem > 0:
            in_remediation += 1

        rows.append({
            "id": inst.id, "pack": "CAR-SA-01", "period_label": inst.period_label,
            "period_end": inst.period_end.isoformat(), "bank_name": inst.bank_name,
            "status": inst.status, "report_status": rstatus,
            "buffer_status": flags.get("buffer_status") if flags else None,
            "failing_rules": fails, "blocking_domains": blocking, "open_remediations": open_rem,
            "data_readiness": data_ready, "report_readiness": report_ready,
        })

    src = sources_service.catalogue(db)
    db.commit()
    source_health = {
        "connected": sum(1 for s in src if s["status"] == "connected"),
        "used_in_car": sum(1 for s in src if s["used_in_car"]),
        "total": len(src),
        "degraded": sum(1 for s in src if s["status"] == "degraded"),
    }

    return {
        "metrics": {
            "active_reports": len(instances),
            "uncertified_data": uncertified_data, "in_remediation": in_remediation,
            "ready_for_preview": ready_for_preview, "signed_off": signed_off,
            "active_packs": sum(1 for p in PACKS if p["status"] == "active"),
        },
        "source_health": source_health, "sources": src,
        "packs": PACKS, "instances": rows,
    }
