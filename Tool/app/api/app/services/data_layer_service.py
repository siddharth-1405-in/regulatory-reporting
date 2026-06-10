"""Data Layer — shared governed canonical data workspace (element-level MVC).

The canonical element catalogue and ownership are global; governed VALUES are
scoped to a reporting period (instance). Maker-checker runs at the element level
and ROLLS UP into the existing Finance/Risk domain certification, which remains
the calculation gate (see certification_service). Agents and the engine are
untouched.

Element status lifecycle:
    draft → edited → frozen → submitted → certified
                                submitted → rejected → (edited)
    certified → invalidated   (when an approved value later changes)
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

EDITABLE_STATES = {"draft", "edited", "rejected", "invalidated"}
LOCKED_STATES = {"frozen", "submitted", "certified"}


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
        override = float(g.override_value) if g and g.override_value is not None else None
        src = sources_reg.source_for(e.element_code)
        out.append({
            "element_code": e.element_code, "label": e.label, "sheet_name": e.sheet_name,
            "section": e.section_name, "domain": e.source_domain,
            "business_meaning": rules_reg.business_meaning(e.element_code),
            "source_system": src["source_name"], "source_code": src["source_code"],
            "source_field": src["source_field"], "source_type": e.source_type,
            "raw_value": float(raw.get(e.element_code, Decimal("0"))),
            "override_value": override,
            "value": float(effective.get(e.element_code, Decimal("0"))),
            "status": status, "editable": status in EDITABLE_STATES, "has_override": override is not None,
            "last_updated_by": g.last_updated_by if g else "system",
            "last_approved_by": g.approved_by if g else None,
            "dependent_packs": ["CAR-SA-01"],
            "dependent_schedules": deps.get(e.element_code, [e.sheet_name]),
        })
    return out


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


# ---- maker actions ----------------------------------------------------------
def edit_value(db: Session, *, instance_id: int, element_code: str, value: float,
               role: str, actor: str, reason: str = "Manual override") -> ElementGovernance:
    """Governed manual override. The raw system value (ElementValue) is preserved;
    the override is what the engine uses. Always re-enters maker-checker and
    invalidates the owning domain certification."""
    _require(role, {"Maker", "Admin"}, "edit data values")
    r = _row(db, instance_id, element_code)
    if r.status in LOCKED_STATES:
        raise RolePermissionError(f"Element is {r.status}; reopen before editing.")
    r.override_value = Decimal(str(value))
    r.override_reason = reason
    r.status = "edited"
    r.last_updated_by = actor
    r.last_updated_at = _now()
    db.flush()
    # value changed -> invalidate the owning domain certification (gate closes)
    certification_service.invalidate_for_elements(db, instance_id, [element_code], actor=actor)
    audit_service.log(db, actor=actor, action="override_value", entity_type="element_governance",
                      entity_id=element_code, instance_id=instance_id,
                      after={"override": float(value), "reason": reason})
    return r


def clear_override(db: Session, *, instance_id: int, element_code: str, role: str, actor: str):
    _require(role, {"Maker", "Admin"}, "clear overrides")
    r = _row(db, instance_id, element_code)
    if r.status in LOCKED_STATES:
        raise RolePermissionError(f"Element is {r.status}; reopen first.")
    r.override_value = None
    r.override_reason = ""
    r.status = "edited"
    db.flush()
    certification_service.invalidate_for_elements(db, instance_id, [element_code], actor=actor)
    return r


def drilldown(db: Session, instance_id: int, code: str) -> dict:
    """Raw → transformation → processed lineage for one governed element."""
    e = reg.REGISTRY.get(code)
    raw = report_instance_service.load_raw_inputs(db, instance_id).get(code)
    g = (db.query(ElementGovernance).filter(ElementGovernance.instance_id == instance_id,
                                            ElementGovernance.element_code == code).one_or_none())
    override = float(g.override_value) if g and g.override_value is not None else None
    effective = override if override is not None else (float(raw) if raw is not None else 0.0)
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
    if override is not None:
        steps.append({"step": "Manual override", "detail": g.override_reason or "Governed override",
                      "value": override})
    steps.append({"step": rule.get("rule_name", "Rule"), "detail": rule.get("plain_english", ""),
                  "value": contribution})

    return {
        "element_code": code, "label": e.label if e else code,
        "business_meaning": rules_reg.business_meaning(code),
        "source": src, "raw_value": float(raw) if raw is not None else None,
        "override_value": override, "effective_value": effective,
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


def freeze(db, instance_id, codes, role, actor):
    return _bulk_set(db, instance_id, codes, role, actor, {"Maker", "Admin"},
                     {"draft", "edited"}, "frozen", "freeze values")


def reopen(db: Session, instance_id: int, codes: list[str], role: str, actor: str) -> list[str]:
    """Pull values back to 'edited' for amendment. Reopening a certified or
    submitted value invalidates the owning domain certification (a controlled
    recall of approved data — the spec's invalidation requirement)."""
    _require(role, {"Maker", "Admin"}, "reopen values")
    changed, recall_domains = [], set()
    for code in codes:
        r = _row(db, instance_id, code)
        if r.status in ("frozen", "submitted", "certified", "rejected", "invalidated"):
            if r.status in ("submitted", "certified"):
                d = ownership_service.domain_for_element(code)
                if d:
                    recall_domains.add(d)
            r.status = "edited"
            r.last_updated_by = actor
            r.last_updated_at = _now()
            changed.append(code)
    for domain in recall_domains:
        certification_service.set_status(db, instance_id, domain, "Invalidated",
                                         actor=actor, reason="Certified data reopened for amendment")
    db.flush()
    audit_service.log(db, actor=actor, action="reopen_values", entity_type="element_governance",
                      instance_id=instance_id, after={"elements": changed, "recalled_domains": list(recall_domains)})
    return changed


def submit(db, instance_id, codes, role, actor):
    return _bulk_set(db, instance_id, codes, role, actor, {"Maker", "Admin"},
                     {"frozen"}, "submitted", "submit values for sign-off")


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
