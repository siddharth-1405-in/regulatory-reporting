"""Summary — Capital Adequacy Ratios (deterministic, cross-schedule).

    Total RWA            = credit + market + operational
    CET1 ratio           = Net CET1 / Total RWA
    Tier 1 ratio         = Total Tier 1 / Total RWA
    Total capital ratio  = Total regulatory capital / Total RWA
"""
from __future__ import annotations

from decimal import Decimal

from ..registry.car_sa01.parameters import SAMA_SUMMARY_MINIMUMS

Z = Decimal("0")


def _ratio(num: Decimal, den: Decimal) -> Decimal:
    return (num / den) if den != 0 else Z


def compute(s1: dict[str, Decimal], credit_rwa: Decimal, market_rwa: Decimal,
            oprisk_rwa: Decimal) -> dict[str, Decimal]:
    total_rwa = credit_rwa + market_rwa + oprisk_rwa
    cet1 = s1["S1_CET1_NET"]
    tier1 = s1["S1_TIER1_TOTAL"]
    total_capital = s1["S1_TOTAL_CAPITAL"]

    return {
        "SUM_CREDIT_RWA": credit_rwa,
        "SUM_MARKET_RWA": market_rwa,
        "SUM_OPRISK_RWA": oprisk_rwa,
        "SUM_TOTAL_RWA": total_rwa,
        "SUM_CET1_CAPITAL": cet1,
        "SUM_AT1_CAPITAL": s1["S1_AT1_TOTAL"],
        "SUM_TIER1_CAPITAL": tier1,
        "SUM_TIER2_CAPITAL": s1["S1_T2_TOTAL"],
        "SUM_TOTAL_CAPITAL": total_capital,
        "SUM_CET1_RATIO": _ratio(cet1, total_rwa),
        "SUM_TIER1_RATIO": _ratio(tier1, total_rwa),
        "SUM_TOTAL_RATIO": _ratio(total_capital, total_rwa),
        # SAMA published minimums for comparison (constants).
        "SUM_MIN_CET1": SAMA_SUMMARY_MINIMUMS["cet1"],
        "SUM_MIN_TIER1": SAMA_SUMMARY_MINIMUMS["tier1"],
        "SUM_MIN_TOTAL": SAMA_SUMMARY_MINIMUMS["total_capital"],
    }
