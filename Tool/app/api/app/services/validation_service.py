"""Validation engine — deterministic integrity and compliance checks.

Produces ValidationResult rows from a CarResult. Includes the concentration
rule that surfaces the seeded Schedule 2 anomaly, plus the buffer / minimum
ratio checks that the anomaly trips.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from ..calc.types import CarResult
from ..models import ReportInstance, ValidationResult

Z = Decimal("0")
CONCENTRATION_THRESHOLD = Decimal("0.30")  # single credit line > 30% of credit RWA


def _approx(a: Decimal, b: Decimal, tol: Decimal = Decimal("0.01")) -> bool:
    return abs(a - b) <= tol


def evaluate(instance: ReportInstance, result: CarResult) -> list[dict]:
    """Return a list of {rule_code, status, message, elements, remediation_hint}."""
    v = result.value
    out: list[dict] = []

    def add(rule, status, message, elements=None, hint=""):
        out.append({"rule_code": rule, "status": status, "message": message,
                    "elements": elements or [], "remediation_hint": hint})

    # 1. Cover completeness
    if instance.bank_name and instance.period_end:
        add("COVER_COMPLETE", "pass", "Cover identification fields are complete.")
    else:
        add("COVER_COMPLETE", "fail", "Cover is missing bank name or reporting period.",
            hint="Complete the Cover sheet before submission.")

    # 2-5. RWA integrity (totals reconcile to components)
    credit = v("S2_CREDIT_RWA"); market = v("S3_MARKET_RWA"); op = v("S4_OPRISK_RWA")
    if _approx(v("S2_ONBAL_RWA") + v("S2_OFFBAL_RWA"), credit):
        add("CREDIT_RWA_INTEGRITY", "pass", "Credit RWA equals on- plus off-balance subtotals.")
    else:
        add("CREDIT_RWA_INTEGRITY", "fail", "Credit RWA does not equal its subtotals.",
            ["S2_CREDIT_RWA"])
    if _approx(v("S3_MARKET_CHARGE") * Decimal("12.5"), market):
        add("MARKET_RWA_INTEGRITY", "pass", "Market RWA equals capital charge × 12.5.")
    else:
        add("MARKET_RWA_INTEGRITY", "fail", "Market RWA ≠ charge × 12.5.", ["S3_MARKET_RWA"])
    if _approx(v("S4_OPRISK_CHARGE") * Decimal("12.5"), op):
        add("OPRISK_RWA_INTEGRITY", "pass", "Operational RWA equals capital charge × 12.5.")
    else:
        add("OPRISK_RWA_INTEGRITY", "fail", "Operational RWA ≠ charge × 12.5.", ["S4_OPRISK_RWA"])
    if _approx(credit + market + op, v("SUM_TOTAL_RWA")):
        add("TOTAL_RWA_INTEGRITY", "pass", "Total RWA equals credit + market + operational.")
    else:
        add("TOTAL_RWA_INTEGRITY", "fail", "Total RWA ≠ sum of components.", ["SUM_TOTAL_RWA"])

    # 6. Ratio consistency
    total_rwa = v("SUM_TOTAL_RWA")
    if total_rwa and _approx(v("S1_CET1_NET") / total_rwa, v("SUM_CET1_RATIO"), Decimal("0.0001")):
        add("RATIO_CONSISTENCY", "pass", "Capital ratios are consistent with capital ÷ Total RWA.")
    else:
        add("RATIO_CONSISTENCY", "warn", "Capital ratios could not be reconciled.", ["SUM_CET1_RATIO"])

    # 7. Capital ratio minimums (SAMA)
    breaches = []
    for code, minimum, label in (("SUM_CET1_RATIO", "SUM_MIN_CET1", "CET1"),
                                 ("SUM_TIER1_RATIO", "SUM_MIN_TIER1", "Tier 1"),
                                 ("SUM_TOTAL_RATIO", "SUM_MIN_TOTAL", "Total Capital")):
        if v(code) < v(minimum):
            breaches.append(label)
    if breaches:
        add("CAPITAL_RATIO_MINIMUMS", "fail",
            f"Below SAMA minimum on: {', '.join(breaches)}.",
            ["SUM_CET1_RATIO", "SUM_TIER1_RATIO", "SUM_TOTAL_RATIO"],
            hint="Verify RWA inputs (esp. Schedule 2) and capital composition.")
    else:
        add("CAPITAL_RATIO_MINIMUMS", "pass", "All capital ratios meet SAMA minimums.")

    # 8. Buffer consistency
    if result.flags.get("buffer_status") == "Compliant":
        add("BUFFER_CONSISTENCY", "pass", "Combined capital buffer requirement is met.")
    else:
        add("BUFFER_CONSISTENCY", "fail",
            "Combined buffer requirement breached — CET1 below buffer threshold.",
            ["S5_CET1_SURPLUS"], hint="Investigate inflated RWA or capital shortfall.")

    # 9. Schedule 6 nil reconciliation
    if _approx(v("S6_RECON_DIFF"), Z):
        add("S6_NIL_RECONCILIATION", "pass", "Capital reconciliation difference is nil.")
    else:
        add("S6_NIL_RECONCILIATION", "fail",
            f"Reconciliation difference is {v('S6_RECON_DIFF')}, expected nil.",
            ["S6_RECON_DIFF"])

    # 10. RWA composition = 100%
    if _approx(v("S6_COMPOSITION_PCT"), Decimal("1"), Decimal("0.0001")):
        add("RWA_COMPOSITION_100", "pass", "RWA composition totals 100%.")
    else:
        add("RWA_COMPOSITION_100", "fail", "RWA composition does not total 100%.", ["S6_COMPOSITION_PCT"])

    # 11. Concentration anomaly (catches the seeded Schedule 2 error)
    sched2 = result.schedules.get("Schedule 2")
    if sched2 and credit > 0:
        flagged = [(l.element_code, l.result) for l in sched2.lines
                   if l.result / credit > CONCENTRATION_THRESHOLD]
        if flagged:
            codes = [c for c, _ in flagged]
            add("CREDIT_CONCENTRATION_ANOMALY", "fail",
                "One or more credit exposure classes exceed 30% of total credit RWA — "
                "possible data error or genuine concentration.",
                codes, hint="Confirm the exposure amount and risk weight for the flagged class.")
        else:
            add("CREDIT_CONCENTRATION_ANOMALY", "pass",
                "No single credit class exceeds the 30% concentration threshold.")

    return out


def persist(db: Session, *, instance_id: int, calc_run_id: int,
            results: list[dict]) -> list[ValidationResult]:
    db.query(ValidationResult).filter(ValidationResult.instance_id == instance_id).delete()
    rows = []
    for r in results:
        row = ValidationResult(instance_id=instance_id, calc_run_id=calc_run_id,
                               rule_code=r["rule_code"], status=r["status"],
                               message=r["message"], elements=r["elements"],
                               remediation_hint=r["remediation_hint"])
        db.add(row)
        rows.append(row)
    db.flush()
    return rows
