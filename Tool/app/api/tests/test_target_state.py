"""Target-state tests — source mapping, rule edit auto-recompute, governed
override, two-tier schedule sign-off, ungated export."""
from datetime import date
from decimal import Decimal

import pytest

from app.registry.car_sa01 import elements as reg
from app.registry.car_sa01 import sources as sources_reg
from app.services import (
    calc_service, certification_service, data_layer_service as dl, ingestion_service,
    ownership_service, report_instance_service, report_signoff_service, rules_service,
    sources_service,
)
from app.registry.car_sa01.sample_data import baseline_inputs


def _certified_instance(db):
    inst = report_instance_service.create_instance(
        db, period_label="Q4 2025", period_end=date(2025, 12, 31), bank_name="Test Bank", actor="maker")
    data = baseline_inputs()
    for domain in ("Finance", "Risk"):
        vals = {c: v for c, v in data.items() if ownership_service.domain_for_element(c) == domain}
        ingestion_service.ingest_values(db, instance_id=inst.id, domain=domain,
                                        source_label="src", values=vals, actor=f"{domain}.maker")
    certification_service.certify(db, inst.id, "Finance", actor="cfo.checker")
    certification_service.certify(db, inst.id, "Risk", actor="cro.checker")
    db.commit()
    return inst


# ---- source systems ---------------------------------------------------------
def test_every_input_maps_to_a_real_source(db):
    sources_service.ensure_sources(db)
    db.commit()
    names = {s["code"] for s in sources_service.catalogue(db)}
    assert {"SAP_S4", "MUREX", "FINASTRA", "MOODYS", "SAS_RISK"} <= names
    for e in reg.INPUT_ELEMENTS:
        src = sources_reg.source_for(e.element_code)
        assert src["source_code"] in names
    # credit exposures come from Finastra; market risk from Murex; capital from SAP
    assert sources_reg.source_for("S2_ON_CORP_BBB")["source_code"] == "FINASTRA"
    assert sources_reg.source_for("S3_FX_NETOPEN")["source_code"] == "MUREX"
    assert sources_reg.source_for("S1_CET1_PAIDUP")["source_code"] == "SAP_S4"


# ---- rule engine ------------------------------------------------------------
def test_rule_edit_recomputes_and_tags_user_edited(db):
    inst = _certified_instance(db)
    calc_service.ensure_current(db, inst.id, actor="system")
    before = calc_service.latest_run(db, inst.id).results["values"]["S2_CREDIT_RWA"]
    rules_service.edit_rule(db, instance_id=inst.id, key="S2_ON_CORP_BBB.risk_weight",
                            value=0.5, role="Maker", actor="risk.maker")
    db.commit()
    after = calc_service.latest_run(db, inst.id).results["values"]["S2_CREDIT_RWA"]
    assert after < before  # halving the risk weight lowers credit RWA
    tag = next(r["tag"] for r in rules_service.list_rules(db, inst.id) if r["element_code"] == "S2_ON_CORP_BBB")
    assert tag == "user-edited"


# ---- corrections flow through re-ingestion (no manual override) -------------
def test_reingestion_changes_effective_value(db):
    inst = _certified_instance(db)
    raw0 = report_instance_service.load_raw_inputs(db, inst.id)["S2_ON_CORP_A"]
    assert raw0 == Decimal("25000000")
    # the engine always uses the raw system value; corrections come from upstream
    ingestion_service.update_value(db, instance_id=inst.id, element_code="S2_ON_CORP_A",
                                   value=Decimal("40000000"), actor="risk.maker")
    db.commit()
    eff = report_instance_service.load_inputs(db, inst.id)["S2_ON_CORP_A"]
    assert eff == Decimal("40000000")
    dd = dl.drilldown(db, inst.id, "S2_ON_CORP_A")
    assert dd["raw_value"] == 40_000_000
    assert "override_value" not in dd
    assert [s["step"] for s in dd["steps"]][0] == "Source extract"


# ---- two-tier report sign-off ----------------------------------------------
def test_schedule_signoff_requires_data_then_summary_after_all(db):
    inst = _certified_instance(db)
    calc_service.ensure_current(db, inst.id, actor="system")
    db.commit()
    view = {s["key"]: s for s in report_signoff_service.schedule_view(db, inst.id)}
    assert view["S1"]["can_signoff"] and not view["Summary"]["can_signoff"]
    for key in ["S1", "S2", "S3", "S4", "S5", "S6"]:
        report_signoff_service.signoff(db, inst.id, key, "Checker", "cro.checker", "ok")
    db.commit()
    assert report_signoff_service.schedule_view(db, inst.id)
    summary = {s["key"]: s for s in report_signoff_service.schedule_view(db, inst.id)}["Summary"]
    assert summary["can_signoff"]
    report_signoff_service.signoff(db, inst.id, "Summary", "Checker", "cro.checker", "final")
    db.commit()
    assert report_signoff_service.report_status(db, inst.id) == "Signed Off"


def test_changing_certified_data_reopens_signed_schedule(db):
    inst = _certified_instance(db)
    calc_service.ensure_current(db, inst.id, actor="system")
    report_signoff_service.signoff(db, inst.id, "S2", "Checker", "cro.checker", "ok")
    db.commit()
    # change a certified Risk value -> Risk cert invalidates -> S2 reopens
    ingestion_service.update_value(db, instance_id=inst.id, element_code="S2_ON_CORP_A",
                                   value=Decimal("30000000"), actor="risk.maker")
    db.commit()
    s2 = {s["key"]: s for s in report_signoff_service.schedule_view(db, inst.id)}["S2"]
    assert s2["status"] == "reopened"


def test_maker_cannot_sign_off(db):
    inst = _certified_instance(db)
    calc_service.ensure_current(db, inst.id, actor="system")
    with pytest.raises(dl.RolePermissionError):
        report_signoff_service.signoff(db, inst.id, "S1", "Maker", "m", "")
