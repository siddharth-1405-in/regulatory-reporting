"""Structured result types for the deterministic CAR engine.

These dataclasses are the single structured output consumed by validation,
lineage, export (Excel + PDF) and the API. Money values are SAR '000 as Decimal.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class LineResult:
    """One workbook line (input + its deterministic result)."""
    element_code: str
    label: str
    section: str
    inputs: dict[str, Decimal] = field(default_factory=dict)  # e.g. {"exposure":.., "risk_weight":..}
    result: Decimal = Decimal("0")                            # RWA / charge / net amount


@dataclass
class ScheduleResult:
    sheet_name: str
    lines: list[LineResult] = field(default_factory=list)
    subtotals: dict[str, Decimal] = field(default_factory=dict)   # element_code -> value
    totals: dict[str, Decimal] = field(default_factory=dict)


@dataclass
class CarResult:
    """Full deterministic computation for one report instance."""
    schedules: dict[str, ScheduleResult] = field(default_factory=dict)
    # Flat element_code -> value for every derived metric (lineage / export / API).
    values: dict[str, Decimal] = field(default_factory=dict)
    # Headline metrics convenience view.
    metrics: dict[str, Decimal] = field(default_factory=dict)
    # Buffer / status flags.
    flags: dict[str, str] = field(default_factory=dict)

    def value(self, code: str) -> Decimal:
        return self.values.get(code, Decimal("0"))
