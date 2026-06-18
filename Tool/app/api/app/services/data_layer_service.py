"""Data Layer — shared governed canonical data workspace (element-level MVC).

The canonical element catalogue and ownership are global; governed VALUES are
scoped to a reporting period (instance). Maker-checker runs at the element level
and ROLLS UP into the existing Finance/Risk domain certification, which remains
the calculation gate (see certification_service). Agents and the engine are
untouched.

Element status lifecycle (attestation only — values are never overwritten here):
    draft (ready for submission) → submitted → certified
                                   submitted → rejected
    certified | submitted → invalidated   (when upstream data later changes)
    rejected | invalidated → submitted    (re-submit after an upstream fix)

Corrections flow through re-ingestion (ingestion_service) or rule-parameter edits
(rules_service), never through manual value overrides.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from functools import lru_cache

from sqlalchemy.orm import Session

from ..models import CalcRun, ElementGovernance
from ..registry.car_sa01 import elements as reg
from ..registry.car_sa01 import rules as rules_reg
from ..registry.car_sa01 import sources as sources_reg
from . import (
    audit_service, certification_service, ingestion_service, lineage_service,
    ownership_service, report_instance_service,
)

# states a Maker may submit from (everything not locked under review/certified)
SUBMITTABLE_STATES = {"draft", "rejected", "invalidated"}
LOCKED_STATES = {"submitted", "certified"}


class RolePermissionError(PermissionError):
    pass


def _now():
    return datetime.now(timezone.utc)


def _require(role: str, allowed: set[str], action: str):
    if role not in allowed:
        raise RolePermissionError(f"Role '{role}' may not {action}.")


# ---- ownership metadata from the matrix (domain -> steward / source) --------
@lru_cache(maxsize=1)
def _domain_meta() -> dict[str, dict]:
    meta: dict[str, dict] = {}
    for row in ownership_service.parse_matrix():
        meta.setdefault(row["domain"], {"steward": row["steward"],
                                        "source_system": row["source_system"]})
    # sensible fallbacks
    meta.setdefault("Finance", {"steward": "CFO Office", "source_system": "Core Banking / GL"})
    meta.setdefault("Risk", {"steward": "CRO Office", "source_system": "Risk Engine"})
    return meta


@lru_cache(maxsize=1)
def _dependent_schedules() -> dict[str, list[str]]:
    """element_code -> sorted schedules it feeds (own sheet + downstream)."""
    edges = lineage_service.build_edges()
    adj: dict[str, list[str]] = {}
    for frm, to in edges:
        adj.setdefault(frm, []).append(to)
    out: dict[str, list[str]] = {}
    for e in reg.INPUT_ELEMENTS:
        sheets = {e.sheet_name}
        seen, frontier = set(), [e.element_code]
        for _ in range(5):
            nxt = []
            for c in frontier:
                for d in adj.get(c, []):
                    if d not in seen:
                        seen.add(d)
                        nxt.append(d)
                        tgt = reg.REGISTRY.get(d)
                        if tgt:
                            sheets.add(tgt.sheet_name)
            frontier = nxt
        out[e.element_code] = sorted(sheets)
    return out


# ---- governance rows --------------------------------------------------------
def _row(db: Session, instance_id: int, code: str) -> ElementGovernance:
    r = (db.query(ElementGovernance)
         .filter(ElementGovernance.instance_id == instance_id,
                 ElementGovernance.element_code == code).one_or_none())
    if r is None:
        r = ElementGovernance(instance_id=instance_id, element_code=code, status="draft")
        db.add(r)
        db.flush()
    return r


def ensure_governance(db: Session, instance_id: int) -> None:
    """Back-fill governance rows for every input element. Status mirrors the
    current domain certification so the Data Layer and the gate start aligned."""
    existing = {g.element_code for g in
                db.query(ElementGovernance).filter(ElementGovernance.instance_id == instance_id).all()}
    cert = certification_service.status_map(db, instance_id)
    for e in reg.INPUT_ELEMENTS:
        if e.element_code in existing:
            continue
        certified = cert.get(e.source_domain or "", "") == "Certified"
        db.add(ElementGovernance(instance_id=instance_id, element_code=e.element_code,
                                 status="certified" if certified else "draft",
                                 approved_by="system" if certified else None,
                                 approved_at=_now() if certified else None))
    db.flush()


# ---- read -------------------------------------------------------------------
def catalogue(db: Session, instance_id: int) -> list[dict]:
    ensure_governance(db, instance_id)
    effective = report_instance_service.load_inputs(db, instance_id)
    raw = report_instance_service.load_raw_inputs(db, instance_id)
    gov = {g.element_code: g for g in
           db.query(ElementGovernance).filter(ElementGovernance.instance_id == instance_id).all()}
    deps = _dependent_schedules()
    out = []
    for e in reg.INPUT_ELEMENTS:
        g = gov.get(e.element_code)
        status = g.status if g else "draft"
        src = sources_reg.source_for(e.element_code)
        out.append({
            "element_code": e.element_code, "label": e.label, "sheet_name": e.sheet_name,
            "section": e.section_name, "domain": e.source_domain,
            "business_meaning": rules_reg.business_meaning(e.element_code),
            "source_system": src["source_name"], "source_code": src["source_code"],
            "source_field": src["source_field"], "source_type": e.source_type,
            "raw_value": float(raw.get(e.element_code, Decimal("0"))),
            "value": float(effective.get(e.element_code, Decimal("0"))),
            "status": status, "can_submit": status in SUBMITTABLE_STATES,
            "last_updated_by": g.last_updated_by if g else "system",
            "last_approved_by": g.approved_by if g else None,
            "dependent_packs": ["CAR-SA-01"],
            "dependent_schedules": deps.get(e.element_code, [e.sheet_name]),
            "derived": False,
        })
    out.extend(_s5_derived_rows(db, instance_id))
    return out


# Schedule 5 has no maker-input data elements — it is fully derived from S1–S4
# outputs and the regulatory buffer parameters. We surface its key computed
# outputs as read-only ("derived") rows so the schedule is visible in the grid;
# they are never submitted/signed off here (buffer rates are edited in the Rule
# Engine, source data in S1–S4).
_S5_DERIVED = [
    ("S5_BUFFER_CCB", "Capital Conservation Buffer (CCB)", "rate",
     "Fixed conservation buffer, % of total RWA."),
    ("S5_BUFFER_CCYB", "Countercyclical Capital Buffer (CCyB)", "rate",
     "Countercyclical buffer in force, % of total RWA."),
    ("S5_BUFFER_DSIB", "D-SIB Surcharge", "rate",
     "Systemic-importance surcharge, % of total RWA."),
    ("S5_COMBINED_BUFFER", "Combined Buffer Requirement", "rate",
     "Sum of all applicable buffers, met with CET1 above the 4.50% minimum."),
    ("S5_CET1_SURPLUS", "CET1 surplus / (deficit) over combined requirement", "ratio",
     "CET1 headroom over the combined buffer — the binding distribution test."),
]


def _s5_derived_rows(db: Session, instance_id: int) -> list[dict]:
    run = (db.query(CalcRun).filter(CalcRun.instance_id == instance_id)
           .order_by(CalcRun.id.desc()).first())
    values = run.results.get("values", {}) if run else {}
    rows = []
    for code, label, kind, meaning in _S5_DERIVED:
        raw = values.get(code)
        try:
            val = float(raw)
        except (TypeError, ValueError):
            val = None
        display = ("—" if val is None
                   else f"{val*100:.2f}%" if kind in ("rate", "ratio")
                   else f"{val:,.0f}")
        rows.append({
            "element_code": code, "label": label, "sheet_name": "Schedule 5",
            "section": "Capital Buffers", "domain": "Finance/Risk",
            "business_meaning": meaning,
            "source_system": "Derived (calc engine)", "source_code": "DERIVED",
            "source_field": "—", "source_type": "derived",
            "raw_value": val or 0.0, "value": val or 0.0, "display": display,
            "status": "derived", "can_submit": False,
            "last_updated_by": "system", "last_approved_by": None,
            "dependent_packs": ["CAR-SA-01"], "dependent_schedules": ["Schedule 5", "Summary"],
            "derived": True,
        })
    return rows


def signoff_queue(db: Session, instance_id: int) -> list[dict]:
    ensure_governance(db, instance_id)
    rows = (db.query(ElementGovernance)
            .filter(ElementGovernance.instance_id == instance_id,
                    ElementGovernance.status == "submitted").all())
    meta = _domain_meta()
    out = []
    for r in rows:
        e = reg.REGISTRY.get(r.element_code)
        domain = e.source_domain if e else None
        out.append({"element_code": r.element_code, "label": e.label if e else r.element_code,
                    "domain": domain, "steward": meta.get(domain or "", {}).get("steward", ""),
                    "submitted_by": r.submitted_by})
    return out


def status_summary(db: Session, instance_id: int) -> dict[str, int]:
    ensure_governance(db, instance_id)
    rows = db.query(ElementGovernance).filter(ElementGovernance.instance_id == instance_id).all()
    summary: dict[str, int] = {}
    for r in rows:
        summary[r.status] = summary.get(r.status, 0) + 1
    return summary


# ---- read: lineage ----------------------------------------------------------
def drilldown(db: Session, instance_id: int, code: str) -> dict:
    """Source → transformation → processed lineage for one report-ready element."""
    e = reg.REGISTRY.get(code)
    raw = report_instance_service.load_raw_inputs(db, instance_id).get(code)
    g = (db.query(ElementGovernance).filter(ElementGovernance.instance_id == instance_id,
                                            ElementGovernance.element_code == code).one_or_none())
    effective = float(raw) if raw is not None else 0.0
    src = sources_reg.source_for(code)
    rule = rules_reg.rule_for(code)

    # processed contribution from the latest calc run (RWA / charge / net amount)
    run = (db.query(CalcRun).filter(CalcRun.instance_id == instance_id)
           .order_by(CalcRun.id.desc()).first())
    contribution = None
    if run:
        for sched in run.results.get("schedules", {}).values():
            for line in sched["lines"]:
                if line["element_code"] == code:
                    contribution = line["result"]
                    break
        if contribution is None:
            contribution = run.results.get("values", {}).get(code)

    steps = [{"step": "Source extract", "detail": f"{src['source_name']} · {src['source_field']}",
              "value": float(raw) if raw is not None else None}]
    steps.append({"step": rule.get("rule_name", "Rule"), "detail": rule.get("plain_english", ""),
                  "value": contribution})

    return {
        "element_code": code, "label": e.label if e else code,
        "business_meaning": rules_reg.business_meaning(code),
        "source": src, "raw_value": float(raw) if raw is not None else None,
        "effective_value": effective,
        "processed_value": contribution, "rule": rule,
        "steps": steps,
        "domain": e.source_domain if e else None, "status": g.status if g else "draft",
        "lineage_upstream": lineage_service.trace_upstream(db, instance_id, code),
    }


def _bulk_set(db: Session, instance_id: int, codes: list[str], role: str, actor: str,
              allowed_roles: set[str], from_states: set[str], to_state: str,
              action: str) -> list[str]:
    _require(role, allowed_roles, action)
    changed = []
    for code in codes:
        r = _row(db, instance_id, code)
        if r.status in from_states:
            r.status = to_state
            r.last_updated_by = actor
            r.last_updated_at = _now()
            if to_state == "submitted":
                r.submitted_by = actor
                r.submitted_at = _now()
            changed.append(code)
    db.flush()
    audit_service.log(db, actor=actor, action=action.replace(" ", "_"),
                      entity_type="element_governance", instance_id=instance_id,
                      after={"elements": changed, "to": to_state})
    return changed


def submit(db, instance_id, codes, role, actor):
    """Maker submits report-ready elements for Checker sign-off. Allowed from any
    non-locked state (ready/rejected/invalidated) — no separate freeze step."""
    return _bulk_set(db, instance_id, codes, role, actor, {"Maker", "Admin"},
                     SUBMITTABLE_STATES, "submitted", "submit values for sign-off")


# ---- checker actions --------------------------------------------------------
def approve(db: Session, instance_id: int, codes: list[str], role: str, actor: str) -> dict:
    _require(role, {"Checker", "Admin"}, "approve values")
    approved = []
    for code in codes:
        r = _row(db, instance_id, code)
        if r.status == "submitted":
            r.status = "certified"
            r.approved_by = actor
            r.approved_at = _now()
            approved.append(code)
    db.flush()
    # roll up: a domain is certified when all its input elements are certified
    domains_certified = []
    for domain in sorted(ownership_service.required_domains()):
        elems = ownership_service.elements_for_domain(domain)
        statuses = {g.element_code: g.status for g in
                    db.query(ElementGovernance)
                    .filter(ElementGovernance.instance_id == instance_id).all()}
        if elems and all(statuses.get(c) == "certified" for c in elems):
            certification_service.certify(db, instance_id, domain, actor=actor)
            domains_certified.append(domain)
    audit_service.log(db, actor=actor, action="approve_values", entity_type="element_governance",
                      instance_id=instance_id, after={"elements": approved, "domains": domains_certified})
    return {"approved": approved, "domains_certified": domains_certified}


def reject(db: Session, instance_id: int, codes: list[str], role: str, actor: str,
           reason: str = "") -> list[str]:
    _require(role, {"Checker", "Admin"}, "reject values")
    rejected = []
    for code in codes:
        r = _row(db, instance_id, code)
        if r.status == "submitted":
            r.status = "rejected"
            r.reject_reason = reason
            r.approved_by = actor
            r.approved_at = _now()
            rejected.append(code)
    db.flush()
    audit_service.log(db, actor=actor, action="reject_values", entity_type="element_governance",
                      instance_id=instance_id, after={"elements": rejected, "reason": reason})
    return rejected
