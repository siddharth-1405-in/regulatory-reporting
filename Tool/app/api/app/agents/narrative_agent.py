"""Narrative Agent — drafts EN + AR executive narrative with citations.

Drafts only; a Checker approves before the narrative is finalised/sent. Numbers
quoted come verbatim from the deterministic result (never invented).
"""
from __future__ import annotations

from ..calc.types import CarResult
from .base import AgentResult, call_claude_json

AGENT_TYPE = "narrative"
SYSTEM = (
    "You are the Narrative Agent for a SAMA CAR-SA-01 capital return. Draft a concise "
    "executive narrative (English and Arabic) using ONLY the figures provided. Cite "
    "schedules in square brackets, e.g. [Schedule 2]. Reply as JSON: "
    '{"en","ar","confidence"}.'
)


def _pct(x: float) -> str:
    return f"{x*100:.2f}%"


def run(result: CarResult) -> tuple[AgentResult, dict]:
    m = result.metrics
    f = result.flags
    facts = {
        "total_rwa": float(m["total_rwa"]),
        "cet1_ratio": float(m["cet1_ratio"]),
        "tier1_ratio": float(m["tier1_ratio"]),
        "total_ratio": float(m["total_ratio"]),
        "buffer_status": f.get("buffer_status"),
        "credit_rwa": float(m["credit_rwa"]),
    }
    parsed, model = call_claude_json(SYSTEM, str(facts), narrative=True)

    if parsed and parsed.get("en"):
        en, ar = parsed["en"], parsed.get("ar", "")
        confidence = float(parsed.get("confidence", 0.9))
    else:
        status_en = ("meets all SAMA minimum capital requirements and combined buffer"
                     if facts["buffer_status"] == "Compliant"
                     else "breaches the combined capital buffer requirement")
        en = (
            f"For the reporting period, total risk-weighted assets stood at "
            f"SAR {facts['total_rwa']:,.0f} thousand [Summary], of which credit risk "
            f"contributed SAR {facts['credit_rwa']:,.0f} thousand [Schedule 2]. The bank "
            f"reported a CET1 ratio of {_pct(facts['cet1_ratio'])}, a Tier 1 ratio of "
            f"{_pct(facts['tier1_ratio'])} and a total capital ratio of "
            f"{_pct(facts['total_ratio'])} [Summary]. On this basis the bank {status_en} "
            f"[Schedule 5]."
        )
        ar = (
            f"بلغت الأصول المرجحة بالمخاطر SAR {facts['total_rwa']:,.0f} ألف [الملخص]، "
            f"وبلغت نسبة الشق الأول من رأس المال (CET1) {_pct(facts['cet1_ratio'])} ونسبة "
            f"إجمالي رأس المال {_pct(facts['total_ratio'])} [الملخص]. وعلى هذا الأساس فإن "
            f"البنك {'يستوفي' if facts['buffer_status']=='Compliant' else 'لا يستوفي'} "
            f"متطلبات الهامش الرأسمالي المجمّع [الجدول 5]."
        )
        confidence = 0.9

    citations = {"Summary": {"type": "sheet"}, "Schedule 2": {"type": "sheet"},
                 "Schedule 5": {"type": "sheet"}}
    agent_result = AgentResult(
        agent_type=AGENT_TYPE,
        reasoning_summary="Drafted bilingual executive narrative from deterministic results.",
        confidence=confidence,
        evidence_used=[{"type": "metric", "name": k, "value": v} for k, v in facts.items()],
        impacted_metrics=["SUM_CET1_RATIO", "SUM_TOTAL_RATIO", "S5_CET1_SURPLUS"],
        proposed_action="Review and approve narrative for the Board capital pack.",
        model_version=model,
        output={"en": en, "ar": ar, "citations": citations, "confidence": confidence},
    )
    return agent_result, {"en": en, "ar": ar, "citations": citations, "confidence": confidence}
