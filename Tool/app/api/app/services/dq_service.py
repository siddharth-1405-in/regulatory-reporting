"""Data quality checks on ingested input values (pre-calculation)."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from ..models import DQFinding
from ..registry.car_sa01 import elements as reg

Z = Decimal("0")


def run(db: Session, instance_id: int, inputs: dict[str, Decimal]) -> list[DQFinding]:
    db.query(DQFinding).filter(DQFinding.instance_id == instance_id).delete()
    findings: list[DQFinding] = []

    def add(severity, message, code=None):
        f = DQFinding(instance_id=instance_id, element_code=code,
                      severity=severity, message=message)
        db.add(f)
        findings.append(f)

    # negative exposures / charges (Schedule 2 / 3 inputs should be non-negative)
    for code, val in inputs.items():
        e = reg.REGISTRY.get(code)
        if e and e.kind in ("credit_onbal", "credit_offbal", "market_rate",
                            "market_direct", "oprisk_gi") and val < Z:
            add("error", f"Negative value for {e.label} ({code}).", code)

    # operational risk: all 3 years should be present if any are
    for base, label, (y1, y2, y3), _beta, _row in reg.S4_BUSINESS_LINES:
        vals = [inputs.get(y1, Z), inputs.get(y2, Z), inputs.get(y3, Z)]
        if any(v != Z for v in vals) and any(v == Z for v in vals):
            add("warn", f"{label}: incomplete 3-year gross income series.", base)

    # at least some capital and some RWA inputs present
    if all(inputs.get(c, Z) == Z for c in reg.codes_by_kind("cet1_gross")):
        add("error", "No CET1 capital inputs provided (Schedule 1).")
    if all(inputs.get(c, Z) == Z for c in reg.codes_by_kind("credit_onbal")):
        add("warn", "No on-balance-sheet credit exposures provided (Schedule 2).")

    if not findings:
        add("info", "All data quality checks passed.")
    db.flush()
    return findings
