"""HTTP API for the CAR reporting platform."""
from __future__ import annotations

import re
from decimal import Decimal

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..models import (
    AgentRun, Certification, CircularChange, DQFinding, Narrative,
    OwnershipAssignment, RemediationProposal, ValidationResult,
)
from ..registry.car_sa01 import elements as reg
from ..schemas.schemas import (
    ActorRequest, CertifyRequest, CreateInstance, IngestRequest, InstanceOut,
    SetParameter,
)
from ..services import (
    audit_service, calc_service, certification_service, config_service,
    dq_service, export_service, ingestion_service, lineage_service,
    ownership_service, remediation_service, report_instance_service,
)

router = APIRouter(prefix="/api")


# ---- meta / registry --------------------------------------------------------
@router.get("/health")
def health():
    from ..core.config import settings
    return {"status": "ok", "ai_enabled": settings.ai_enabled}


@router.get("/registry")
def registry():
    sheets: dict[str, list] = {}
    for e in reg.ALL_ELEMENTS:
        sheets.setdefault(e.sheet_name, []).append({
            "element_code": e.element_code, "label": e.label, "section": e.section_name,
            "source_domain": e.source_domain, "source_type": e.source_type,
            "lineage_level": e.lineage_level, "is_input": e.is_input,
            "rate": float(e.rate) if e.rate is not None else None,
            "ccf": float(e.ccf) if e.ccf is not None else None,
        })
    return {"sheets": sheets, "required_domains": sorted(ownership_service.required_domains())}


@router.get("/ownership")
def ownership(db: Session = Depends(get_db)):
    rows = db.query(OwnershipAssignment).all()
    return {
        "assignments": [{"data_element": a.data_element, "domain": a.domain, "steward": a.steward,
                         "source_system": a.source_system, "frequency": a.frequency,
                         "ai_action": a.ai_action} for a in rows],
        "required_domains": sorted(ownership_service.required_domains()),
    }


# ---- data-foundation template -----------------------------------------------
@router.get("/data-foundation/template")
def download_template():
    """Generate and return a CAR-SA-01 data intake template Excel file."""
    import io
    from openpyxl import Workbook
    wb = Workbook()

    # Sheet 1: Data Template
    ws = wb.active
    ws.title = "Data Template"
    headers = ["Data Element ID", "Data Element Name", "Value", "Notes"]
    ws.append(headers)
    for col, _ in enumerate(headers, 1):
        ws.column_dimensions[ws.cell(1, col).column_letter].width = 30

    for e in reg.ALL_ELEMENTS:
        if e.is_input:
            ws.append([e.element_code, e.label, "", ""])

    # Sheet 2: Instructions
    inst_ws = wb.create_sheet("Instructions")
    inst_ws.column_dimensions["A"].width = 80
    instructions = [
        ["CAR-SA-01 Data Intake Template — Fill Guide"],
        [""],
        ["HOW TO COMPLETE THIS TEMPLATE"],
        ["1. Use the 'Data Template' sheet to enter values."],
        ["2. Do not change column headers or the Data Element ID column."],
        ["3. Enter numeric values in the 'Value' column (SAR '000 unless noted)."],
        ["4. Use the 'Notes' column for any clarifications or source references."],
        ["5. Save as .xlsx and upload using the 'Upload completed template' button."],
        [""],
        ["COLUMN GUIDE"],
        ["Data Element ID  : System identifier — do not edit."],
        ["Data Element Name: Business label for reference only."],
        ["Value            : Your reported figure (SAR '000)."],
        ["Notes            : Optional — source system, date, or comments."],
        [""],
        ["Supported file formats: .xlsx"],
    ]
    for row in instructions:
        inst_ws.append(row)

    buf = io.BytesIO()
    wb.save(buf)
    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=CAR_SA01_DataTemplate.xlsx"},
    )


def _parse_amount(raw) -> Decimal | None:
    """Parse an uploaded cell into a Decimal. Thousands commas and surrounding
    whitespace are allowed (e.g. '1,250,000' or ' 1250000 '); letters, currency
    symbols and other special characters are rejected. Returns None if invalid."""
    if isinstance(raw, (int, float, Decimal)):
        try:
            return Decimal(str(raw))
        except Exception:
            return None
    s = str(raw).strip().replace(",", "").replace(" ", "")
    if not s:
        return None
    # optional leading minus, digits, optional single decimal part
    if not re.fullmatch(r"-?\d+(\.\d+)?", s):
        return None
    try:
        return Decimal(s)
    except Exception:
        return None


@router.post("/instances/{iid}/ingest/upload")
async def ingest_upload(iid: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Accept an uploaded template Excel file and ingest the element values."""
    import io
    from openpyxl import load_workbook
    content = await file.read()
    try:
        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(min_row=2, values_only=True))
    except Exception as exc:
        raise HTTPException(400, f"Cannot parse file: {exc}")

    values: dict[str, Decimal] = {}
    errors: list[str] = []
    seen: set[str] = set()
    for r in rows:
        if not r or r[0] is None:
            continue
        code = str(r[0]).strip()
        raw = r[2]
        if raw is None or str(raw).strip() == "":
            continue
        if code not in reg.REGISTRY:
            errors.append(f"Unknown element: {code}")
            continue
        # duplicate data element rows must not silently overwrite each other
        if code in seen:
            errors.append(f"Duplicate data element: {code} (only the first occurrence is used)")
            continue
        seen.add(code)
        parsed = _parse_amount(raw)
        if parsed is None:
            errors.append(f"Non-standard value for {code}: '{raw}' (numbers only; commas allowed)")
            continue
        values[code] = parsed

    if not values and errors:
        raise HTTPException(400, {"message": "No valid values found", "errors": errors})

    batch = ingestion_service.ingest_values(
        db, instance_id=iid, domain="Upload",
        source_label=file.filename or "template_upload",
        values=values, actor="maker",
    )
    report_instance_service.set_status(db, iid, "INGESTED", actor="maker")
    db.commit()
    return {"batch_id": batch.id, "ingested": len(values), "skipped": len(errors), "errors": errors}


# ---- instances --------------------------------------------------------------
@router.post("/instances", response_model=InstanceOut)
def create_instance(body: CreateInstance, db: Session = Depends(get_db)):
    inst = report_instance_service.create_instance(
        db, period_label=body.period_label, period_end=body.period_end,
        bank_name=body.bank_name, actor=body.actor)
    certification_service.ensure_domains(db, inst.id)
    db.commit()
    return inst


@router.get("/instances", response_model=list[InstanceOut])
def list_instances(db: Session = Depends(get_db)):
    return report_instance_service.list_instances(db)


@router.get("/instances/{iid}")
def get_instance(iid: int, db: Session = Depends(get_db)):
    inst = report_instance_service.get(db, iid)
    if not inst:
        raise HTTPException(404, "instance not found")
    run = calc_service.latest_run(db, iid)
    allowed, blocking = certification_service.is_calc_allowed(db, iid)
    return {
        "instance": InstanceOut.model_validate(inst).model_dump(mode="json"),
        "certifications": certification_service.status_map(db, iid),
        "calc_allowed": allowed, "blocking_domains": blocking,
        "metrics": run.results["metrics"] if run else None,
        "flags": run.results["flags"] if run else None,
        "calc_run_id": run.id if run else None,
    }


@router.post("/instances/{iid}/ingest")
def ingest(iid: int, body: IngestRequest, db: Session = Depends(get_db)):
    vals = {k: Decimal(str(v)) for k, v in body.values.items()}
    batch = ingestion_service.ingest_values(db, instance_id=iid, domain=body.domain,
                                            source_label=body.source_label, values=vals,
                                            actor=body.actor)
    report_instance_service.set_status(db, iid, "INGESTED", actor=body.actor)
    db.commit()
    return {"batch_id": batch.id, "ingested": len(vals)}


@router.get("/instances/{iid}/inputs")
def get_inputs(iid: int, db: Session = Depends(get_db)):
    return {k: float(v) for k, v in report_instance_service.load_inputs(db, iid).items()}


@router.post("/instances/{iid}/dq/run")
def run_dq(iid: int, db: Session = Depends(get_db)):
    inputs = report_instance_service.load_inputs(db, iid)
    findings = dq_service.run(db, iid, inputs)
    db.commit()
    return [{"severity": f.severity, "message": f.message, "element_code": f.element_code}
            for f in findings]


@router.get("/instances/{iid}/dq")
def get_dq(iid: int, db: Session = Depends(get_db)):
    rows = db.query(DQFinding).filter(DQFinding.instance_id == iid).all()
    return [{"severity": f.severity, "message": f.message, "element_code": f.element_code}
            for f in rows]


# ---- certification ----------------------------------------------------------
@router.get("/instances/{iid}/certifications")
def certifications(iid: int, db: Session = Depends(get_db)):
    rows = db.query(Certification).filter(Certification.instance_id == iid).all()
    allowed, blocking = certification_service.is_calc_allowed(db, iid)
    return {
        "domains": [{"domain": c.domain, "status": c.status, "certified_by": c.certified_by,
                     "certified_at": c.certified_at.isoformat() if c.certified_at else None,
                     "reason": c.reason,
                     "elements": ownership_service.elements_for_domain(c.domain)} for c in rows],
        "calc_allowed": allowed, "blocking_domains": blocking,
    }


@router.post("/instances/{iid}/certifications/{domain}/certify")
def certify(iid: int, domain: str, body: CertifyRequest, db: Session = Depends(get_db)):
    cert = certification_service.certify(db, iid, domain, actor=body.actor)
    db.commit()
    return {"domain": cert.domain, "status": cert.status}


# ---- calculation / validation / lineage -------------------------------------
@router.post("/instances/{iid}/calculate")
def calculate(iid: int, db: Session = Depends(get_db)):
    try:
        run, result, findings = calc_service.run_calculation(db, iid, actor="maker")
    except calc_service.CertificationGateError as e:
        raise HTTPException(409, detail={"error": "certification_gate", "blocking_domains": e.blocking})
    db.commit()
    return {"calc_run_id": run.id, "metrics": run.results["metrics"],
            "flags": run.results["flags"],
            "failing_rules": [f["rule_code"] for f in findings if f["status"] == "fail"]}


@router.get("/instances/{iid}/calc")
def get_calc(iid: int, db: Session = Depends(get_db)):
    run = calc_service.latest_run(db, iid)
    if not run:
        raise HTTPException(404, "no calculation yet")
    return run.results


@router.get("/instances/{iid}/validation")
def validation(iid: int, db: Session = Depends(get_db)):
    rows = db.query(ValidationResult).filter(ValidationResult.instance_id == iid).all()
    return [{"rule_code": r.rule_code, "status": r.status, "message": r.message,
             "elements": r.elements, "remediation_hint": r.remediation_hint} for r in rows]


@router.get("/instances/{iid}/lineage")
def lineage(iid: int, code: str, db: Session = Depends(get_db)):
    return {"code": code, "upstream": lineage_service.trace_upstream(db, iid, code),
            "label": reg.REGISTRY[code].label if code in reg.REGISTRY else code}


# ---- agents / remediation / narrative ---------------------------------------
def _agent_dict(r: AgentRun) -> dict:
    return {"id": r.id, "agent_type": r.agent_type, "reasoning_summary": r.reasoning_summary,
            "confidence": float(r.confidence), "evidence_used": r.evidence_used,
            "impacted_metrics": r.impacted_metrics, "proposed_action": r.proposed_action,
            "approval_required": r.approval_required, "prompt_version": r.prompt_version,
            "model_version": r.model_version, "status": r.status, "output": r.output,
            "created_at": r.created_at.isoformat()}


@router.post("/instances/{iid}/agents/run")
def run_agents(iid: int, db: Session = Depends(get_db)):
    run = calc_service.latest_run(db, iid)
    if not run:
        raise HTTPException(409, "calculate before running agents")
    from ..agents import orchestrator
    from ..calc import engine
    inputs = report_instance_service.load_inputs(db, iid)
    params, buffers = config_service.get_params_and_buffers(db)
    result = engine.compute(inputs, params=params, buffers=buffers)
    findings = [{"rule_code": v.rule_code, "status": v.status, "message": v.message}
                for v in db.query(ValidationResult).filter(ValidationResult.instance_id == iid).all()]
    summary = orchestrator.run_governed_pipeline(db, iid, result, findings, actor="maker")
    db.commit()
    return summary


@router.get("/instances/{iid}/agents")
def agents(iid: int, db: Session = Depends(get_db)):
    rows = db.query(AgentRun).filter(AgentRun.instance_id == iid).order_by(AgentRun.id).all()
    return [_agent_dict(r) for r in rows]


@router.get("/instances/{iid}/remediations")
def remediations(iid: int, db: Session = Depends(get_db)):
    rows = remediation_service.list_for_instance(db, iid)
    return [{"id": p.id, "element_code": p.element_code, "current_value": float(p.current_value),
             "proposed_value": float(p.proposed_value), "rationale": p.rationale,
             "status": p.status, "checker": p.checker, "agent_run_id": p.agent_run_id} for p in rows]


@router.post("/remediations/{pid}/approve")
def approve_remediation(pid: int, body: ActorRequest, db: Session = Depends(get_db)):
    try:
        res = remediation_service.approve(db, pid, checker=body.actor)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return res


@router.post("/remediations/{pid}/reject")
def reject_remediation(pid: int, body: ActorRequest, db: Session = Depends(get_db)):
    try:
        remediation_service.reject(db, pid, checker=body.actor, reason=body.reason)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return {"status": "rejected"}


@router.get("/instances/{iid}/narratives")
def narratives(iid: int, db: Session = Depends(get_db)):
    rows = db.query(Narrative).filter(Narrative.instance_id == iid).order_by(Narrative.id).all()
    return [{"id": n.id, "language": n.language, "version": n.version, "body": n.body,
             "citations": n.citations, "confidence": float(n.confidence), "status": n.status}
            for n in rows]


@router.post("/instances/{iid}/narratives/{nid}/approve")
def approve_narrative(iid: int, nid: int, body: ActorRequest, db: Session = Depends(get_db)):
    n = db.get(Narrative, nid)
    if not n:
        raise HTTPException(404, "narrative not found")
    n.status = "approved"
    audit_service.log(db, actor=body.actor, action="approve_narrative", entity_type="narrative",
                      entity_id=nid, instance_id=iid)
    db.commit()
    return {"id": n.id, "status": n.status}


@router.get("/instances/{iid}/circulars")
def circulars(iid: int, db: Session = Depends(get_db)):
    rows = db.query(CircularChange).all()
    return [{"id": c.id, "regulator": c.regulator, "standard": c.standard,
             "description": c.description, "affected_reports": c.affected_reports,
             "affected_elements": c.affected_elements, "status": c.status,
             "target_date": c.target_date, "impact_analysis": c.impact_analysis} for c in rows]


# ---- sign-off + export + audit ----------------------------------------------
@router.post("/instances/{iid}/signoff")
def signoff(iid: int, body: ActorRequest, db: Session = Depends(get_db)):
    allowed, blocking = certification_service.is_calc_allowed(db, iid)
    if not allowed:
        raise HTTPException(409, detail={"error": "certification_gate", "blocking_domains": blocking})
    run = calc_service.latest_run(db, iid)
    fails = db.query(ValidationResult).filter(ValidationResult.instance_id == iid,
                                              ValidationResult.status == "fail").count()
    if fails:
        raise HTTPException(409, detail={"error": "validation_failures", "count": fails})
    report_instance_service.set_status(db, iid, "SIGNED_OFF", actor=body.actor)
    audit_service.log(db, actor=body.actor, action="signoff", entity_type="report_instance",
                      entity_id=iid, instance_id=iid)
    db.commit()
    return {"status": "SIGNED_OFF", "calc_run_id": run.id if run else None}


def _require_signoff(db: Session, iid: int):
    inst = report_instance_service.get(db, iid)
    if not inst:
        raise HTTPException(404, "instance not found")
    if inst.status not in ("SIGNED_OFF", "EXPORTED"):
        raise HTTPException(409, detail={"error": "not_signed_off", "status": inst.status})


@router.get("/instances/{iid}/export/excel")
def export_excel(iid: int, db: Session = Depends(get_db)):
    # export is NOT gated on sign-off; the file/report status reflects Draft vs Signed Off
    calc_service.ensure_current(db, iid, actor="system")
    data = export_service.build_excel(db, iid)
    audit_service.log(db, actor="system", action="export_excel", entity_type="report_instance",
                      entity_id=iid, instance_id=iid)
    db.commit()
    return Response(content=data,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename=CAR-SA-01_{iid}.xlsx"})


@router.get("/instances/{iid}/export/pdf")
def export_pdf(iid: int, db: Session = Depends(get_db)):
    calc_service.ensure_current(db, iid, actor="system")
    data, media = export_service.build_pdf(db, iid)
    ext = "pdf" if media == "application/pdf" else "html"
    return Response(content=data, media_type=media,
                    headers={"Content-Disposition": f"inline; filename=CAR-SA-01_{iid}.{ext}"})


@router.get("/instances/{iid}/audit")
def audit(iid: int, db: Session = Depends(get_db)):
    rows = audit_service.for_instance(db, iid)
    return [{"actor": a.actor, "action": a.action, "entity_type": a.entity_type,
             "entity_id": a.entity_id, "after": a.after, "ts": a.ts.isoformat()} for a in rows]


# ---- config -----------------------------------------------------------------
@router.get("/config/parameters")
def list_params(db: Session = Depends(get_db)):
    return [{"key": p.key, "value": float(p.value), "scope": p.scope, "description": p.description}
            for p in config_service.list_parameters(db)]


@router.post("/config/parameters")
def set_param(body: SetParameter, db: Session = Depends(get_db)):
    p = config_service.set_parameter(db, key=body.key, value=body.value, scope=body.scope,
                                     description=body.description)
    db.commit()
    return {"key": p.key, "value": float(p.value), "scope": p.scope}
