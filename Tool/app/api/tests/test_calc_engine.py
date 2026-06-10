"""Unit tests for the deterministic CAR-SA-01 calculation engine.

Proves each schedule's formulas against the synthetic baseline and verifies the
seeded Schedule 2 anomaly materially inflates Total RWA and breaches the buffer.
"""
from decimal import Decimal

import pytest

from app.calc import engine
from app.registry.car_sa01.parameters import D
from app.registry.car_sa01.sample_data import (
    apply_schedule2_anomaly, baseline_inputs,
)


@pytest.fixture
def base():
    return engine.compute(baseline_inputs())


@pytest.fixture
def anomalous():
    return engine.compute(apply_schedule2_anomaly(baseline_inputs()))


# ---- Schedule 1: capital ----------------------------------------------------
def test_schedule1_capital(base):
    assert base.value("S1_CET1_SUBTOTAL") == D("16_200_000")
    assert base.value("S1_CET1_DEDUCT_TOTAL") == D("1_700_000")
    assert base.value("S1_CET1_NET") == D("14_500_000")          # subtotal - deductions
    assert base.value("S1_AT1_TOTAL") == D("2_000_000")
    assert base.value("S1_TIER1_TOTAL") == D("16_500_000")       # CET1 + AT1
    assert base.value("S1_T2_TOTAL") == D("2_000_000")
    assert base.value("S1_TOTAL_CAPITAL") == D("18_500_000")     # Tier1 + Tier2


# ---- Schedule 2: credit RWA -------------------------------------------------
def test_schedule2_credit_rwa(base):
    assert base.value("S2_ONBAL_RWA") == D("67_200_000")         # sum(exposure x rw)
    assert base.value("S2_OFFBAL_RWA") == D("7_000_000")         # sum(exposure x ccf x rw)
    assert base.value("S2_CREDIT_RWA") == D("74_200_000")


def test_offbalance_ccf_chain(base):
    # LC: 10,000,000 x 0.2 (CCF) = 2,000,000 equivalent x 1.0 (rw) = 2,000,000 RWA
    lc = next(l for l in base.schedules["Schedule 2"].lines if l.element_code == "S2_OFF_TRADE_LC")
    assert lc.inputs["equivalent"] == D("2_000_000")
    assert lc.result == D("2_000_000")


# ---- Schedule 3: market risk ------------------------------------------------
def test_schedule3_market_risk(base):
    assert base.value("S3_MARKET_CHARGE") == D("302_500")
    assert base.value("S3_MARKET_RWA") == D("302_500") * D("12.5")   # x 12.5


# ---- Schedule 4: operational risk -------------------------------------------
def test_schedule4_operational_risk(base):
    assert base.value("S4_OPRISK_CHARGE") == D("1_119_000")
    assert base.value("S4_OPRISK_RWA") == D("1_119_000") * D("12.5")


# ---- Summary: total RWA + ratios --------------------------------------------
def test_summary_total_rwa_and_ratios(base):
    total_rwa = D("74_200_000") + D("3_781_250") + D("13_987_500")
    assert base.value("SUM_TOTAL_RWA") == total_rwa               # credit+market+op
    assert base.value("SUM_CET1_RATIO") == D("14_500_000") / total_rwa
    assert base.value("SUM_TIER1_RATIO") == D("16_500_000") / total_rwa
    assert base.value("SUM_TOTAL_RATIO") == D("18_500_000") / total_rwa
    assert base.flags["buffer_status"] == "Compliant"


# ---- Schedule 6: reconciliation + composition -------------------------------
def test_schedule6_nil_reconciliation(base):
    assert base.value("S6_RECON_DIFF") == D("0")                  # must be nil


def test_schedule6_rwa_composition_totals_100pct(base):
    assert base.value("S6_COMPOSITION_PCT") == D("1")             # 100%


# ---- The seeded anomaly -----------------------------------------------------
def test_anomaly_inflates_rwa_and_breaches_buffer(base, anomalous):
    # Corporate BBB exposure 9.5m -> 105m at 100% risk weight = +95.5m RWA
    delta = anomalous.value("SUM_TOTAL_RWA") - base.value("SUM_TOTAL_RWA")
    assert delta == D("95_500_000")
    # ratios collapse and the bank breaches its combined buffer requirement
    assert anomalous.value("SUM_CET1_RATIO") < base.value("SUM_CET1_RATIO")
    assert anomalous.flags["buffer_status"] == "Breach"
    # capital reconciliation is unaffected by an RWA error
    assert anomalous.value("S6_RECON_DIFF") == D("0")


def test_anomaly_remediation_restores_compliance(anomalous):
    # remediation corrects the exposure back to 9.5m -> recompute -> compliant
    from app.registry.car_sa01.sample_data import ANOMALY_CORRECT, ANOMALY_ELEMENT
    corrected = apply_schedule2_anomaly(baseline_inputs())
    corrected[ANOMALY_ELEMENT] = ANOMALY_CORRECT
    fixed = engine.compute(corrected)
    assert fixed.flags["buffer_status"] == "Compliant"
