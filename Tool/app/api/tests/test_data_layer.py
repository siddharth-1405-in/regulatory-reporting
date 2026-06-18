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
    # every input element is present as a submittable (non-derived) row
    inputs = [c for c in cat if not c.get("derived")]
    assert len(inputs) == len(reg.INPUT_ELEMENTS)
    sample = next(c for c in cat if c["element_code"] == "S2_ON_CORP_BBB")
    assert sample["domain"] == "Risk"
    assert "Schedule 2" in sample["dependent_schedules"]
    assert "Summary" in sample["dependent_schedules"]
    # Schedule 5 surfaces as read-only derived rows (no maker inputs of its own)
    derived = [c for c in cat if c.get("derived")]
    assert derived and all(d["sheet_name"] == "Schedule 5" for d in derived)
    assert all(d["status"] == "derived" and not d["can_submit"] for d in derived)


def test_element_lifecycle_submit_approve(db):
    inst = _instance(db)
    code = "S2_ON_CORP_A"
    assert dl._row(db, inst.id, code).status == "draft"
    dl.submit(db, inst.id, [code], "Maker", "risk.maker")
    assert dl._row(db, inst.id, code).status == "submitted"
    assert any(q["element_code"] == code for q in dl.signoff_queue(db, inst.id))
    dl.approve(db, inst.id, [code], "Checker", "cro.checker")
    assert dl._row(db, inst.id, code).status == "certified"


def test_rejected_element_can_be_resubmitted(db):
    inst = _instance(db)
    code = "S2_ON_CORP_A"
    dl.submit(db, inst.id, [code], "Maker", "risk.maker")
    dl.reject(db, inst.id, [code], "Checker", "cro.checker", reason="needs upstream fix")
    assert dl._row(db, inst.id, code).status == "rejected"
    # after the upstream correction, the Maker can submit again
    dl.submit(db, inst.id, [code], "Maker", "risk.maker")
    assert dl._row(db, inst.id, code).status == "submitted"


def test_role_enforcement(db):
    inst = _instance(db)
    with pytest.raises(dl.RolePermissionError):
        dl.submit(db, inst.id, ["S2_ON_CORP_A"], "Checker", "c")
    with pytest.raises(dl.RolePermissionError):
        dl.approve(db, inst.id, ["S2_ON_CORP_A"], "Maker", "m")


def test_full_signoff_rolls_up_and_unlocks_calc(db):
    inst = _instance(db)
    codes = [e.element_code for e in __import__("app.registry.car_sa01.elements",
             fromlist=["INPUT_ELEMENTS"]).INPUT_ELEMENTS]
    assert not certification_service.is_calc_allowed(db, inst.id)[0]
    dl.submit(db, inst.id, codes, "Maker", "maker")
    res = dl.approve(db, inst.id, codes, "Checker", "checker")
    db.commit()
    assert set(res["domains_certified"]) == {"Finance", "Risk"}
    assert certification_service.is_calc_allowed(db, inst.id)[0]


def test_certified_element_is_not_submittable(db):
    inst = _instance(db)
    certification_service.certify(db, inst.id, "Risk", actor="cro.checker")
    db.commit()
    code = "S2_ON_CORP_A"
    assert dl._row(db, inst.id, code).status == "certified"
    # a certified value is locked: it is not in the submittable set and a submit is a no-op
    cat = {c["element_code"]: c for c in dl.catalogue(db, inst.id)}
    assert cat[code]["can_submit"] is False
    assert dl.submit(db, inst.id, [code], "Maker", "risk.maker") == []
    assert dl._row(db, inst.id, code).status == "certified"


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
