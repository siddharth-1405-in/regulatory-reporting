"""Domain certification — gating and invalidation.

Governance invariants:
  * Calculation is BLOCKED until every required domain (Finance, Risk) has a
    current 'Certified' status for the instance.
  * Any change to an input element invalidates the certification of the domain
    that owns it, re-blocking calculation until re-certified.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..models import Certification, ElementGovernance
from . import audit_service, ownership_service


def _now():
    return datetime.now(timezone.utc)


def _gov_row(db: Session, instance_id: int, code: str) -> ElementGovernance:
    row = (db.query(ElementGovernance)
           .filter(ElementGovernance.instance_id == instance_id,
                   ElementGovernance.element_code == code).one_or_none())
    if row is None:
        row = ElementGovernance(instance_id=instance_id, element_code=code, status="draft")
        db.add(row)
        db.flush()
    return row


def _cascade_elements(db: Session, instance_id: int, domain: str, status: str, actor: str) -> None:
    """Keep element governance in lockstep with a domain-level certify."""
    for code in ownership_service.elements_for_domain(domain):
        row = _gov_row(db, instance_id, code)
        row.status = status
        if status == "certified":
            row.approved_by = actor
            row.approved_at = _now()
    db.flush()


def _get_or_create(db: Session, instance_id: int, domain: str) -> Certification:
    cert = (db.query(Certification)
            .filter(Certification.instance_id == instance_id, Certification.domain == domain)
            .one_or_none())
    if cert is None:
        cert = Certification(instance_id=instance_id, domain=domain, status="Not Started")
        db.add(cert)
        db.flush()
    return cert


def ensure_domains(db: Session, instance_id: int) -> None:
    for domain in sorted(ownership_service.required_domains()):
        _get_or_create(db, instance_id, domain)


def set_status(db: Session, instance_id: int, domain: str, status: str,
               actor: str = "system", reason: str = "") -> Certification:
    cert = _get_or_create(db, instance_id, domain)
    before = cert.status
    cert.status = status
    cert.reason = reason
    if status == "Certified":
        cert.certified_by = actor
        cert.certified_at = _now()
        cert.invalidated_at = None
    db.flush()
    audit_service.log(db, actor=actor, action="certify", entity_type="certification",
                      entity_id=cert.id, instance_id=instance_id,
                      before={"status": before}, after={"status": status, "domain": domain})
    return cert


def certify(db: Session, instance_id: int, domain: str, actor: str) -> Certification:
    cert = set_status(db, instance_id, domain, "Certified", actor=actor)
    _cascade_elements(db, instance_id, domain, "certified", actor)
    return cert


def invalidate_for_elements(db: Session, instance_id: int, changed_codes: list[str],
                            actor: str = "system") -> list[str]:
    """Invalidate certifications for any domain owning a changed element, and
    flip any already-approved element governance rows to 'invalidated'."""
    # element-level: an approved/in-flight value that changes is invalidated
    for code in changed_codes:
        row = (db.query(ElementGovernance)
               .filter(ElementGovernance.instance_id == instance_id,
                       ElementGovernance.element_code == code).one_or_none())
        if row and row.status in ("certified", "submitted", "frozen"):
            row.status = "invalidated"

    domains = {d for d in (ownership_service.domain_for_element(c) for c in changed_codes) if d}
    invalidated = []
    for domain in domains:
        cert = (db.query(Certification)
                .filter(Certification.instance_id == instance_id,
                        Certification.domain == domain).one_or_none())
        if cert and cert.status == "Certified":
            cert.status = "Invalidated"
            cert.invalidated_at = _now()
            cert.reason = "Upstream data changed after certification"
            invalidated.append(domain)
            audit_service.log(db, actor=actor, action="invalidate_certification",
                              entity_type="certification", entity_id=cert.id,
                              instance_id=instance_id, after={"domain": domain})
    db.flush()
    return invalidated


def status_map(db: Session, instance_id: int) -> dict[str, str]:
    ensure_domains(db, instance_id)
    return {c.domain: c.status for c in
            db.query(Certification).filter(Certification.instance_id == instance_id).all()}


def is_calc_allowed(db: Session, instance_id: int) -> tuple[bool, list[str]]:
    """Returns (allowed, blocking_domains)."""
    statuses = status_map(db, instance_id)
    blocking = [d for d in sorted(ownership_service.required_domains())
                if statuses.get(d) != "Certified"]
    return (len(blocking) == 0, blocking)
