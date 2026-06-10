"""Rule engine — plain-English transformation rules over canonical elements.

Reads effective rule parameters (registry defaults + config_service overrides),
renders the plain-English rule and machine structure, and tags provenance
(system / user-edited / override). Editing a rule persists a parameter override
and triggers auto-recompute.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from ..models import ElementGovernance
from ..registry.car_sa01 import elements as reg
from ..registry.car_sa01 import rules as rules_reg
from . import audit_service, calc_service, config_service
from .data_layer_service import RolePermissionError, _require


def _effective_params(db: Session) -> dict[str, Decimal]:
    params, _ = config_service.get_params_and_buffers(db)
    return params


def list_rules(db: Session, instance_id: int) -> list[dict]:
    params = _effective_params(db)
    overrides = {g.element_code for g in
                 db.query(ElementGovernance)
                 .filter(ElementGovernance.instance_id == instance_id,
                         ElementGovernance.override_value.isnot(None)).all()}
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
        tag = "override" if e.element_code in overrides else ("user-edited" if edited else "system")
        out.append({
            "element_code": e.element_code, "label": e.label, "sheet_name": e.sheet_name,
            "domain": e.source_domain, **rule, "tag": tag,
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
