"""Schedule 4 — Operational Risk Capital Charge, TSA (deterministic).

    Average gross income = mean of 3 years (per business line)
    Capital charge       = average gross income × beta
    Operational risk RWA = total capital charge × 12.5
"""
from __future__ import annotations

from decimal import Decimal

from ..registry.car_sa01 import elements as reg
from ..registry.car_sa01.parameters import RWA_FACTOR
from .types import LineResult, ScheduleResult

Z = Decimal("0")
THREE = Decimal("3")


def compute(inputs: dict[str, Decimal], params: dict[str, Decimal] | None = None) -> ScheduleResult:
    params = params or {}
    sched = ScheduleResult(sheet_name="Schedule 4")
    total_charge = Z

    for base, label, (y1, y2, y3), beta_default, _row in reg.S4_BUSINESS_LINES:
        gi1, gi2, gi3 = inputs.get(y1, Z), inputs.get(y2, Z), inputs.get(y3, Z)
        avg = (gi1 + gi2 + gi3) / THREE
        beta = params.get(f"{base}.beta", beta_default)
        charge = avg * beta
        total_charge += charge
        sched.lines.append(LineResult(base, label, "Operational Risk",
                                       {"gi_y1": gi1, "gi_y2": gi2, "gi_y3": gi3,
                                        "avg_gross_income": avg, "beta": beta}, charge))

    oprisk_rwa = total_charge * RWA_FACTOR
    sched.subtotals = {"S4_OPRISK_CHARGE": total_charge}
    sched.totals = {"S4_OPRISK_RWA": oprisk_rwa}
    return sched
