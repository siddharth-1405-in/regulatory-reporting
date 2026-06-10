"""Synthetic CAR-SA-01 input data for a mid/large Saudi bank (SAR '000).

Used by both the database seed script and the calculation tests. Two states:

  * ``baseline_inputs()`` — internally consistent, comfortably compliant.
  * ``apply_schedule2_anomaly()`` — a single Schedule 2 data-entry error
    (Corporate BBB+ to BB- exposure entered ~10x too high) that materially
    inflates Credit Risk RWA → Total RWA and pushes the bank into a capital
    buffer breach. This is the seeded anomaly the agents must surface and the
    remediation must correct.
"""
from __future__ import annotations

from decimal import Decimal

from .parameters import D

# The single line the anomaly corrupts, and its correct vs erroneous value.
ANOMALY_ELEMENT = "S2_ON_CORP_BBB"
ANOMALY_CORRECT = D("9_500_000")
ANOMALY_ERRONEOUS = D("105_000_000")


def baseline_inputs() -> dict[str, Decimal]:
    """Correct, compliant set of inputs across all schedules."""
    v: dict[str, Decimal] = {}

    # ---- Schedule 1: capital -------------------------------------------------
    v.update({
        "S1_CET1_PAIDUP": D("8_000_000"),
        "S1_CET1_SHARE_PREMIUM": D("1_500_000"),
        "S1_CET1_RETAINED": D("4_500_000"),
        "S1_CET1_CY_PROFIT": D("1_200_000"),
        "S1_CET1_AOCI": D("300_000"),
        "S1_CET1_OTHER_RESERVES": D("500_000"),
        "S1_CET1_MINORITY": D("200_000"),
        # deductions
        "S1_CET1D_GOODWILL": D("800_000"),
        "S1_CET1D_INTANGIBLES": D("400_000"),
        "S1_CET1D_DTA_PROFIT": D("200_000"),
        "S1_CET1D_CFHEDGE": D("100_000"),
        "S1_CET1D_PENSION": D("50_000"),
        "S1_CET1D_OTHER": D("150_000"),
        # AT1
        "S1_AT1_INSTRUMENTS": D("2_000_000"),
        # Tier 2
        "S1_T2_INSTRUMENTS": D("1_500_000"),
        "S1_T2_GEN_PROVISIONS": D("500_000"),
    })
    # CET1 net = 16,200,000 - 1,700,000 = 14,500,000
    # Tier 1 = 16,500,000 ; Total capital = 18,500,000

    # ---- Schedule 2: credit risk exposures ----------------------------------
    v.update({
        "S2_ON_SAUDI_GOV": D("30_000_000"),     # rw 0%
        "S2_ON_CORP_A": D("25_000_000"),        # rw 50% -> 12,500,000
        "S2_ON_CORP_BBB": ANOMALY_CORRECT,      # rw 100% -> 9,500,000  (anomaly target)
        "S2_ON_RETAIL": D("18_000_000"),        # rw 75% -> 13,500,000
        "S2_ON_RRE_LOW": D("22_000_000"),       # rw 35% -> 7,700,000
        "S2_ON_BANK_A": D("10_000_000"),        # rw 50% -> 5,000,000
        "S2_ON_SME_CORP": D("8_000_000"),       # rw 100% -> 8,000,000
        "S2_ON_CRE": D("6_000_000"),            # rw 100% -> 6,000,000
        "S2_ON_PSE_DOM": D("5_000_000"),        # rw 20% -> 1,000,000
        "S2_ON_OTHER": D("4_000_000"),          # rw 100% -> 4,000,000
        # off-balance
        "S2_OFF_TRADE_LC": D("10_000_000"),     # ccf 20%, rw 100% -> 2,000,000
        "S2_OFF_COMMIT_GT1Y": D("8_000_000"),   # ccf 50%, rw 100% -> 4,000,000
        "S2_OFF_DIRECT_CREDIT": D("1_000_000"), # ccf 100%, rw 100% -> 1,000,000
    })
    # on-bal RWA = 67,200,000 ; off-bal RWA = 7,000,000 ; credit RWA = 74,200,000

    # ---- Schedule 3: market risk --------------------------------------------
    v.update({
        "S3_IR_SPECIFIC_IG": D("5_000_000"),    # x 0.25% -> 12,500
        "S3_EQ_GENERAL": D("1_000_000"),        # x 8% -> 80,000
        "S3_FX_NETOPEN": D("2_000_000"),        # x 8% -> 160,000
        "S3_IR_GENERAL_DURATION": D("50_000"),  # direct charge
    })
    # market charge = 302,500 ; market RWA = 3,781,250

    # ---- Schedule 4: operational risk (3-yr gross income) -------------------
    v.update({
        "S4_RETAIL_BANKING_GI_Y1": D("3_000_000"),
        "S4_RETAIL_BANKING_GI_Y2": D("3_200_000"),
        "S4_RETAIL_BANKING_GI_Y3": D("3_400_000"),   # avg 3,200,000 x 12% = 384,000
        "S4_COMMERCIAL_BANKING_GI_Y1": D("2_000_000"),
        "S4_COMMERCIAL_BANKING_GI_Y2": D("2_100_000"),
        "S4_COMMERCIAL_BANKING_GI_Y3": D("2_200_000"),  # avg 2,100,000 x 15% = 315,000
        "S4_TRADING_SALES_GI_Y1": D("800_000"),
        "S4_TRADING_SALES_GI_Y2": D("900_000"),
        "S4_TRADING_SALES_GI_Y3": D("1_000_000"),    # avg 900,000 x 18% = 162,000
        "S4_CORP_FINANCE_GI_Y1": D("500_000"),
        "S4_CORP_FINANCE_GI_Y2": D("600_000"),
        "S4_CORP_FINANCE_GI_Y3": D("700_000"),       # avg 600,000 x 18% = 108,000
        "S4_PAYMENT_SETTLEMENT_GI_Y1": D("300_000"),
        "S4_PAYMENT_SETTLEMENT_GI_Y2": D("300_000"),
        "S4_PAYMENT_SETTLEMENT_GI_Y3": D("300_000"), # avg 300,000 x 18% = 54,000
        "S4_AGENCY_SERVICES_GI_Y1": D("200_000"),
        "S4_AGENCY_SERVICES_GI_Y2": D("200_000"),
        "S4_AGENCY_SERVICES_GI_Y3": D("200_000"),    # avg 200,000 x 15% = 30,000
        "S4_ASSET_MGMT_GI_Y1": D("400_000"),
        "S4_ASSET_MGMT_GI_Y2": D("400_000"),
        "S4_ASSET_MGMT_GI_Y3": D("400_000"),         # avg 400,000 x 12% = 48,000
        "S4_RETAIL_BROKERAGE_GI_Y1": D("150_000"),
        "S4_RETAIL_BROKERAGE_GI_Y2": D("150_000"),
        "S4_RETAIL_BROKERAGE_GI_Y3": D("150_000"),   # avg 150,000 x 12% = 18,000
    })
    # op charge = 1,119,000 ; op RWA = 13,987,500

    # ---- Schedule 6: reconciliation (sign convention: "Less" = negative) ----
    v.update({
        "S6_PAIDUP_FS": D("8_000_000"),
        "S6_SHARE_PREMIUM_FS": D("1_500_000"),
        "S6_RETAINED_FS": D("4_500_000"),
        "S6_OCI_FS": D("2_000_000"),       # AOCI + other reserves + CY profit
        "S6_MINORITY_FS": D("200_000"),
        "S6_GOODWILL_FS": D("-1_200_000"), # goodwill + intangibles
        "S6_DTA_FS": D("-200_000"),
        "S6_CFHEDGE_FS": D("-100_000"),
        "S6_OTHER_DEDUCT_FS": D("-200_000"),  # pension + other
        "S6_T2_INSTRUMENTS_FS": D("1_500_000"),
        "S6_T2_INSTRUMENTS_ADJ": D("2_000_000"),  # AT1 eligible captured here (MVP)
        "S6_GEN_PROVISIONS_FS": D("500_000"),
    })
    # reconciled total = 18,500,000 == Schedule 1 total capital -> nil difference

    return v


def apply_schedule2_anomaly(inputs: dict[str, Decimal]) -> dict[str, Decimal]:
    """Return a copy with the Schedule 2 corporate-exposure data error applied."""
    out = dict(inputs)
    out[ANOMALY_ELEMENT] = ANOMALY_ERRONEOUS
    return out
