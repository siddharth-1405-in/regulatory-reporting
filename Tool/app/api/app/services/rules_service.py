"""Rule engine — plain-English transformation rules over canonical elements.

Reads effective rule parameters (registry defaults + config_service overrides),
renders the plain-English rule and machine structure, and tags provenance
(system / user-edited). Editing a rule persists a parameter override and triggers
auto-recompute.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from ..registry.car_sa01 import elements as reg
from ..registry.car_sa01 import rules as rules_reg
from . import audit_service, calc_service, config_service
from .data_layer_service import RolePermissionError, _require


def _effective_params(db: Session) -> dict[str, Decimal]:
    params, _ = config_service.get_params_and_buffers(db)
    return params


def list_rules(db: Session, instance_id: int) -> list[dict]:
    params = _effective_params(db)
    out = []
    for e in reg.INPUT_ELEMENTS:
        rw = params.get(f"{e.element_code}.risk_weight")
        cf = params.get(f"{e.element_code}.ccf")
        beta = params.get(f"{rules_reg._base_line(e.element_code)}.beta")
        rate = params.get(f"{e.element_code}.charge_rate")
        rule = rules_reg.rule_for(e.element_code,
                                  risk_weight=rw if rw is not None else rate,
                                  ccf=cf, beta=beta)
        edited = any(k in params for k in
                     (f"{e.element_code}.risk_weight", f"{e.element_code}.ccf",
                      f"{e.element_code}.charge_rate", f"{rules_reg._base_line(e.element_code)}.beta"))
        tag = "user-edited" if edited else "system"
        out.append({
            "element_code": e.element_code, "label": e.label, "sheet_name": e.sheet_name,
            "domain": e.source_domain, **rule, "tag": tag,
        })
    out.extend(_buffer_rules(db))
    return out


# Schedule 5 buffer rates are regulatory parameters (not source data elements),
# so they belong in the rule engine as editable rules. Editing routes through
# edit_rule -> config_service buffer scope -> auto-recompute.
_BUFFER_RULES = [
    ("ccb", "Capital Conservation Buffer (CCB)",
     "Fixed conservation buffer of {pct} of total RWA, met with CET1 on top of the 4.50% minimum."),
    ("ccyb", "Countercyclical Capital Buffer (CCyB)",
     "Countercyclical buffer of {pct} of total RWA in force for the reporting jurisdiction."),
    ("dsib", "D-SIB Surcharge",
     "Domestic systemically-important bank surcharge of {pct} of total RWA."),
    ("other", "Other SAMA-prescribed buffers",
     "Any further SAMA-prescribed buffer of {pct} of total RWA."),
]


def _buffer_rules(db: Session) -> list[dict]:
    _, buffers = config_service.get_params_and_buffers(db)
    overridden = {p.key for p in config_service.list_parameters(db) if p.scope == "buffer"}
    out = []
    for key, label, template in _BUFFER_RULES:
        val = float(buffers.get(key, 0))
        edited = key in overridden
        out.append({
            "element_code": f"S5_{key.upper()}", "label": label, "sheet_name": "Schedule 5",
            "domain": "Finance/Risk", "rule_name": "Capital buffer rate", "rule_type": "buffer",
            "plain_english": template.format(pct=f"{val*100:.2f}%"),
            "editable_params": [{"key": key, "label": label, "value": val, "format": "pct"}],
            "origin": "SAMA Basel III capital buffer framework", "editable": True,
            "tag": "user-edited" if edited else "system",
        })
    return out


def edit_rule(db: Session, *, instance_id: int, key: str, value: float, role: str, actor: str) -> dict:
    """Persist a rule parameter override and auto-recompute the draft."""
    _require(role, {"Maker", "Admin"}, "edit rules")
    scope = "buffer" if key in ("ccb", "ccyb", "dsib", "other") else "parameter"
    config_service.set_parameter(db, key=key, value=value, scope=scope,
                                 description=f"Rule override by {actor}")
    audit_service.log(db, actor=actor, action="edit_rule", entity_type="config_parameter",
                      entity_id=key, instance_id=instance_id, after={"value": value})
    db.flush()
    run = calc_service.ensure_current(db, instance_id, actor=actor)
    return {"key": key, "value": value, "recomputed": run is not None}
