"""Integration tests — governance flow end to end.

Covers certification gating, the seeded anomaly, remediation approval (Checker
gate), invalidation on upstream change, and export gating.
"""
from datetime import date
from decimal import Decimal

import pytest

from app.agents import orchestrator
from app.models import ValidationResult
from app.services import (
    calc_service, certification_service, dq_service, export_service,
    ingestion_service, ownership_service, remediation_service,
    report_instance_service,
)
from app.registry.car_sa01.sample_data import apply_schedule2_anomaly, baseline_inputs


def _make_instance(db, anomaly=True):
    inst = report_instance_service.create_instance(
        db, period_label="Q4 2025", period_end=date(2025, 12, 31),
        bank_name="Test Bank", actor="maker")
    data = apply_schedule2_anomaly(baseline_inputs()) if anomaly else baseline_inputs()
    finance = {c: v for c, v in data.items() if ownership_service.domain_for_element(c) == "Finance"}
    risk = {c: v for c, v in data.items() if ownership_service.domain_for_element(c) == "Risk"}
    ingestion_service.ingest_values(db, instance_id=inst.id, domain="Finance",
                                    source_label="GL", values=finance, actor="finance.maker")
    ingestion_service.ingest_values(db, instance_id=inst.id, domain="Risk",
                                    source_label="Risk", values=risk, actor="risk.maker")
    db.commit()
    return inst


def _certify_all(db, iid):
    certification_service.certify(db, iid, "Finance", actor="cfo.checker")
    certification_service.certify(db, iid, "Risk", actor="cro.checker")
    db.commit()


# ---- certification gate -----------------------------------------------------
def test_calc_blocked_until_certified(db):
    inst = _make_instance(db)
    allowed, blocking = certification_service.is_calc_allowed(db, inst.id)
    assert not allowed and set(blocking) == {"Finance", "Risk"}
    with pytest.raises(calc_service.CertificationGateError):
        calc_service.run_calculation(db, inst.id, actor="maker")


def test_calc_runs_after_certification_and_flags_anomaly(db):
    inst = _make_instance(db)
    _certify_all(db, inst.id)
    run, result, findings = calc_service.run_calculation(db, inst.id, actor="maker")
    db.commit()
    assert result.flags["buffer_status"] == "Breach"
    failing = {f["rule_code"] for f in findings if f["status"] == "fail"}
    assert "CREDIT_CONCENTRATION_ANOMALY" in failing
    assert "BUFFER_CONSISTENCY" in failing


# ---- remediation approval (Checker gate) ------------------------------------
def test_remediation_requires_checker_and_restores_compliance(db):
    inst = _make_instance(db)
    _certify_all(db, inst.id)
    run, result, findings = calc_service.run_calculation(db, inst.id, actor="maker")
    fdicts = [{"rule_code": f["rule_code"], "status": f["status"], "message": f["message"]}
              for f in findings]
    summary = orchestrator.run_governed_pipeline(db, inst.id, result, fdicts, actor="maker")
    db.commit()
    pid = summary["remediation_proposal_id"]
    assert pid is not None

    proposals = remediation_service.list_for_instance(db, inst.id)
    assert proposals[0].status == "proposed"   # not auto-applied

    res = remediation_service.approve(db, pid, checker="cro.checker")
    db.commit()
    assert res["buffer_status"] == "Compliant"
    assert res["failing_rules"] == []
    assert remediation_service.list_for_instance(db, inst.id)[0].status == "approved"


def test_reject_leaves_value_unchanged(db):
    inst = _make_instance(db)
    _certify_all(db, inst.id)
    run, result, findings = calc_service.run_calculation(db, inst.id, actor="maker")
    fdicts = [{"rule_code": f["rule_code"], "status": f["status"], "message": f["message"]}
              for f in findings]
    summary = orchestrator.run_governed_pipeline(db, inst.id, result, fdicts, actor="maker")
    db.commit()
    pid = summary["remediation_proposal_id"]
    remediation_service.reject(db, pid, checker="cro.checker", reason="needs source confirmation")
    db.commit()
    before = report_instance_service.load_inputs(db, inst.id)["S2_ON_CORP_BBB"]
    assert before == Decimal("105000000")


# ---- invalidation on upstream change ----------------------------------------
def test_value_change_invalidates_certification(db):
    inst = _make_instance(db, anomaly=False)
    _certify_all(db, inst.id)
    assert certification_service.is_calc_allowed(db, inst.id)[0]
    ingestion_service.update_value(db, instance_id=inst.id, element_code="S2_ON_CORP_A",
                                   value=Decimal("30000000"), actor="risk.maker")
    db.commit()
    allowed, blocking = certification_service.is_calc_allowed(db, inst.id)
    assert not allowed and "Risk" in blocking   # Risk owns the changed element


# ---- DQ + export ------------------------------------------------------------
def test_dq_runs(db):
    inst = _make_instance(db)
    findings = dq_service.run(db, inst.id, report_instance_service.load_inputs(db, inst.id))
    db.commit()
    assert findings  # at least the 'all checks passed' info row or warnings


def test_export_excel_after_calc(db):
    inst = _make_instance(db, anomaly=False)
    _certify_all(db, inst.id)
    calc_service.run_calculation(db, inst.id, actor="maker")
    db.commit()
    data = export_service.build_excel(db, inst.id)
    assert data[:2] == b"PK"  # xlsx is a zip archive
