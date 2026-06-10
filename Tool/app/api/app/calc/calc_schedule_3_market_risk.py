"""Schedule 3 — Market Risk Capital Charge, Standardised (deterministic).

    Rate lines:   capital charge = position/notional × charge rate
    Direct lines: capital charge = entered amount
    Market risk RWA = total capital charge × 12.5
"""
from __future__ import annotations

from decimal import Decimal

from ..registry.car_sa01 import elements as reg
from ..registry.car_sa01.parameters import RWA_FACTOR
from .types import LineResult, ScheduleResult

Z = Decimal("0")


def compute(inputs: dict[str, Decimal], params: dict[str, Decimal] | None = None) -> ScheduleResult:
    params = params or {}
    sched = ScheduleResult(sheet_name="Schedule 3")
    total_charge = Z

    for code in reg.codes_by_kind("market_rate"):
        e = reg.get(code)
        position = inputs.get(code, Z)
        rate = params.get(f"{code}.charge_rate", e.rate)
        charge = position * rate
        total_charge += charge
        sched.lines.append(LineResult(code, e.label, e.section_name,
                                       {"position": position, "charge_rate": rate}, charge))

    for code in reg.codes_by_kind("market_direct"):
        e = reg.get(code)
        charge = inputs.get(code, Z)
        total_charge += charge
        sched.lines.append(LineResult(code, e.label, e.section_name, {"charge": charge}, charge))

    market_rwa = total_charge * RWA_FACTOR
    sched.subtotals = {"S3_MARKET_CHARGE": total_charge}
    sched.totals = {"S3_MARKET_RWA": market_rwa}
    return sched
