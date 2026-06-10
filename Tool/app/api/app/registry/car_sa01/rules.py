"""Rule-engine semantics for CAR-SA-01 — plain-English rules + machine structure.

Each canonical element carries a transformation rule keyed off its registry
`kind`. The plain-English text is for the UI; the editable parameters
(risk weight / CCF / beta) map to `config_service` keys so editing a rule
persists an override and triggers auto-recompute.
"""
from __future__ import annotations

from decimal import Decimal

from . import elements as reg


def _pct(x) -> str:
    return f"{Decimal(str(x)) * 100:.2f}%".replace(".00%", "%")


def _base_line(code: str) -> str:
    # S4_RETAIL_BANKING_GI_Y1 -> S4_RETAIL_BANKING
    for suffix in ("_GI_Y1", "_GI_Y2", "_GI_Y3"):
        if code.endswith(suffix):
            return code[: -len(suffix)]
    return code


def rule_for(code: str, *, risk_weight=None, ccf=None, beta=None) -> dict:
    e = reg.REGISTRY.get(code)
    if e is None:
        return {}
    kind = e.kind
    rw = risk_weight if risk_weight is not None else e.rate
    cf = ccf if ccf is not None else e.ccf
    params: list[dict] = []
    origin = "SAMA Basel III standardised approach"

    if kind == "cet1_gross":
        rtype, name = "aggregation", "CET1 recognition"
        text = "Recognised as Common Equity Tier 1 and summed into CET1 before regulatory deductions."
    elif kind == "cet1_deduction":
        rtype, name = "adjustment", "CET1 deduction"
        text = "Deducted from CET1 capital per SAMA Basel III regulatory adjustments."
    elif kind == "at1_gross":
        rtype, name = "aggregation", "AT1 recognition"
        text = "Recognised as Additional Tier 1 capital and added to the AT1 total."
    elif kind == "at1_deduction":
        rtype, name = "adjustment", "AT1 deduction"
        text = "Deducted from Additional Tier 1 capital."
    elif kind == "t2_gross":
        rtype, name = "aggregation", "Tier 2 recognition"
        text = "Recognised as Tier 2 capital and added to the Tier 2 total."
    elif kind == "t2_deduction":
        rtype, name = "adjustment", "Tier 2 deduction"
        text = "Deducted from Tier 2 capital."
    elif kind == "credit_onbal":
        rtype, name = "risk_weight", "Standardised risk weight"
        origin = "Risk-weight bucket from Moody's Analytics ratings"
        text = f"On-balance exposure risk-weighted at {_pct(rw)} → RWA = exposure × {_pct(rw)}."
        params = [{"key": f"{code}.risk_weight", "label": "Risk weight", "value": float(rw), "format": "pct"}]
    elif kind == "credit_offbal":
        rtype, name = "ccf_risk_weight", "CCF + risk weight"
        text = (f"Off-balance exposure converted at {_pct(cf)} CCF, then risk-weighted at "
                f"{_pct(rw)} → RWA = exposure × CCF × risk weight.")
        params = [{"key": f"{code}.ccf", "label": "CCF", "value": float(cf), "format": "pct"},
                  {"key": f"{code}.risk_weight", "label": "Risk weight", "value": float(rw), "format": "pct"}]
    elif kind == "market_rate":
        rtype, name = "market_charge", "Market-risk capital charge"
        text = f"Capital charge = net position × {_pct(rw)}; Market-risk RWA = charge × 12.5."
        params = [{"key": f"{code}.charge_rate", "label": "Charge rate", "value": float(rw), "format": "pct"}]
    elif kind == "market_direct":
        rtype, name = "market_charge", "Direct capital charge"
        text = "Capital charge taken directly from the standardised model; RWA = charge × 12.5."
    elif kind == "oprisk_gi":
        base = _base_line(code)
        b = beta if beta is not None else e.rate
        rtype, name = "operational", "Operational-risk beta"
        origin = "TSA business-line beta (SAS Risk)"
        text = f"3-year average gross income × beta {_pct(b)}; Operational-risk RWA = charge × 12.5."
        params = [{"key": f"{base}.beta", "label": "Beta", "value": float(b), "format": "pct"}]
    elif kind in ("recon_fs", "recon_adj"):
        rtype, name = "reconciliation", "FS reconciliation"
        text = "Reconciles published financial-statement equity to regulatory capital (difference must be nil)."
    else:
        rtype, name = "aggregation", "Derived"
        text = "Derived deterministically from upstream certified elements."

    return {"rule_name": name, "rule_type": rtype, "plain_english": text,
            "editable_params": params, "origin": origin, "editable": bool(params)}


# ---- business meaning (concise English) -------------------------------------
_MEANING_SPECIFIC = {
    "S1_CET1_PAIDUP": "Core paid-up ordinary equity — the highest quality of regulatory capital.",
    "S1_CET1_RETAINED": "Accumulated retained earnings available to absorb losses as CET1.",
    "S1_CET1D_GOODWILL": "Goodwill is fully deducted from CET1 as it cannot absorb losses.",
    "S2_ON_CORP_BBB": "Lending to mid-rated corporates; risk-weighted at 100% under the standardised approach.",
    "S2_ON_RETAIL": "Regulatory retail portfolio benefiting from the 75% preferential risk weight.",
    "S2_ON_RRE_LOW": "Low-LTV residential mortgages attracting a 35% risk weight.",
    "S3_FX_NETOPEN": "Net open FX position carrying market risk capital at 8%.",
    "S4_RETAIL_BANKING_GI_Y1": "Retail banking gross income feeding the operational-risk capital charge.",
}
_MEANING_BY_KIND = {
    "cet1_gross": "Component of Common Equity Tier 1 capital.",
    "cet1_deduction": "Regulatory deduction reducing CET1 capital.",
    "at1_gross": "Additional Tier 1 capital instrument.",
    "at1_deduction": "Deduction from Additional Tier 1 capital.",
    "t2_gross": "Tier 2 capital instrument or eligible reserve.",
    "t2_deduction": "Deduction from Tier 2 capital.",
    "credit_onbal": "On-balance-sheet credit exposure contributing to credit-risk RWA.",
    "credit_offbal": "Off-balance-sheet credit exposure converted via CCF into credit-risk RWA.",
    "market_rate": "Market-risk position attracting a standardised capital charge.",
    "market_direct": "Market-risk capital charge taken directly from the standardised model.",
    "oprisk_gi": "Business-line gross income driving the operational-risk capital charge.",
    "recon_fs": "Published financial-statement figure used in the capital reconciliation.",
    "recon_adj": "Regulatory adjustment bridging published equity to regulatory capital.",
}


def business_meaning(code: str) -> str:
    if code in _MEANING_SPECIFIC:
        return _MEANING_SPECIFIC[code]
    e = reg.REGISTRY.get(code)
    return _MEANING_BY_KIND.get(e.kind if e else "", e.label if e else code)
