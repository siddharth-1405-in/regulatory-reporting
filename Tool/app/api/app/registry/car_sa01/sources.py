"""Enterprise source-system catalogue and element→source mapping for CAR-SA-01.

Realistic named vendor systems (not abstract "core banking"). The mapping is the
product's view of where each canonical CAR data element originates. Some systems
(Moody's, SAS, Collateral) contribute rule inputs (ratings, aggregation,
coverage) rather than being the primary record — that is reflected in their
`coverage` description and surfaced in the rule text.
"""
from __future__ import annotations

from . import elements as reg

# ---- catalogue --------------------------------------------------------------
# code, name, vendor, category, used_in_car, steward, coverage, freshness_hours
SOURCE_CATALOGUE = [
    ("SAP_S4", "SAP S/4HANA", "SAP", "ERP / General Ledger", True, "CFO Office — Finance Control",
     "Capital composition, gross income, published-FS equity", 6),
    ("ORACLE_FCCS", "Oracle FCCS", "Oracle", "Financial Consolidation", True, "Group Reporting",
     "Consolidation, minority interest, regulatory adjustments (Schedule 6)", 12),
    ("MUREX", "Murex MX.3", "Murex", "Treasury & Trading", True, "Head of Treasury",
     "AT1 / Tier 2 instruments, market-risk positions (Schedule 3)", 2),
    ("FINASTRA", "Finastra Fusion", "Finastra", "Core Lending / Trade Finance", True, "CRO Office — Credit",
     "On- and off-balance credit exposures (Schedule 2)", 6),
    ("MOODYS", "Moody's Analytics", "Moody's", "Ratings & Credit Risk", True, "CRO Office — Credit Risk",
     "External ratings driving standardised risk-weight buckets", 24),
    ("SAS_RISK", "SAS Risk", "SAS", "Risk Analytics", True, "CRO Office — Risk Analytics",
     "RWA aggregation and operational-risk capital charge", 4),
    ("COLLATERAL", "Collateral Management System", "In-house", "Collateral & CRM", True, "CRO Office — Collateral",
     "Secured-exposure LTV and past-due provision coverage", 8),
    ("TEMENOS", "Temenos Transact", "Temenos", "Core Banking", False, "Retail Banking Ops",
     "Available — not used in the CAR demo", 6),
    ("BLOOMBERG", "Bloomberg", "Bloomberg", "Market Data", False, "Front Office",
     "Available — market data / FX rates", 1),
    ("DYNAMICS", "Microsoft Dynamics 365", "Microsoft", "ERP", False, "Finance",
     "Available — not used in the CAR demo", 12),
]

CATALOGUE_BY_CODE = {c[0]: c for c in SOURCE_CATALOGUE}


def _primary(code: str) -> str:
    """Primary system of record for an element_code (used for ingestion)."""
    e = reg.REGISTRY.get(code)
    kind = e.kind if e else None
    if code.startswith(("S1_AT1", "S1_T2")):
        return "MUREX"
    if code.startswith("S1_"):
        return "SAP_S4"
    if code.startswith("S4_"):
        return "SAP_S4"
    if code.endswith("_ADJ") or "MINORITY" in code:
        return "ORACLE_FCCS"
    if code.startswith("S6_"):
        return "SAP_S4"
    if kind in ("credit_onbal", "credit_offbal"):
        return "FINASTRA"
    if kind in ("market_rate", "market_direct"):
        return "MUREX"
    if kind == "oprisk_gi":
        return "SAP_S4"
    return "SAP_S4"


def source_for(code: str) -> dict:
    sys_code = _primary(code)
    name = CATALOGUE_BY_CODE[sys_code][1]
    # plausible dataset.field reference
    e = reg.REGISTRY.get(code)
    dataset = {
        "SAP_S4": "GL.BALANCES", "ORACLE_FCCS": "FCCS.CONSOL", "MUREX": "MX.POSITIONS",
        "FINASTRA": "FUSION.EXPOSURES", "MOODYS": "RATINGS.MASTER",
    }.get(sys_code, "GL.BALANCES")
    return {"source_code": sys_code, "source_name": name,
            "source_field": f"{dataset}::{code}",
            "sheet": e.sheet_name if e else None}


def catalogue_dicts() -> list[dict]:
    out = []
    for code, name, vendor, cat, used, steward, coverage, fresh in SOURCE_CATALOGUE:
        out.append({"code": code, "name": name, "vendor": vendor, "category": cat,
                    "used_in_car": used, "steward": steward, "coverage": coverage,
                    "freshness_hours": fresh})
    return out


def car_element_count(source_code: str) -> int:
    return sum(1 for e in reg.INPUT_ELEMENTS if _primary(e.element_code) == source_code)
