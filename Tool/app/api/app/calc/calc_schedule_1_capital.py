"""Schedule 1 — Regulatory Capital Composition (deterministic).

Formulas (docs/TDD.md):
    Net CET1   = CET1 subtotal - CET1 deductions
    Total AT1  = AT1 gross - AT1 deductions
    Total T1   = Net CET1 + Total AT1
    Total T2   = Tier 2 gross - Tier 2 deductions
    Total cap  = Total T1 + Total T2
"""
from __future__ import annotations

from decimal import Decimal

from ..registry.car_sa01 import elements as reg
from .types import LineResult, ScheduleResult

Z = Decimal("0")


def _g(inputs: dict[str, Decimal], code: str) -> Decimal:
    return inputs.get(code, Z)


def _sum(inputs: dict[str, Decimal], codes: list[str]) -> Decimal:
    return sum((_g(inputs, c) for c in codes), Z)


def compute(inputs: dict[str, Decimal]) -> ScheduleResult:
    cet1_gross = reg.codes_by_kind("cet1_gross")
    cet1_deduct = reg.codes_by_kind("cet1_deduction")
    at1_gross = reg.codes_by_kind("at1_gross")
    at1_deduct = reg.codes_by_kind("at1_deduction")
    t2_gross = reg.codes_by_kind("t2_gross")
    t2_deduct = reg.codes_by_kind("t2_deduction")

    cet1_subtotal = _sum(inputs, cet1_gross)
    cet1_deduct_total = _sum(inputs, cet1_deduct)
    cet1_net = cet1_subtotal - cet1_deduct_total

    at1_total = _sum(inputs, at1_gross) - _sum(inputs, at1_deduct)
    tier1_total = cet1_net + at1_total

    t2_total = _sum(inputs, t2_gross) - _sum(inputs, t2_deduct)
    total_capital = tier1_total + t2_total

    sched = ScheduleResult(sheet_name="Schedule 1")
    for code in cet1_gross + cet1_deduct + at1_gross + at1_deduct + t2_gross + t2_deduct:
        e = reg.get(code)
        sched.lines.append(LineResult(code, e.label, e.section_name,
                                       {"amount": _g(inputs, code)}, _g(inputs, code)))
    sched.subtotals = {
        "S1_CET1_SUBTOTAL": cet1_subtotal,
        "S1_CET1_DEDUCT_TOTAL": cet1_deduct_total,
    }
    sched.totals = {
        "S1_CET1_NET": cet1_net,
        "S1_AT1_TOTAL": at1_total,
        "S1_TIER1_TOTAL": tier1_total,
        "S1_T2_TOTAL": t2_total,
        "S1_TOTAL_CAPITAL": total_capital,
    }
    return sched
