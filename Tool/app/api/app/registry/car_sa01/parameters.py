"""Canonical deterministic parameters for the CAR-SA-01 report pack.

These are the configurable regulatory constants taken directly from the SAMA
CAR workbook. They are the ONLY tunable inputs to the deterministic engine.
`config_service` may override any of these per report instance; the values here
are the defaults that ship with the pack.

Nothing in this module performs a calculation — it is pure reference data.
"""
from __future__ import annotations

from decimal import Decimal


def D(value: str | int | float) -> Decimal:
    return Decimal(str(value))


# RWA conversion factor for market & operational risk (capital charge x 12.5).
RWA_FACTOR = D("12.5")

# Pillar 1 minimum capital ratios (Basel III / SAMA), as fraction of Total RWA.
PILLAR1_MINIMUMS: dict[str, Decimal] = {
    "cet1": D("0.045"),
    "tier1": D("0.06"),
    "total_capital": D("0.08"),
}

# SAMA published-minimum ratios shown on the Summary sheet (incl. CCB baseline).
SAMA_SUMMARY_MINIMUMS: dict[str, Decimal] = {
    "cet1": D("0.07"),
    "tier1": D("0.085"),
    "total_capital": D("0.105"),
}

# Capital buffer rates (fraction of Total RWA). CCyB / D-SIB are jurisdiction or
# bank specific and are treated as configurable inputs (default values shown).
BUFFER_RATES: dict[str, Decimal] = {
    "ccb": D("0.025"),      # Capital Conservation Buffer
    "ccyb": D("0.000"),     # Countercyclical Capital Buffer
    "dsib": D("0.010"),     # D-SIB surcharge (if designated)
    "other": D("0.000"),    # Other SAMA-prescribed buffers
}

# Capital Conservation Buffer dividend-distribution constraint bands (Schedule 5).
# Each band: (cet1_low, cet1_high, min_conservation_ratio, max_payout_ratio).
CCB_DISTRIBUTION_BANDS: list[tuple[Decimal, Decimal, Decimal, Decimal]] = [
    (D("0.045"), D("0.05125"), D("1.00"), D("0.00")),
    (D("0.05125"), D("0.0575"), D("0.80"), D("0.20")),
    (D("0.0575"), D("0.06375"), D("0.60"), D("0.40")),
    (D("0.06375"), D("0.07"), D("0.40"), D("0.60")),
    (D("0.07"), D("9.99"), D("0.00"), None),  # above 7%: no restriction
]

# Maximum eligibility cap for general provisions in Tier 2 (Standardised
# Approach): 1.25% of credit risk RWA. Surfaced as a validation, not auto-applied.
T2_GENERAL_PROVISION_CAP_PCT = D("0.0125")
