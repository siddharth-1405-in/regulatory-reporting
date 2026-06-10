"""Canonical CAR-SA-01 element registry.

Every line item in the SAMA CAR workbook is described here exactly once, keyed
by a stable `element_code`. Input lines carry the deterministic regulatory rate
(risk weight / CCF / charge rate / beta) taken from the workbook, co-located so
there is a single source of truth. Derived lines (subtotals, totals, ratios) are
also registered so lineage, validation and export can reference them by code.

The registry is the calculation source of record. The workbook is used only for
structure, labels, styling and as an export target — its cross-sheet formulas are
known to be internally inconsistent and are NOT trusted (see docs/TDD.md).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .parameters import D

# ---- vocabularies -----------------------------------------------------------
FINANCE = "Finance"
RISK = "Risk"

SRC_INPUT = "input"
SRC_FORMULA = "formula"
SRC_CROSS = "cross_sheet"
SRC_ASSUMPTION = "assumption"

# lineage levels, lowest (raw) to highest (headline)
L_INPUT = "input"
L_SUBTOTAL = "schedule_subtotal"
L_TOTAL = "schedule_total"
L_SUMMARY = "summary"
L_RATIO = "ratio_buffer"


@dataclass(frozen=True)
class Element:
    element_code: str
    label: str
    sheet_name: str
    section_name: str
    source_domain: str | None      # Finance / Risk / None (pure derived)
    source_type: str               # input / formula / cross_sheet / assumption
    lineage_level: str
    export_cell: str | None = None       # e.g. "C7" on its sheet
    kind: str | None = None              # engine routing tag (see below)
    rate: Decimal | None = None          # risk weight / charge rate / beta
    ccf: Decimal | None = None           # credit conversion factor (off-balance)
    parameter_dependencies: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_input(self) -> bool:
        return self.source_type == SRC_INPUT


# =============================================================================
# SCHEDULE 1 — Regulatory Capital Composition  (domain: Finance)
# =============================================================================
_S1 = "Schedule 1"
_S1_CET1_GROSS = [
    ("S1_CET1_PAIDUP", "Paid-up ordinary share capital / common shares", "C7"),
    ("S1_CET1_SHARE_PREMIUM", "Share premium (relating to CET1)", "C8"),
    ("S1_CET1_RETAINED", "Retained earnings (prior year)", "C9"),
    ("S1_CET1_CY_PROFIT", "Current year profit attributable to shareholders (net of dividends)", "C10"),
    ("S1_CET1_AOCI", "Accumulated Other Comprehensive Income (AOCI)", "C11"),
    ("S1_CET1_OTHER_RESERVES", "Other disclosed reserves", "C12"),
    ("S1_CET1_MINORITY", "Minority interest — eligible amount", "C13"),
]
_S1_CET1_DEDUCT = [
    ("S1_CET1D_GOODWILL", "Goodwill (net of associated DTL)", "C16"),
    ("S1_CET1D_INTANGIBLES", "Other intangible assets (net of DTL)", "C17"),
    ("S1_CET1D_DTA_PROFIT", "DTA relying on future profitability (excl. temporary differences)", "C18"),
    ("S1_CET1D_CFHEDGE", "Cash flow hedge reserve", "C19"),
    ("S1_CET1D_PROV_SHORTFALL", "Shortfall of provisions to expected losses (IRB only)", "C20"),
    ("S1_CET1D_SECURITISATION", "Securitisation gain on sale", "C21"),
    ("S1_CET1D_OWN_CREDIT", "Gains/losses from own credit risk on fair-valued liabilities", "C22"),
    ("S1_CET1D_PENSION", "Defined benefit pension fund net assets", "C23"),
    ("S1_CET1D_OWN_CET1", "Investments in own CET1 instruments (treasury shares)", "C24"),
    ("S1_CET1D_RECIPROCAL", "Reciprocal cross-holdings in CET1 of other FIs", "C25"),
    ("S1_CET1D_SIGNIFICANT", "Significant investments in CET1 of unconsolidated FIs (>10%)", "C26"),
    ("S1_CET1D_NONSIG", "Non-significant investments in CET1 — above 10% threshold", "C27"),
    ("S1_CET1D_MSR", "Mortgage servicing rights — above 10% threshold", "C28"),
    ("S1_CET1D_DTA_TEMP", "DTA from temporary differences — above 10% threshold", "C29"),
    ("S1_CET1D_ABOVE15", "Amounts above 15% combined threshold", "C30"),
    ("S1_CET1D_OTHER", "Other deductions as prescribed by SAMA", "C31"),
]
_S1_AT1_GROSS = [
    ("S1_AT1_INSTRUMENTS", "Qualifying AT1 instruments (Perpetual Sukuk / bonds)", "C36"),
    ("S1_AT1_SHARE_PREMIUM", "Share premium relating to AT1 instruments", "C37"),
]
_S1_AT1_DEDUCT = [
    ("S1_AT1D_OWN", "Less: Investments in own AT1 instruments", "C38"),
    ("S1_AT1D_RECIPROCAL", "Less: Reciprocal cross-holdings in AT1 of other FIs", "C39"),
    ("S1_AT1D_SIGNIFICANT", "Less: Significant investments in AT1 of unconsolidated FIs", "C40"),
    ("S1_AT1D_OTHER", "Other AT1 deductions as prescribed by SAMA", "C41"),
]
_S1_T2_GROSS = [
    ("S1_T2_INSTRUMENTS", "Qualifying Tier 2 instruments (Subordinated Sukuk / bonds, ≥5y)", "C46"),
    ("S1_T2_SHARE_PREMIUM", "Share premium relating to Tier 2 instruments", "C47"),
    ("S1_T2_GEN_PROVISIONS", "General provisions / general loan-loss reserves (SA, max 1.25% credit RWA)", "C48"),
    ("S1_T2_EXCESS_PROV", "Excess of provisions over expected losses (IRB)", "C49"),
]
_S1_T2_DEDUCT = [
    ("S1_T2D_OWN", "Less: Investments in own Tier 2 instruments", "C50"),
    ("S1_T2D_RECIPROCAL", "Less: Reciprocal cross-holdings in Tier 2 of other FIs", "C51"),
    ("S1_T2D_SIGNIFICANT", "Less: Significant investments in Tier 2 of unconsolidated FIs", "C52"),
    ("S1_T2D_OTHER", "Other Tier 2 deductions as prescribed by SAMA", "C53"),
]


def _s1_elements() -> list[Element]:
    out: list[Element] = []
    for code, label, cell in _S1_CET1_GROSS:
        out.append(Element(code, label, _S1, "CET1 — gross", FINANCE, SRC_INPUT, L_INPUT, cell, kind="cet1_gross"))
    for code, label, cell in _S1_CET1_DEDUCT:
        out.append(Element(code, label, _S1, "CET1 — deductions", FINANCE, SRC_INPUT, L_INPUT, cell, kind="cet1_deduction"))
    for code, label, cell in _S1_AT1_GROSS:
        out.append(Element(code, label, _S1, "AT1 — gross", FINANCE, SRC_INPUT, L_INPUT, cell, kind="at1_gross"))
    for code, label, cell in _S1_AT1_DEDUCT:
        out.append(Element(code, label, _S1, "AT1 — deductions", FINANCE, SRC_INPUT, L_INPUT, cell, kind="at1_deduction"))
    for code, label, cell in _S1_T2_GROSS:
        out.append(Element(code, label, _S1, "Tier 2 — gross", FINANCE, SRC_INPUT, L_INPUT, cell, kind="t2_gross"))
    for code, label, cell in _S1_T2_DEDUCT:
        out.append(Element(code, label, _S1, "Tier 2 — deductions", FINANCE, SRC_INPUT, L_INPUT, cell, kind="t2_deduction"))
    return out


# =============================================================================
# SCHEDULE 2 — Credit Risk RWA (Standardised)  (domain: Risk)
# =============================================================================
_S2 = "Schedule 2"
# (code, label, row, risk_weight)
_S2_ONBAL = [
    ("S2_ON_SAUDI_GOV", "Claims on Saudi Government and SAMA", 7, "0"),
    ("S2_ON_SAUDI_GOV_FX", "Claims on Saudi Government — foreign currency", 8, "0"),
    ("S2_ON_GCC_AAA", "Claims on GCC Governments (AAA to AA-)", 9, "0"),
    ("S2_ON_GCC_A", "Claims on GCC Governments (A+ to A-)", 10, "0.2"),
    ("S2_ON_GCC_BBB", "Claims on GCC Governments (BBB+ to B-)", 11, "0.5"),
    ("S2_ON_GCC_UNRATED", "Claims on GCC Governments (unrated)", 12, "1"),
    ("S2_ON_SOV_AAA", "Claims on other Sovereigns (AAA to AA-)", 13, "0"),
    ("S2_ON_SOV_A", "Claims on other Sovereigns (A+ to A-)", 14, "0.2"),
    ("S2_ON_SOV_BBB", "Claims on other Sovereigns (BBB+ to BB-)", 15, "0.5"),
    ("S2_ON_SOV_LOW", "Claims on other Sovereigns (below BB- / unrated)", 16, "1"),
    ("S2_ON_PSE_DOM", "Claims on Public Sector Entities — domestic", 17, "0.2"),
    ("S2_ON_PSE_FOR", "Claims on Public Sector Entities — foreign", 18, "0.5"),
    ("S2_ON_MDB", "Claims on Multilateral Development Banks", 19, "0.2"),
    ("S2_ON_BANK_ST", "Claims on Banks — short-term (< 3 months)", 20, "0.2"),
    ("S2_ON_BANK_AAA", "Claims on Banks — long-term (AAA to AA-)", 21, "0.2"),
    ("S2_ON_BANK_A", "Claims on Banks — long-term (A+ to A-)", 22, "0.5"),
    ("S2_ON_BANK_BBB", "Claims on Banks — long-term (BBB+ to BB-)", 23, "1"),
    ("S2_ON_BANK_LOW", "Claims on Banks — long-term (below BB- / unrated)", 24, "1.5"),
    ("S2_ON_SECFIRM", "Claims on Securities Firms (bank-equivalent)", 25, "0.5"),
    ("S2_ON_CORP_AAA", "Claims on Corporates (AAA to AA-)", 26, "0.2"),
    ("S2_ON_CORP_A", "Claims on Corporates (A+ to A-)", 27, "0.5"),
    ("S2_ON_CORP_BBB", "Claims on Corporates (BBB+ to BB-)", 28, "1"),
    ("S2_ON_CORP_LOW", "Claims on Corporates (below BB- / unrated)", 29, "1"),
    ("S2_ON_SME_CORP", "Claims on SMEs — Corporate treatment", 30, "1"),
    ("S2_ON_RETAIL", "Regulatory Retail Portfolio", 31, "0.75"),
    ("S2_ON_RETAIL_SME", "Retail SMEs (qualifying)", 32, "0.75"),
    ("S2_ON_RRE_LOW", "Residential Real Estate (≤80% LTV)", 33, "0.35"),
    ("S2_ON_RRE_HIGH", "Residential Real Estate (>80% LTV)", 34, "0.75"),
    ("S2_ON_CRE", "Commercial Real Estate", 35, "1"),
    ("S2_ON_PASTDUE_LOW", "Past Due Loans — net of provisions (<20% covered)", 36, "1.5"),
    ("S2_ON_PASTDUE_HIGH", "Past Due Loans — net of provisions (≥20% covered)", 37, "1"),
    ("S2_ON_HIGHRISK", "Higher Risk Categories (VC, speculative RE, etc.)", 38, "1.5"),
    ("S2_ON_CASH", "Cash items and equivalents", 39, "0"),
    ("S2_ON_GOLD", "Gold bullion held in own vaults", 40, "0"),
    ("S2_ON_FIXEDASSETS", "Fixed assets (property and equipment)", 41, "1"),
    ("S2_ON_OTHER", "Other assets", 42, "1"),
]
# (code, label, row, ccf, risk_weight)
_S2_OFFBAL = [
    ("S2_OFF_DIRECT_CREDIT", "Direct credit substitutes (financial guarantees)", 46, "1", "1"),
    ("S2_OFF_TRADE_LC", "Trade finance — documentary credits (LCs, short-term)", 47, "0.2", "1"),
    ("S2_OFF_TRADE_BONDS", "Trade finance — performance / bid bonds", 48, "0.5", "1"),
    ("S2_OFF_COMMIT_GT1Y", "Commitments with original maturity > 1 year", 49, "0.5", "1"),
    ("S2_OFF_COMMIT_LE1Y", "Commitments with original maturity ≤ 1 year (or revocable)", 50, "0.2", "1"),
    ("S2_OFF_REPO", "Repurchase / reverse repo agreements", 51, "1", "1"),
    ("S2_OFF_SECLENDING", "Securities lending / borrowing", 52, "1", "1"),
    ("S2_OFF_DERIVATIVES", "Derivatives — Current Exposure Method (add-on)", 53, "0.5", "1"),
    ("S2_OFF_OTHER", "Other off-balance sheet items", 54, "1", "1"),
]


def _s2_elements() -> list[Element]:
    out: list[Element] = []
    for code, label, row, rw in _S2_ONBAL:
        out.append(Element(code, label, _S2, "On-Balance Sheet", RISK, SRC_INPUT, L_INPUT,
                           f"C{row}", kind="credit_onbal", rate=D(rw),
                           parameter_dependencies=(f"{code}.risk_weight",)))
    for code, label, row, ccf, rw in _S2_OFFBAL:
        out.append(Element(code, label, _S2, "Off-Balance Sheet", RISK, SRC_INPUT, L_INPUT,
                           f"C{row}", kind="credit_offbal", rate=D(rw), ccf=D(ccf),
                           parameter_dependencies=(f"{code}.ccf", f"{code}.risk_weight")))
    return out


# =============================================================================
# SCHEDULE 3 — Market Risk Capital Charge (Standardised)  (domain: Risk)
# =============================================================================
_S3 = "Schedule 3"
# rate-based lines: (code, label, row, charge_rate)
_S3_RATE = [
    ("S3_IR_SPECIFIC_GOV", "Specific Risk — Government & qualifying bonds", 7, "0"),
    ("S3_IR_SPECIFIC_IG", "Specific Risk — Other bonds (investment grade)", 8, "0.0025"),
    ("S3_IR_SPECIFIC_NONIG", "Specific Risk — Other bonds (below investment grade)", 9, "0.08"),
    ("S3_EQ_SPECIFIC", "Equity — Specific Risk (individual positions)", 14, "0.08"),
    ("S3_EQ_GENERAL", "Equity — General Market Risk (net portfolio)", 15, "0.08"),
    ("S3_FX_NETOPEN", "Net open foreign exchange position (all currencies)", 17, "0.08"),
    ("S3_FX_GOLD", "Gold net open position", 18, "0.08"),
    ("S3_COMMODITIES", "Commodities — Simplified approach", 20, "0.15"),
]
# direct-charge lines: capital charge entered directly  (code, label, row)
_S3_DIRECT = [
    ("S3_IR_GENERAL_DURATION", "General Market Risk — Duration method", 10),
    ("S3_IR_BASIS", "Basis Risk add-on", 11),
    ("S3_IR_YIELDCURVE", "Yield Curve Risk add-on", 12),
    ("S3_OPTIONS", "Options — Simplified / Delta-plus add-on", 22),
]


def _s3_elements() -> list[Element]:
    out: list[Element] = []
    for code, label, row, rate in _S3_RATE:
        out.append(Element(code, label, _S3, "Market Risk", RISK, SRC_INPUT, L_INPUT,
                           f"C{row}", kind="market_rate", rate=D(rate),
                           parameter_dependencies=(f"{code}.charge_rate",)))
    for code, label, row in _S3_DIRECT:
        out.append(Element(code, label, _S3, "Market Risk", RISK, SRC_INPUT, L_INPUT,
                           f"C{row}", kind="market_direct"))
    return out


# =============================================================================
# SCHEDULE 4 — Operational Risk Capital Charge (TSA)  (domain: Finance)
# =============================================================================
_S4 = "Schedule 4"
# (base_code, label, row, beta)
_S4_LINES = [
    ("S4_CORP_FINANCE", "Corporate Finance", 6, "0.18"),
    ("S4_TRADING_SALES", "Trading & Sales", 7, "0.18"),
    ("S4_RETAIL_BANKING", "Retail Banking", 8, "0.12"),
    ("S4_COMMERCIAL_BANKING", "Commercial Banking", 9, "0.15"),
    ("S4_PAYMENT_SETTLEMENT", "Payment & Settlement", 10, "0.18"),
    ("S4_AGENCY_SERVICES", "Agency Services", 11, "0.15"),
    ("S4_ASSET_MGMT", "Asset Management", 12, "0.12"),
    ("S4_RETAIL_BROKERAGE", "Retail Brokerage", 13, "0.12"),
]


def _s4_elements() -> list[Element]:
    out: list[Element] = []
    for base, label, row, beta in _S4_LINES:
        for yr, col in ((1, "C"), (2, "D"), (3, "E")):
            out.append(Element(f"{base}_GI_Y{yr}", f"{label} — Gross Income Year {yr}", _S4,
                               "Operational Risk", FINANCE, SRC_INPUT, L_INPUT, f"{col}{row}",
                               kind="oprisk_gi", rate=D(beta),
                               parameter_dependencies=(f"{base}.beta",)))
    return out


# Mapping consumed by the calc engine: business line -> (y1,y2,y3 codes, beta).
S4_BUSINESS_LINES = [
    (base, label, (f"{base}_GI_Y1", f"{base}_GI_Y2", f"{base}_GI_Y3"), D(beta), row)
    for base, label, row, beta in _S4_LINES
]


# =============================================================================
# SCHEDULE 6 — Reconciliation to Published Financial Statements  (Finance)
# =============================================================================
_S6 = "Schedule 6"
# (base_code, label, row)  -> published-FS (C) and adjustment (D) inputs
_S6_LINES = [
    ("S6_PAIDUP", "Paid-up share capital", 7),
    ("S6_SHARE_PREMIUM", "Share premium", 8),
    ("S6_RETAINED", "Retained earnings", 9),
    ("S6_OCI", "Other comprehensive income / reserves", 10),
    ("S6_MINORITY", "Minority interests", 11),
    ("S6_GOODWILL", "Less: Goodwill and intangibles (net of DTL)", 13),
    ("S6_DTA", "Less: Deferred tax assets", 14),
    ("S6_CFHEDGE", "Less: Cash flow hedge reserve", 15),
    ("S6_OWNSHARES", "Less: Own shares (treasury stock)", 16),
    ("S6_OTHER_DEDUCT", "Less: Other regulatory deductions", 17),
    ("S6_T2_INSTRUMENTS", "Plus: Eligible Tier 2 instruments", 18),
    ("S6_GEN_PROVISIONS", "Plus: General provisions (eligible amount)", 19),
]


def _s6_elements() -> list[Element]:
    out: list[Element] = []
    for base, label, row in _S6_LINES:
        out.append(Element(f"{base}_FS", f"{label} (published FS)", _S6, "Reconciliation",
                           FINANCE, SRC_INPUT, L_INPUT, f"C{row}", kind="recon_fs"))
        out.append(Element(f"{base}_ADJ", f"{label} (regulatory adjustment)", _S6, "Reconciliation",
                           FINANCE, SRC_INPUT, L_INPUT, f"D{row}", kind="recon_adj"))
    return out


# =============================================================================
# DERIVED elements (subtotals, totals, ratios, buffers) — engine outputs.
# =============================================================================
def _derived() -> list[Element]:
    def e(code, label, sheet, section, level, cell=None, stype=SRC_FORMULA):
        return Element(code, label, sheet, section, None, stype, level, cell)
    return [
        # Schedule 1
        e("S1_CET1_SUBTOTAL", "Sub-total: CET1 before regulatory adjustments", _S1, "CET1", L_SUBTOTAL, "C14"),
        e("S1_CET1_DEDUCT_TOTAL", "Total Regulatory Deductions from CET1", _S1, "CET1", L_SUBTOTAL, "C32"),
        e("S1_CET1_NET", "TOTAL CET1 CAPITAL (NET)", _S1, "CET1", L_TOTAL, "E33"),
        e("S1_AT1_TOTAL", "TOTAL AT1 CAPITAL", _S1, "AT1", L_TOTAL, "E42"),
        e("S1_TIER1_TOTAL", "TOTAL TIER 1 CAPITAL (CET1 + AT1)", _S1, "Tier 1", L_TOTAL, "E43"),
        e("S1_T2_TOTAL", "TOTAL TIER 2 CAPITAL", _S1, "Tier 2", L_TOTAL, "E54"),
        e("S1_TOTAL_CAPITAL", "TOTAL REGULATORY CAPITAL (TIER 1 + TIER 2)", _S1, "Total", L_TOTAL, "E55"),
        # Schedule 2
        e("S2_ONBAL_RWA", "Sub-Total: On-Balance Sheet RWA", _S2, "Credit Risk", L_SUBTOTAL, "G43"),
        e("S2_OFFBAL_RWA", "Sub-Total: Off-Balance Sheet RWA", _S2, "Credit Risk", L_SUBTOTAL, "G55"),
        e("S2_CREDIT_RWA", "TOTAL CREDIT RISK RWA", _S2, "Credit Risk", L_TOTAL, "G57"),
        # Schedule 3
        e("S3_MARKET_CHARGE", "TOTAL MARKET RISK CAPITAL CHARGE", _S3, "Market Risk", L_SUBTOTAL, "E23"),
        e("S3_MARKET_RWA", "MARKET RISK RWA (charge × 12.5)", _S3, "Market Risk", L_TOTAL, "E24"),
        # Schedule 4
        e("S4_OPRISK_CHARGE", "TOTAL OPERATIONAL RISK CAPITAL CHARGE", _S4, "Operational Risk", L_SUBTOTAL, "G14"),
        e("S4_OPRISK_RWA", "OPERATIONAL RISK RWA (charge × 12.5)", _S4, "Operational Risk", L_TOTAL, "G15"),
        # Summary
        e("SUM_TOTAL_RWA", "Total Risk-Weighted Assets (RWA)", "Summary", "Capital Adequacy", L_SUMMARY, "D12", SRC_CROSS),
        e("SUM_CET1_RATIO", "CET1 ratio", "Summary", "Capital Adequacy", L_RATIO, "E7"),
        e("SUM_TIER1_RATIO", "Tier 1 ratio", "Summary", "Capital Adequacy", L_RATIO, "E9"),
        e("SUM_TOTAL_RATIO", "Total capital ratio", "Summary", "Capital Adequacy", L_RATIO, "E11"),
        # Schedule 5
        e("S5_COMBINED_BUFFER", "Total Combined Buffer Requirement", _S5 := "Schedule 5", "Buffers", L_RATIO),
        e("S5_CET1_SURPLUS", "CET1 surplus / (deficit) over combined requirement", _S5, "Buffers", L_RATIO),
        # Schedule 6
        e("S6_TOTAL_REG_CAPITAL", "TOTAL REGULATORY CAPITAL (per Schedule 1)", _S6, "Reconciliation", L_TOTAL, "E20"),
        e("S6_RECON_DIFF", "Difference (should be nil)", _S6, "Reconciliation", L_TOTAL, "E21"),
        e("S6_CREDIT_PCT", "Credit Risk RWA — % of total", _S6, "RWA Composition", L_RATIO, "D25"),
        e("S6_MARKET_PCT", "Market Risk RWA — % of total", _S6, "RWA Composition", L_RATIO, "D26"),
        e("S6_OPRISK_PCT", "Operational Risk RWA — % of total", _S6, "RWA Composition", L_RATIO, "D27"),
        e("S6_RWA_TOTAL", "TOTAL RWA (composition check)", _S6, "RWA Composition", L_TOTAL, "C28"),
    ]


# =============================================================================
# Assemble the registry
# =============================================================================
INPUT_ELEMENTS: list[Element] = (
    _s1_elements() + _s2_elements() + _s3_elements() + _s4_elements() + _s6_elements()
)
DERIVED_ELEMENTS: list[Element] = _derived()
ALL_ELEMENTS: list[Element] = INPUT_ELEMENTS + DERIVED_ELEMENTS

REGISTRY: dict[str, Element] = {e.element_code: e for e in ALL_ELEMENTS}


def get(code: str) -> Element:
    return REGISTRY[code]


def inputs_for_sheet(sheet: str) -> list[Element]:
    return [e for e in INPUT_ELEMENTS if e.sheet_name == sheet]


def inputs_by_domain(domain: str) -> list[Element]:
    return [e for e in INPUT_ELEMENTS if e.source_domain == domain]


def codes_by_kind(kind: str) -> list[str]:
    return [e.element_code for e in INPUT_ELEMENTS if e.kind == kind]


# sanity: no duplicate codes
assert len(REGISTRY) == len(ALL_ELEMENTS), "duplicate element_code in CAR-SA-01 registry"
