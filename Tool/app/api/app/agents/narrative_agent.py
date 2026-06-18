"""Narrative Agent — drafts EN + AR executive narrative with citations.

Drafts only; a Checker approves before the narrative is finalised/sent. Numbers
quoted come verbatim from the deterministic result (never invented). The tone is
written for a CFO / Board capital pack: a clear adequacy verdict, buffer headroom
in basis points, the principal RWA drivers, reconciliation integrity and the
distribution implication.
"""
from __future__ import annotations

from ..calc.types import CarResult
from .base import AgentResult, call_claude_json

AGENT_TYPE = "narrative"
SYSTEM = (
    "You are the Narrative Agent preparing the executive commentary for a SAMA "
    "CAR-SA-01 capital adequacy return that will be read by the CFO and the Board. "
    "Write a crisp, decision-useful narrative in BOTH English and Arabic using ONLY "
    "the figures provided — never invent or round away material detail. Cover, in order: "
    "(1) the overall capital adequacy verdict against SAMA minimums; (2) CET1, Tier 1 and "
    "total capital ratios with their headroom over the Pillar 1 minimums; (3) total RWA and "
    "its principal driver (credit vs market vs operational); (4) the combined buffer "
    "requirement and the CET1 surplus or deficit against it, including any dividend-"
    "distribution constraint; (5) reconciliation integrity to the published financials; and "
    "(6) the management implication (capital actions or distribution capacity). Be concise "
    "(roughly 130–180 words), authoritative and free of hedging. Cite schedules in square "
    'brackets, e.g. [Schedule 2]. Reply as JSON: {"en","ar","confidence"}.'
)


def _pct(x: float) -> str:
    return f"{x*100:.2f}%"


def _bps(x: float) -> str:
    return f"{x*10000:,.0f} bps"


def run(result: CarResult) -> tuple[AgentResult, dict]:
    m = result.metrics
    f = result.flags
    compliant = f.get("buffer_status") == "Compliant"
    credit_share = float(m["credit_rwa"]) / float(m["total_rwa"]) if m.get("total_rwa") else 0.0
    facts = {
        "total_rwa": float(m["total_rwa"]),
        "credit_rwa": float(m["credit_rwa"]),
        "market_rwa": float(m["market_rwa"]),
        "oprisk_rwa": float(m["oprisk_rwa"]),
        "credit_rwa_share": round(credit_share, 4),
        "cet1_ratio": float(m["cet1_ratio"]),
        "tier1_ratio": float(m["tier1_ratio"]),
        "total_ratio": float(m["total_ratio"]),
        "cet1_surplus_p1_bps": round((float(m["cet1_ratio"]) - 0.045) * 10000),
        "total_surplus_p1_bps": round((float(m["total_ratio"]) - 0.08) * 10000),
        "combined_buffer": float(m.get("combined_buffer", 0)),
        "cet1_buffer_surplus": float(m.get("cet1_buffer_surplus", 0)),
        "recon_diff": float(m.get("recon_diff", 0)),
        "buffer_status": f.get("buffer_status"),
        "distribution_band": f.get("distribution_band"),
        "max_dividend_payout": f.get("max_dividend_payout"),
    }
    parsed, model = call_claude_json(SYSTEM, str(facts), narrative=True)

    if parsed and parsed.get("en"):
        en, ar = parsed["en"], parsed.get("ar", "")
        confidence = float(parsed.get("confidence", 0.9))
    else:
        verdict = ("remains adequately capitalised and meets all SAMA Pillar 1 minimums and the "
                   "combined capital buffer" if compliant
                   else "breaches the combined capital buffer requirement and falls below the "
                        "SAMA distribution threshold")
        buffer_line = (
            f"The combined buffer requirement is {_pct(facts['combined_buffer'])} of RWA, leaving a "
            f"CET1 {'surplus' if facts['cet1_buffer_surplus'] >= 0 else 'deficit'} of "
            f"{_bps(abs(facts['cet1_buffer_surplus']))} against that requirement [Schedule 5]."
        )
        dist_line = (
            f"On this basis there is no constraint on capital distributions."
            if compliant else
            f"Distributions are therefore constrained (maximum payout: {facts['max_dividend_payout']}), "
            f"and management should prioritise a capital remediation plan."
        )
        recon_line = (
            "Regulatory capital reconciles to the published financial statements with no residual "
            "difference [Schedule 6]." if abs(facts["recon_diff"]) < 1 else
            f"A reconciliation difference of SAR {facts['recon_diff']:,.0f} thousand to the published "
            f"financial statements requires investigation [Schedule 6]."
        )
        en = (
            f"For the reporting period the bank {verdict}. The total capital ratio is "
            f"{_pct(facts['total_ratio'])} (CET1 {_pct(facts['cet1_ratio'])}, Tier 1 "
            f"{_pct(facts['tier1_ratio'])}), {facts['total_surplus_p1_bps']:,} bps above the 8.00% "
            f"Pillar 1 total-capital minimum and {facts['cet1_surplus_p1_bps']:,} bps of CET1 headroom "
            f"[Summary]. Total risk-weighted assets are SAR {facts['total_rwa']:,.0f} thousand, of which "
            f"credit risk represents {_pct(facts['credit_rwa_share'])} (SAR {facts['credit_rwa']:,.0f} "
            f"thousand) and is the principal driver, with market and operational risk contributing the "
            f"balance [Schedule 2][Schedule 3][Schedule 4]. {buffer_line} {recon_line} {dist_line}"
        )
        ar_verdict = ("يتمتع البنك بكفاية رأسمالية ويستوفي جميع الحدود الدنيا للركيزة الأولى والهامش الرأسمالي المجمّع"
                      if compliant else
                      "لا يستوفي البنك متطلب الهامش الرأسمالي المجمّع ويقع دون عتبة التوزيعات لدى ساما")
        ar = (
            f"للفترة المشمولة بالتقرير، {ar_verdict}. بلغت نسبة إجمالي رأس المال "
            f"{_pct(facts['total_ratio'])} (الشق الأول من حقوق الملكية {_pct(facts['cet1_ratio'])}، "
            f"والشق الأول {_pct(facts['tier1_ratio'])}) [الملخص]. بلغت الأصول المرجحة بالمخاطر "
            f"SAR {facts['total_rwa']:,.0f} ألف، ويمثل مخاطر الائتمان "
            f"{_pct(facts['credit_rwa_share'])} منها وهو المحرك الرئيسي [الجدول 2]. "
            f"يبلغ الهامش الرأسمالي المجمّع {_pct(facts['combined_buffer'])} من الأصول المرجحة، "
            f"مع {'فائض' if facts['cet1_buffer_surplus'] >= 0 else 'عجز'} في الشق الأول قدره "
            f"{_bps(abs(facts['cet1_buffer_surplus']))} [الجدول 5]."
        )
        confidence = 0.9

    citations = {"Summary": {"type": "sheet"}, "Schedule 2": {"type": "sheet"},
                 "Schedule 5": {"type": "sheet"}, "Schedule 6": {"type": "sheet"}}
    agent_result = AgentResult(
        agent_type=AGENT_TYPE,
        reasoning_summary="Drafted a CFO/Board-grade bilingual executive narrative from the deterministic results.",
        confidence=confidence,
        evidence_used=[{"type": "metric", "name": k, "value": v} for k, v in facts.items()],
        impacted_metrics=["SUM_TOTAL_RATIO", "SUM_CET1_RATIO", "S5_CET1_SURPLUS", "S6_RECON_DIFF"],
        proposed_action="Review and approve the executive narrative for the Board capital pack.",
        model_version=model,
        output={"en": en, "ar": ar, "citations": citations, "confidence": confidence},
    )
    return agent_result, {"en": en, "ar": ar, "citations": citations, "confidence": confidence}
