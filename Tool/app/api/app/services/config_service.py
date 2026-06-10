"""Configuration of deterministic regulatory parameters.

Resolves per-line rate overrides and buffer rates from the ConfigParameter
table, falling back to the registry defaults. Returns the (params, buffers)
dicts consumed by the calc engine, so Admin edits flow into every recalc.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from ..models import ConfigParameter
from ..registry.car_sa01.parameters import BUFFER_RATES, D


def get_params_and_buffers(db: Session, pack_code: str = "CAR-SA-01") -> tuple[dict[str, Decimal], dict[str, Decimal]]:
    rows = db.query(ConfigParameter).filter(ConfigParameter.pack_code == pack_code).all()
    params: dict[str, Decimal] = {}
    buffers: dict[str, Decimal] = {k: D(v) for k, v in BUFFER_RATES.items()}
    for r in rows:
        if r.scope == "buffer":
            buffers[r.key] = D(r.value)
        else:
            params[r.key] = D(r.value)
    return params, buffers


def set_parameter(db: Session, *, key: str, value: Decimal | float, scope: str = "parameter",
                  pack_code: str = "CAR-SA-01", description: str = "") -> ConfigParameter:
    row = (db.query(ConfigParameter)
           .filter(ConfigParameter.pack_code == pack_code, ConfigParameter.key == key)
           .one_or_none())
    if row is None:
        row = ConfigParameter(pack_code=pack_code, key=key, scope=scope, description=description)
        db.add(row)
    row.value = float(value)
    row.scope = scope
    if description:
        row.description = description
    db.flush()
    return row


def list_parameters(db: Session, pack_code: str = "CAR-SA-01") -> list[ConfigParameter]:
    return (db.query(ConfigParameter)
            .filter(ConfigParameter.pack_code == pack_code)
            .order_by(ConfigParameter.scope, ConfigParameter.key).all())
