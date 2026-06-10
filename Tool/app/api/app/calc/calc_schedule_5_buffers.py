"""Schedule 5 — Capital Buffers & Combined Capital Requirement (deterministic).

    Combined buffer requirement = CCB + CCyB + D-SIB + other          (× RWA)
    CET1 available for buffers   = CET1 ratio − Pillar 1 CET1 minimum (4.5%)
    Buffer surplus / (deficit)   = CET1 available for buffers − combined buffer
    Pillar 1 surplus per tier    = actual ratio − minimum

Buffers are met with CET1 only and sit on top of the 4.5% CET1 minimum
(assuming the AT1/Tier 2 buckets are filled by AT1/Tier 2 — the standard MVP
simplification). The dividend-distribution constraint band is resolved from the
CET1 ratio.
"""
from __future__ import annotations

from decimal import Decimal

from ..registry.car_sa01.parameters import (
    BUFFER_RATES, CCB_DISTRIBUTION_BANDS, PILLAR1_MINIMUMS,
)

Z = Decimal("0")


def compute(cet1_ratio: Decimal, tier1_ratio: Decimal, total_ratio: Decimal,
            total_rwa: Decimal, buffers: dict[str, Decimal] | None = None) -> dict[str, object]:
    b = {**BUFFER_RATES, **(buffers or {})}
    combined = b["ccb"] + b["ccyb"] + b["dsib"] + b["other"]

    cet1_for_buffers = cet1_ratio - PILLAR1_MINIMUMS["cet1"]
    surplus = cet1_for_buffers - combined

    # dividend-distribution constraint band (by CET1 ratio)
    band_label = "Above 7.0% — no restriction"
    max_payout = "No restriction"
    for low, high, conservation, payout in CCB_DISTRIBUTION_BANDS:
        if low <= cet1_ratio < high:
            if payout is None:
                band_label, max_payout = "Above 7.0% — no restriction", "No restriction"
            else:
                band_label = f"{low*100:.3f}%–{high*100:.3f}% of RWA"
                max_payout = f"{payout*100:.0f}%"
            break

    return {
        "values": {
            "S5_PILLAR1_MIN_CET1": PILLAR1_MINIMUMS["cet1"],
            "S5_PILLAR1_MIN_TIER1": PILLAR1_MINIMUMS["tier1"],
            "S5_PILLAR1_MIN_TOTAL": PILLAR1_MINIMUMS["total_capital"],
            "S5_CET1_SURPLUS_P1": cet1_ratio - PILLAR1_MINIMUMS["cet1"],
            "S5_TIER1_SURPLUS_P1": tier1_ratio - PILLAR1_MINIMUMS["tier1"],
            "S5_TOTAL_SURPLUS_P1": total_ratio - PILLAR1_MINIMUMS["total_capital"],
            "S5_BUFFER_CCB": b["ccb"],
            "S5_BUFFER_CCYB": b["ccyb"],
            "S5_BUFFER_DSIB": b["dsib"],
            "S5_BUFFER_OTHER": b["other"],
            "S5_COMBINED_BUFFER": combined,
            "S5_CET1_AVAILABLE_FOR_BUFFERS": cet1_for_buffers,
            "S5_CET1_SURPLUS": surplus,
            # combined requirement amounts (× RWA) for display
            "S5_COMBINED_BUFFER_AMOUNT": combined * total_rwa,
        },
        "flags": {
            "buffer_status": "Compliant" if surplus >= 0 else "Breach",
            "distribution_band": band_label,
            "max_dividend_payout": max_payout,
        },
    }
