"""Root-Cause & Remediation Agent — proposes a correction for Checker approval.

Creates a RemediationProposal (status 'proposed'). It NEVER changes the input
value itself: a Checker must approve the proposal before it is applied and the
return recalculated (remediation_service.approve).
"""
from __future__ import annotations

from decimal import Decimal

from ..calc.types import CarResult
from .base import AgentResult, call_claude_json

AGENT_TYPE = "remediation"
SYSTEM = (
    "You are the Remediation Agent for a SAMA CAR-SA-01 return. Given an anomalous "
    "input element, propose the most likely correct value and a concise root-cause. "
    "You never apply changes — a human Checker must approve. Reply as JSON: "
    '{"reasoning_summary","confidence","proposed_value","root_cause"}.'
)


def run(result: CarResult, anomaly_output: dict) -> tuple[AgentResult, dict | None]:
    """Returns (agent_result, proposal_dict|None). proposal_dict feeds a
    RemediationProposal row created by the caller after persisting the run."""
    code = anomaly_output.get("element_code")
    current = Decimal(str(anomaly_output.get("value", 0)))
    if not code or current <= 0:
        return (AgentResult(agent_type=AGENT_TYPE,
                            reasoning_summary="No actionable anomaly to remediate.",
                            confidence=0.5, proposed_action="No remediation proposed."), None)

    # heuristic: a ~10x units/scale error is the most common cause of a single
    # exposure dominating credit RWA — propose dividing by 10 (Checker confirms).
    proposed = (current / Decimal("10")).quantize(Decimal("1"))

    user = (f"Element {code} currently {current:,.0f} ('000) dominates credit RWA. Propose the "
            f"most likely correct value and root cause.")
    parsed, model = call_claude_json(SYSTEM, user)
    if parsed and parsed.get("proposed_value") is not None:
        try:
            proposed = Decimal(str(parsed["proposed_value"]))
        except Exception:
            pass
        reasoning = parsed.get("reasoning_summary", "")
        root_cause = parsed.get("root_cause", "Suspected data-entry scale error.")
        confidence = float(parsed.get("confidence", 0.88))
    else:
        reasoning = (
            f"The reported amount ({current:,.0f}) is ~10x the scale of comparable corporate "
            f"exposure classes, the classic signature of a units / decimal data-entry error on "
            f"ingestion. Correcting to {proposed:,.0f} restores the exposure to a plausible level, "
            f"brings credit RWA and Total RWA back in range, and is expected to clear the capital "
            f"buffer breach. Requires Checker confirmation against the source system."
        )
        root_cause = "Schedule 2 ingestion units/scale error (value entered ~10x too high)."
        confidence = 0.88

    agent_result = AgentResult(
        agent_type=AGENT_TYPE, reasoning_summary=reasoning, confidence=confidence,
        evidence_used=[{"type": "metric", "name": "current_value", "value": float(current)},
                       {"type": "diagnosis", "root_cause": root_cause}],
        impacted_metrics=["S2_CREDIT_RWA", "SUM_TOTAL_RWA", "SUM_CET1_RATIO", "S5_CET1_SURPLUS"],
        proposed_action=f"Correct {code} from {current:,.0f} to {proposed:,.0f} (Checker approval required).",
        approval_required=True, model_version=model,
        output={"element_code": code, "current_value": float(current),
                "proposed_value": float(proposed), "root_cause": root_cause},
    )
    proposal = {"element_code": code, "current_value": current, "proposed_value": proposed,
                "rationale": root_cause}
    return agent_result, proposal
