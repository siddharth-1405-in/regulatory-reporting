"""Data Layer governance tests — element-level maker-checker + gate roll-up."""
from datetime import date
from decimal import Decimal

import pytest

from app.services import (
    certification_service, data_layer_service as dl, ingestion_service,
    ownership_service, report_instance_service,
)
from app.registry.car_sa01.sample_data import baseline_inputs


def _instance(db):
    inst = report_instance_service.create_instance(
        db, period_label="Q4 2025", period_end=date(2025, 12, 31),
        bank_name="Test Bank", actor="maker")
    data = baseline_inputs()
    for domain in ("Finance", "Risk"):
        vals = {c: v for c, v in data.items() if ownership_service.domain_for_element(c) == domain}
        ingestion_service.ingest_values(db, instance_id=inst.id, domain=domain,
                                        source_label="src", values=vals, actor=f"{domain}.maker")
    db.commit()
    dl.ensure_governance(db, inst.id)
    db.commit()
    return inst


def test_catalogue_covers_all_inputs(db):
    inst = _instance(db)
    cat = dl.catalogue(db, inst.id)
    from app.registry.car_sa01 import elements as reg
    assert len(cat) == len(reg.INPUT_ELEMENTS)
    sample = next(c for c in cat if c["element_code"] == "S2_ON_CORP_BBB")
    assert sample["domain"] == "Risk"
    assert "Schedule 2" in sample["dependent_schedules"]
    assert "Summary" in sample["dependent_schedules"]


def test_element_lifecycle_edit_freeze_submit_approve(db):
    inst = _instance(db)
    code = "S2_ON_CORP_A"
    dl.edit_value(db, instance_id=inst.id, element_code=code, value=26_000_000, role="Maker", actor="risk.maker")
    assert dl._row(db, inst.id, code).status == "edited"
    dl.freeze(db, inst.id, [code], "Maker", "risk.maker")
    assert dl._row(db, inst.id, code).status == "frozen"
    dl.submit(db, inst.id, [code], "Maker", "risk.maker")
    assert dl._row(db, inst.id, code).status == "submitted"
    assert any(q["element_code"] == code for q in dl.signoff_queue(db, inst.id))
    dl.approve(db, inst.id, [code], "Checker", "cro.checker")
    assert dl._row(db, inst.id, code).status == "certified"


def test_role_enforcement(db):
    inst = _instance(db)
    with pytest.raises(dl.RolePermissionError):
        dl.edit_value(db, instance_id=inst.id, element_code="S2_ON_CORP_A", value=1, role="Checker", actor="c")
    with pytest.raises(dl.RolePermissionError):
        dl.approve(db, inst.id, ["S2_ON_CORP_A"], "Maker", "m")


def test_full_signoff_rolls_up_and_unlocks_calc(db):
    inst = _instance(db)
    codes = [e.element_code for e in __import__("app.registry.car_sa01.elements",
             fromlist=["INPUT_ELEMENTS"]).INPUT_ELEMENTS]
    assert not certification_service.is_calc_allowed(db, inst.id)[0]
    dl.freeze(db, inst.id, codes, "Maker", "maker")
    dl.submit(db, inst.id, codes, "Maker", "maker")
    res = dl.approve(db, inst.id, codes, "Checker", "checker")
    db.commit()
    assert set(res["domains_certified"]) == {"Finance", "Risk"}
    assert certification_service.is_calc_allowed(db, inst.id)[0]


def test_certified_element_is_locked_to_makers(db):
    inst = _instance(db)
    certification_service.certify(db, inst.id, "Risk", actor="cro.checker")
    db.commit()
    assert dl._row(db, inst.id, "S2_ON_CORP_A").status == "certified"
    # a certified value cannot be edited directly — must be reopened first
    with pytest.raises(dl.RolePermissionError):
        dl.edit_value(db, instance_id=inst.id, element_code="S2_ON_CORP_A", value=99_000_000,
                      role="Maker", actor="risk.maker")


def test_reopen_certified_recalls_and_invalidates_domain(db):
    inst = _instance(db)
    certification_service.certify(db, inst.id, "Risk", actor="cro.checker")
    db.commit()
    assert certification_service.status_map(db, inst.id)["Risk"] == "Certified"
    # Maker reopens a certified element to amend it -> element editable, domain recalled
    dl.reopen(db, inst.id, ["S2_ON_CORP_A"], "Maker", "risk.maker")
    db.commit()
    assert dl._row(db, inst.id, "S2_ON_CORP_A").status == "edited"
    assert certification_service.status_map(db, inst.id)["Risk"] == "Invalidated"
    # now editable again
    dl.edit_value(db, instance_id=inst.id, element_code="S2_ON_CORP_A", value=26_000_000,
                  role="Maker", actor="risk.maker")
    assert dl._row(db, inst.id, "S2_ON_CORP_A").status == "edited"


def test_approved_value_change_invalidates(db):
    inst = _instance(db)
    certification_service.certify(db, inst.id, "Finance", actor="cfo.checker")
    certification_service.certify(db, inst.id, "Risk", actor="cro.checker")
    db.commit()
    assert dl._row(db, inst.id, "S2_ON_CORP_A").status == "certified"
    # a system-level change to a certified value (e.g. an approved remediation)
    # invalidates the element governance and the owning domain certification
    ingestion_service.update_value(db, instance_id=inst.id, element_code="S2_ON_CORP_A",
                                   value=Decimal("99000000"), actor="cro.checker")
    db.commit()
    assert dl._row(db, inst.id, "S2_ON_CORP_A").status == "invalidated"
    allowed, blocking = certification_service.is_calc_allowed(db, inst.id)
    assert not allowed and "Risk" in blocking
