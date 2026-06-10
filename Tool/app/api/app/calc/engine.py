"""Deterministic CAR-SA-01 calculation engine.

Runs the schedules in dependency order and assembles the cross-schedule
Summary, buffers (Schedule 5) and reconciliation (Schedule 6). This is the
regulated core: pure functions only, no AI, no database access. Every
regulatory figure on the return originates here.

    Schedule 1 (capital)  ─┐
    Schedule 2 (credit)    ├─► Summary (Total RWA, ratios)
    Schedule 3 (market)    │        ├─► Schedule 5 (buffers)
    Schedule 4 (op risk)  ─┘        └─► Schedule 6 (reconciliation)
"""
from __future__ import annotations

from decimal import Decimal, getcontext

from . import (
    calc_schedule_1_capital as s1,
    calc_schedule_2_credit_rwa as s2,
    calc_schedule_3_market_risk as s3,
    calc_schedule_4_operational_risk as s4,
    calc_schedule_5_buffers as s5,
    calc_schedule_6_reconciliation as s6,
    calc_summary,
)
from .types import CarResult

getcontext().prec = 34  # ample precision for SAR '000 with no float drift


def compute(inputs: dict[str, Decimal],
            params: dict[str, Decimal] | None = None,
            buffers: dict[str, Decimal] | None = None) -> CarResult:
    """Compute the full CAR-SA-01 return from raw input element values.

    `inputs`  : element_code -> Decimal (missing treated as 0)
    `params`  : per-line rate overrides (element_code.risk_weight / .ccf / ...)
    `buffers` : buffer rate overrides (ccb / ccyb / dsib / other)
    """
    params = params or {}
    result = CarResult()

    sched1 = s1.compute(inputs)
    sched2 = s2.compute(inputs, params)
    sched3 = s3.compute(inputs, params)
    sched4 = s4.compute(inputs, params)

    credit_rwa = sched2.totals["S2_CREDIT_RWA"]
    market_rwa = sched3.totals["S3_MARKET_RWA"]
    oprisk_rwa = sched4.totals["S4_OPRISK_RWA"]

    summary = calc_summary.compute(sched1.totals, credit_rwa, market_rwa, oprisk_rwa)
    total_rwa = summary["SUM_TOTAL_RWA"]

    sched5 = s5.compute(
        cet1_ratio=summary["SUM_CET1_RATIO"],
        tier1_ratio=summary["SUM_TIER1_RATIO"],
        total_ratio=summary["SUM_TOTAL_RATIO"],
        total_rwa=total_rwa,
        buffers=buffers,
    )
    sched6 = s6.compute(inputs, sched1.totals["S1_TOTAL_CAPITAL"],
                        credit_rwa, market_rwa, oprisk_rwa)

    # assemble schedules
    result.schedules = {
        "Schedule 1": sched1, "Schedule 2": sched2, "Schedule 3": sched3,
        "Schedule 4": sched4, "Schedule 6": sched6,
    }

    # flat values for lineage / export / API
    values: dict[str, Decimal] = {}
    for sched in (sched1, sched2, sched3, sched4, sched6):
        values.update(sched.subtotals)
        values.update(sched.totals)
    values.update(summary)
    values.update(sched5["values"])  # type: ignore[index]
    result.values = values

    result.metrics = {
        "cet1": sched1.totals["S1_CET1_NET"],
        "tier1": sched1.totals["S1_TIER1_TOTAL"],
        "total_capital": sched1.totals["S1_TOTAL_CAPITAL"],
        "credit_rwa": credit_rwa,
        "market_rwa": market_rwa,
        "oprisk_rwa": oprisk_rwa,
        "total_rwa": total_rwa,
        "cet1_ratio": summary["SUM_CET1_RATIO"],
        "tier1_ratio": summary["SUM_TIER1_RATIO"],
        "total_ratio": summary["SUM_TOTAL_RATIO"],
        "combined_buffer": sched5["values"]["S5_COMBINED_BUFFER"],   # type: ignore[index]
        "cet1_buffer_surplus": sched5["values"]["S5_CET1_SURPLUS"],  # type: ignore[index]
        "recon_diff": sched6.totals["S6_RECON_DIFF"],
        "rwa_composition_pct": sched6.totals["S6_COMPOSITION_PCT"],
    }
    result.flags = sched5["flags"]  # type: ignore[assignment]
    return result
