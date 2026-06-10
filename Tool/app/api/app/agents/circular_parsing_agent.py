"""Circular Parsing Agent — maps a regulatory circular to impacted CAR elements.

Reads a circular / change-log entry and proposes which CAR schedules and
canonical elements are affected. Advisory only — informs the change backlog;
any parameter change still flows through config + Checker approval.
"""
from __future__ import annotations

from ..registry.car_sa01 import elements as reg
from .base import AgentResult, call_claude_json

AGENT_TYPE = "circular_parsing"
SYSTEM = (
    "You are the Circular Parsing Agent for SAMA/CBUAE/AAOIFI regulatory changes. "
    "Given a circular description, identify which CAR-SA-01 schedules and element "
    "codes are likely impacted and the nature of the impact. Reply as JSON: "
    '{"reasoning_summary","confidence","impacted_schedules":[],"impacted_elements":[]}.'
)

# deterministic keyword -> impacted (schedule, element_code prefixes) heuristics
_KEYWORDS = {
    "sukuk": (["Schedule 2", "Schedule 1"], ["S2_ON_CORP_BBB", "S1_T2_INSTRUMENTS"]),
    "rwa": (["Schedule 2"], ["S2_CREDIT_RWA"]),
    "capital": (["Schedule 1"], ["S1_TOTAL_CAPITAL"]),
    "operational": (["Schedule 4"], ["S4_OPRISK_RWA"]),
    "market": (["Schedule 3"], ["S3_MARKET_RWA"]),
    "income": (["Schedule 4"], ["S4_RETAIL_BANKING_GI_Y1"]),
}


def run(circular: dict) -> AgentResult:
    text = f"{circular.get('standard','')} {circular.get('description','')} " \
           f"{circular.get('affected_elements','')}".lower()
    parsed, model = call_claude_json(SYSTEM, str(circular))

    if parsed:
        impacted_sched = parsed.get("impacted_schedules", [])
        impacted_elems = [c for c in parsed.get("impacted_elements", []) if c in reg.REGISTRY]
        reasoning = parsed.get("reasoning_summary", "")
        confidence = float(parsed.get("confidence", 0.8))
    else:
        scheds, elems = set(), set()
        for kw, (s, e) in _KEYWORDS.items():
            if kw in text:
                scheds.update(s)
                elems.update(c for c in e if c in reg.REGISTRY)
        impacted_sched, impacted_elems = sorted(scheds), sorted(elems)
        reasoning = (
            f"Circular '{circular.get('standard','')}' references "
            f"{circular.get('affected_elements','') or 'CAR data elements'}; "
            f"mapped to {len(impacted_sched)} schedule(s) by classification rules. "
            f"Recommend impact review before the next reporting period."
        ) if impacted_sched else "No CAR-SA-01 elements clearly impacted by this circular."
        confidence = 0.78 if impacted_sched else 0.5

    return AgentResult(
        agent_type=AGENT_TYPE, reasoning_summary=reasoning, confidence=confidence,
        evidence_used=[{"type": "circular", "standard": circular.get("standard"),
                        "regulator": circular.get("regulator"),
                        "affected_elements": circular.get("affected_elements")}],
        impacted_metrics=impacted_elems,
        proposed_action="Add to regulatory change backlog; assess parameter/treatment impact.",
        model_version=model,
        output={"impacted_schedules": impacted_sched, "impacted_elements": impacted_elems},
    )
