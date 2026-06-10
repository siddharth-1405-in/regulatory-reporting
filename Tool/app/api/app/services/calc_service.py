"""Calculation orchestration — the governed entry point to the engine.

Enforces the certification gate, runs the deterministic engine, then persists
the CalcRun, lineage edges and validation results. Agents never call this with
write intent; only a Maker/Checker action or an approved remediation triggers it.
"""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal

from sqlalchemy.orm import Session

from ..calc import engine
from ..calc.types import CarResult
from ..models import CalcRun
from . import (
    audit_service, certification_service, config_service, lineage_service,
    report_instance_service, validation_service,
)


class CertificationGateError(RuntimeError):
    def __init__(self, blocking: list[str]):
        self.blocking = blocking
        super().__init__(f"Calculation blocked: domains not certified: {', '.join(blocking)}")


def _f(x):
    return float(x) if isinstance(x, Decimal) else x


def result_to_dict(result: CarResult) -> dict:
    schedules = {}
    for name, s in result.schedules.items():
        schedules[name] = {
            "lines": [{"element_code": l.element_code, "label": l.label, "section": l.section,
                       "inputs": {k: _f(v) for k, v in l.inputs.items()}, "result": _f(l.result)}
                      for l in s.lines],
            "subtotals": {k: _f(v) for k, v in s.subtotals.items()},
            "totals": {k: _f(v) for k, v in s.totals.items()},
        }
    return {
        "schedules": schedules,
        "values": {k: _f(v) for k, v in result.values.items()},
        "metrics": {k: _f(v) for k, v in result.metrics.items()},
        "flags": result.flags,
    }


def _state_hash(inputs: dict[str, Decimal], params: dict, buffers: dict) -> str:
    payload = json.dumps({
        "i": {k: str(v) for k, v in sorted(inputs.items())},
        "p": {k: str(v) for k, v in sorted(params.items())},
        "b": {k: str(v) for k, v in sorted(buffers.items())},
    })
    return hashlib.sha256(payload.encode()).hexdigest()


def run_calculation(db: Session, instance_id: int, actor: str = "system",
                    enforce_gate: bool = True) -> tuple[CalcRun, CarResult, list]:
    allowed, blocking = certification_service.is_calc_allowed(db, instance_id)
    if enforce_gate and not allowed:
        raise CertificationGateError(blocking)

    inputs = report_instance_service.load_inputs(db, instance_id)
    params, buffers = config_service.get_params_and_buffers(db)
    result = engine.compute(inputs, params=params, buffers=buffers)

    run = CalcRun(instance_id=instance_id, inputs_hash=_state_hash(inputs, params, buffers),
                  results=result_to_dict(result), triggered_by=actor)
    db.add(run)
    db.flush()

    lineage_service.persist(db, instance_id)
    instance = report_instance_service.get(db, instance_id)
    findings = validation_service.evaluate(instance, result)
    validation_service.persist(db, instance_id=instance_id, calc_run_id=run.id, results=findings)

    report_instance_service.set_status(db, instance_id, "VALIDATED", actor=actor)
    audit_service.log(db, actor=actor, action="run_calculation", entity_type="calc_run",
                      entity_id=run.id, instance_id=instance_id,
                      after={"metrics": run.results["metrics"], "flags": run.results["flags"]})
    return run, result, findings


def latest_run(db: Session, instance_id: int) -> CalcRun | None:
    return (db.query(CalcRun).filter(CalcRun.instance_id == instance_id)
            .order_by(CalcRun.created_at.desc(), CalcRun.id.desc()).first())


def ensure_current(db: Session, instance_id: int, actor: str = "system",
                   run_agents: bool = True) -> CalcRun | None:
    """Auto-recompute the draft when data is certified and the effective state
    (inputs + rule params) has changed since the last run. Refreshes AI exception
    analysis + narrative when a fresh computation is produced. No-op (returns the
    latest run) if the state is unchanged; returns None if data is not yet
    certified. This replaces the explicit 'Run Calculation' action."""
    allowed, _ = certification_service.is_calc_allowed(db, instance_id)
    if not allowed:
        return None

    inputs = report_instance_service.load_inputs(db, instance_id)
    params, buffers = config_service.get_params_and_buffers(db)
    current = _state_hash(inputs, params, buffers)
    latest = latest_run(db, instance_id)
    if latest and latest.inputs_hash == current:
        return latest

    run, result, findings = run_calculation(db, instance_id, actor=actor)
    if run_agents:
        from ..models import RemediationProposal
        open_rem = (db.query(RemediationProposal)
                    .filter(RemediationProposal.instance_id == instance_id,
                            RemediationProposal.status == "proposed").count())
        has_fail = any(f["status"] == "fail" for f in findings)
        if has_fail and open_rem == 0:
            from ..agents import orchestrator
            fdicts = [{"rule_code": f["rule_code"], "status": f["status"], "message": f["message"]}
                      for f in findings]
            orchestrator.run_governed_pipeline(db, instance_id, result, fdicts, actor=actor)
    return run
