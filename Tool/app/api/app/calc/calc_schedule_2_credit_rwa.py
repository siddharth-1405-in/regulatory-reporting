"""Schedule 2 — Credit Risk RWA, Standardised Approach (deterministic).

    On-balance RWA       = exposure × risk weight
    Off-balance equiv.   = exposure × CCF
    Off-balance RWA      = equivalent × risk weight
    Total credit RWA     = on-balance subtotal + off-balance subtotal

Per-line rates (risk weight, CCF) come from the registry but may be overridden
per instance via `params` (element_code.risk_weight / element_code.ccf).
"""
from __future__ import annotations

from decimal import Decimal

from ..registry.car_sa01 import elements as reg
from .types import LineResult, ScheduleResult

Z = Decimal("0")


def _rate(params: dict[str, Decimal], key: str, default: Decimal) -> Decimal:
    return params.get(key, default)


def compute(inputs: dict[str, Decimal], params: dict[str, Decimal] | None = None) -> ScheduleResult:
    params = params or {}
    sched = ScheduleResult(sheet_name="Schedule 2")

    onbal_rwa = Z
    for code in reg.codes_by_kind("credit_onbal"):
        e = reg.get(code)
        exposure = inputs.get(code, Z)
        rw = _rate(params, f"{code}.risk_weight", e.rate)
        rwa = exposure * rw
        onbal_rwa += rwa
        sched.lines.append(LineResult(code, e.label, e.section_name,
                                       {"exposure": exposure, "risk_weight": rw}, rwa))

    offbal_rwa = Z
    for code in reg.codes_by_kind("credit_offbal"):
        e = reg.get(code)
        exposure = inputs.get(code, Z)
        ccf = _rate(params, f"{code}.ccf", e.ccf)
        rw = _rate(params, f"{code}.risk_weight", e.rate)
        equivalent = exposure * ccf
        rwa = equivalent * rw
        offbal_rwa += rwa
        sched.lines.append(LineResult(code, e.label, e.section_name,
                                       {"exposure": exposure, "ccf": ccf,
                                        "equivalent": equivalent, "risk_weight": rw}, rwa))

    sched.subtotals = {"S2_ONBAL_RWA": onbal_rwa, "S2_OFFBAL_RWA": offbal_rwa}
    sched.totals = {"S2_CREDIT_RWA": onbal_rwa + offbal_rwa}
    return sched
