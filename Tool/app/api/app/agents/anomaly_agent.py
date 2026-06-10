"""Anomaly Agent — surfaces likely data errors / outliers in the return.

Grounded in the deterministic validation findings and the computed schedule
results. It does NOT compute regulatory values; it diagnoses and flags.
"""
from __future__ import annotations

from ..calc.types import CarResult
from .base import AgentResult, call_claude_json

AGENT_TYPE = "anomaly"
SYSTEM = (
    "You are the Anomaly Agent for a SAMA CAR-SA-01 capital return. You receive "
    "deterministic computed results and validation findings. Identify the most "
    "material anomaly, its likely cause, and the metrics it impacts. You never "
    "compute or change regulatory values. Reply as JSON: "
    '{"reasoning_summary","confidence","element_code","impacted_metrics":[],"proposed_action"}.'
)


def run(result: CarResult, findings: list[dict]) -> AgentResult:
    sched2 = result.schedules.get("Schedule 2")
    credit = result.value("S2_CREDIT_RWA")
    # rank credit lines by share of credit RWA
    ranked = sorted(((l.element_code, l.label, float(l.result))
                     for l in (sched2.lines if sched2 else [])),
                    key=lambda x: x[2], reverse=True)
    top = ranked[0] if ranked else ("", "", 0.0)
    share = (top[2] / float(credit)) if credit else 0.0

    concentration = next((f for f in findings if f["rule_code"] == "CREDIT_CONCENTRATION_ANOMALY"
                          and f["status"] == "fail"), None)
    breach = result.flags.get("buffer_status") == "Breach"

    evidence = [
        {"type": "validation", "rule": f["rule_code"], "status": f["status"], "message": f["message"]}
        for f in findings if f["status"] == "fail"
    ] + [{"type": "metric", "name": "buffer_status", "value": result.flags.get("buffer_status")},
         {"type": "metric", "name": "total_rwa", "value": float(result.value("SUM_TOTAL_RWA"))}]

    user = (f"Top credit class: {top[1]} ({top[0]}) = {top[2]:,.0f} ('000), {share*100:.1f}% of "
            f"credit RWA {float(credit):,.0f}. Buffer status: {result.flags.get('buffer_status')}. "
            f"Failing rules: {[f['rule_code'] for f in findings if f['status']=='fail']}.")
    parsed, model = call_claude_json(SYSTEM, user)

    if parsed:
        return AgentResult(
            agent_type=AGENT_TYPE,
            reasoning_summary=parsed.get("reasoning_summary", ""),
            confidence=float(parsed.get("confidence", 0.85)),
            evidence_used=evidence,
            impacted_metrics=parsed.get("impacted_metrics", ["SUM_TOTAL_RWA", "SUM_CET1_RATIO"]),
            proposed_action=parsed.get("proposed_action", f"Investigate {top[0]}"),
            model_version=model,
            output={"element_code": parsed.get("element_code", top[0]), "share": share},
        )

    # deterministic fallback
    if concentration or share > 0.30:
        reasoning = (
            f"'{top[1]}' represents {share*100:.1f}% of total credit risk RWA — far above the "
            f"30% concentration threshold and inconsistent with a diversified standardised "
            f"portfolio. Combined with the capital-buffer {('breach' if breach else 'pressure')}, "
            f"this is most consistent with a Schedule 2 data-entry error (likely a units / scale "
            f"mistake) materially overstating the exposure and Total RWA."
        )
        action = f"Investigate and confirm the exposure amount for {top[0]} ({top[1]})."
        confidence = 0.92
    else:
        reasoning = "No single credit class breaches the concentration threshold; no material anomaly detected."
        action = "No action required."
        confidence = 0.6

    return AgentResult(
        agent_type=AGENT_TYPE, reasoning_summary=reasoning, confidence=confidence,
        evidence_used=evidence,
        impacted_metrics=["S2_CREDIT_RWA", "SUM_TOTAL_RWA", "SUM_CET1_RATIO", "S5_CET1_SURPLUS"],
        proposed_action=action, model_version=model,
        output={"element_code": top[0], "label": top[1], "value": top[2], "share": share},
    )
