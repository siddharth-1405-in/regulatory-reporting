"""Schedule 6 — Reconciliation to Published Financial Statements (deterministic).

    Part A: regulatory figure per line = published FS + regulatory adjustment.
            Reconciled regulatory capital must equal Schedule 1 total capital.
            Difference (should be nil) = reconciled total − Schedule 1 total.
    Part B: RWA composition = each component / total RWA; must sum to 100%.

Sign convention: "Less:" lines are entered as negative adjustments/values so a
straight sum reproduces total regulatory capital.
"""
from __future__ import annotations

from decimal import Decimal

from ..registry.car_sa01 import elements as reg
from .types import LineResult, ScheduleResult

Z = Decimal("0")


def compute(inputs: dict[str, Decimal], s1_total_capital: Decimal,
            credit_rwa: Decimal, market_rwa: Decimal, oprisk_rwa: Decimal) -> ScheduleResult:
    sched = ScheduleResult(sheet_name="Schedule 6")

    reconciled_total = Z
    for base, label, _row in reg._S6_LINES:
        fs = inputs.get(f"{base}_FS", Z)
        adj = inputs.get(f"{base}_ADJ", Z)
        figure = fs + adj
        reconciled_total += figure
        sched.lines.append(LineResult(base, label, "Reconciliation",
                                       {"published_fs": fs, "adjustment": adj}, figure))

    recon_diff = reconciled_total - s1_total_capital

    total_rwa = credit_rwa + market_rwa + oprisk_rwa
    credit_pct = (credit_rwa / total_rwa) if total_rwa else Z
    market_pct = (market_rwa / total_rwa) if total_rwa else Z
    oprisk_pct = (oprisk_rwa / total_rwa) if total_rwa else Z

    sched.totals = {
        "S6_RECONCILED_CAPITAL": reconciled_total,
        "S6_TOTAL_REG_CAPITAL": s1_total_capital,
        "S6_RECON_DIFF": recon_diff,
        "S6_CREDIT_PCT": credit_pct,
        "S6_MARKET_PCT": market_pct,
        "S6_OPRISK_PCT": oprisk_pct,
        "S6_RWA_TOTAL": total_rwa,
        "S6_COMPOSITION_PCT": credit_pct + market_pct + oprisk_pct,
    }
    return sched
