"""SQLAlchemy 2.x ORM models — governance-first CAR reporting domain.

Governance invariants (enforced in services, not here):
  * no CalcRun until required certifications are complete;
  * any ElementValue change invalidates dependent certifications & downstream;
  * agents write only AgentRun / RemediationProposal / Narrative — never
    ElementValue or CalcRun directly; a RemediationProposal requires Checker
    approval before it is applied.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---- report instance lifecycle ----------------------------------------------
# DRAFT -> INGESTED -> CERTIFYING -> CALCULATED -> VALIDATED
#       -> REMEDIATION -> SIGNED_OFF -> EXPORTED
class ReportPack(Base):
    __tablename__ = "report_pack"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)      # CAR-SA-01
    name: Mapped[str] = mapped_column(String(160))
    regulator: Mapped[str] = mapped_column(String(40), default="SAMA")


class ReportInstance(Base):
    __tablename__ = "report_instance"
    id: Mapped[int] = mapped_column(primary_key=True)
    pack_id: Mapped[int] = mapped_column(ForeignKey("report_pack.id"))
    period_label: Mapped[str] = mapped_column(String(40))           # e.g. "Q2 2025"
    period_end: Mapped[date] = mapped_column(Date)
    bank_name: Mapped[str] = mapped_column(String(160), default="")
    currency: Mapped[str] = mapped_column(String(8), default="SAR")
    units: Mapped[str] = mapped_column(String(16), default="SAR '000")
    status: Mapped[str] = mapped_column(String(24), default="DRAFT")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    pack: Mapped[ReportPack] = relationship()


class CanonicalElement(Base):
    """Registry mirror (for FK/joins/lineage). Seeded from the code registry."""
    __tablename__ = "canonical_element"
    element_code: Mapped[str] = mapped_column(String(48), primary_key=True)
    label: Mapped[str] = mapped_column(String(240))
    sheet_name: Mapped[str] = mapped_column(String(40))
    section_name: Mapped[str] = mapped_column(String(80))
    source_domain: Mapped[str | None] = mapped_column(String(24))
    source_type: Mapped[str] = mapped_column(String(16))
    lineage_level: Mapped[str] = mapped_column(String(24))


class ElementValue(Base):
    """A raw input value for an element on a report instance (versioned)."""
    __tablename__ = "element_value"
    id: Mapped[int] = mapped_column(primary_key=True)
    instance_id: Mapped[int] = mapped_column(ForeignKey("report_instance.id"))
    element_code: Mapped[str] = mapped_column(String(48), index=True)
    raw_value: Mapped[float] = mapped_column(Numeric(24, 3), default=0)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_by: Mapped[str] = mapped_column(String(80), default="system")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# ---- ingestion + data quality ----------------------------------------------
class IngestionBatch(Base):
    __tablename__ = "ingestion_batch"
    id: Mapped[int] = mapped_column(primary_key=True)
    instance_id: Mapped[int] = mapped_column(ForeignKey("report_instance.id"))
    domain: Mapped[str] = mapped_column(String(24))
    source_label: Mapped[str] = mapped_column(String(120))
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class DQFinding(Base):
    __tablename__ = "dq_finding"
    id: Mapped[int] = mapped_column(primary_key=True)
    instance_id: Mapped[int] = mapped_column(ForeignKey("report_instance.id"))
    element_code: Mapped[str | None] = mapped_column(String(48))
    severity: Mapped[str] = mapped_column(String(16))      # info | warn | error
    message: Mapped[str] = mapped_column(Text)


# ---- ownership + certification ----------------------------------------------
class OwnershipAssignment(Base):
    __tablename__ = "ownership_assignment"
    id: Mapped[int] = mapped_column(primary_key=True)
    data_element: Mapped[str] = mapped_column(String(160))
    domain: Mapped[str] = mapped_column(String(24))         # Finance | Risk
    steward: Mapped[str] = mapped_column(String(80))
    source_system: Mapped[str] = mapped_column(String(80), default="")
    frequency: Mapped[str] = mapped_column(String(24), default="")
    ai_action: Mapped[str] = mapped_column(Text, default="")


class Certification(Base):
    __tablename__ = "certification"
    id: Mapped[int] = mapped_column(primary_key=True)
    instance_id: Mapped[int] = mapped_column(ForeignKey("report_instance.id"))
    domain: Mapped[str] = mapped_column(String(24))
    status: Mapped[str] = mapped_column(String(24), default="Not Started")  # Not Started|In Review|Certified|Invalidated
    certified_by: Mapped[str | None] = mapped_column(String(80))
    certified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str] = mapped_column(Text, default="")


# ---- calculation + validation + lineage -------------------------------------
class CalcRun(Base):
    __tablename__ = "calc_run"
    id: Mapped[int] = mapped_column(primary_key=True)
    instance_id: Mapped[int] = mapped_column(ForeignKey("report_instance.id"))
    inputs_hash: Mapped[str] = mapped_column(String(64))
    results: Mapped[dict] = mapped_column(JSON, default=dict)   # values + metrics + flags
    triggered_by: Mapped[str] = mapped_column(String(80), default="system")
    status: Mapped[str] = mapped_column(String(24), default="complete")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ValidationResult(Base):
    __tablename__ = "validation_result"
    id: Mapped[int] = mapped_column(primary_key=True)
    calc_run_id: Mapped[int] = mapped_column(ForeignKey("calc_run.id"))
    instance_id: Mapped[int] = mapped_column(ForeignKey("report_instance.id"))
    rule_code: Mapped[str] = mapped_column(String(48))
    status: Mapped[str] = mapped_column(String(12))            # pass | warn | fail
    message: Mapped[str] = mapped_column(Text)
    elements: Mapped[list] = mapped_column(JSON, default=list)
    remediation_hint: Mapped[str] = mapped_column(Text, default="")


class LineageEdge(Base):
    __tablename__ = "lineage_edge"
    id: Mapped[int] = mapped_column(primary_key=True)
    instance_id: Mapped[int] = mapped_column(ForeignKey("report_instance.id"))
    from_code: Mapped[str] = mapped_column(String(48))
    to_code: Mapped[str] = mapped_column(String(48))
    relation: Mapped[str] = mapped_column(String(40), default="feeds")


# ---- governed agents --------------------------------------------------------
class AgentRun(Base):
    __tablename__ = "agent_run"
    id: Mapped[int] = mapped_column(primary_key=True)
    instance_id: Mapped[int] = mapped_column(ForeignKey("report_instance.id"))
    agent_type: Mapped[str] = mapped_column(String(40))   # anomaly|remediation|narrative|circular_parsing
    evidence_used: Mapped[list] = mapped_column(JSON, default=list)
    reasoning_summary: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), default=0)
    impacted_metrics: Mapped[list] = mapped_column(JSON, default=list)
    proposed_action: Mapped[str] = mapped_column(Text, default="")
    approval_required: Mapped[bool] = mapped_column(Boolean, default=True)
    prompt_version: Mapped[str] = mapped_column(String(24), default="v1")
    model_version: Mapped[str] = mapped_column(String(48), default="deterministic-stub")
    status: Mapped[str] = mapped_column(String(24), default="proposed")  # proposed|approved|rejected
    approved_by: Mapped[str | None] = mapped_column(String(80))
    output: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class RemediationProposal(Base):
    __tablename__ = "remediation_proposal"
    id: Mapped[int] = mapped_column(primary_key=True)
    agent_run_id: Mapped[int] = mapped_column(ForeignKey("agent_run.id"))
    instance_id: Mapped[int] = mapped_column(ForeignKey("report_instance.id"))
    element_code: Mapped[str] = mapped_column(String(48))
    current_value: Mapped[float] = mapped_column(Numeric(24, 3), default=0)
    proposed_value: Mapped[float] = mapped_column(Numeric(24, 3), default=0)
    rationale: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(24), default="proposed")  # proposed|approved|rejected
    maker: Mapped[str] = mapped_column(String(80), default="remediation_agent")
    checker: Mapped[str | None] = mapped_column(String(80))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    maker_rationale: Mapped[str] = mapped_column(Text, default="")   # accept AI rec or alternate action
    checker_comment: Mapped[str] = mapped_column(Text, default="")


class Narrative(Base):
    __tablename__ = "narrative"
    id: Mapped[int] = mapped_column(primary_key=True)
    instance_id: Mapped[int] = mapped_column(ForeignKey("report_instance.id"))
    language: Mapped[str] = mapped_column(String(8))      # en | ar
    version: Mapped[int] = mapped_column(Integer, default=1)
    body: Mapped[str] = mapped_column(Text, default="")
    citations: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), default=0)
    status: Mapped[str] = mapped_column(String(24), default="draft")  # draft|approved|sent
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class CircularChange(Base):
    __tablename__ = "circular_change"
    id: Mapped[int] = mapped_column(primary_key=True)
    regulator: Mapped[str] = mapped_column(String(40))
    standard: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    affected_reports: Mapped[str] = mapped_column(String(160), default="")
    affected_elements: Mapped[str] = mapped_column(String(240), default="")
    action_required: Mapped[str] = mapped_column(Text, default="")
    owner: Mapped[str] = mapped_column(String(80), default="")
    target_date: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(String(40), default="Not Started")
    impact_analysis: Mapped[dict] = mapped_column(JSON, default=dict)  # from circular_parsing_agent


# ---- audit + config ---------------------------------------------------------
class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    instance_id: Mapped[int | None] = mapped_column(ForeignKey("report_instance.id"))
    actor: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str] = mapped_column(String(48))
    entity_id: Mapped[str] = mapped_column(String(48), default="")
    before: Mapped[dict] = mapped_column(JSON, default=dict)
    after: Mapped[dict] = mapped_column(JSON, default=dict)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ConfigParameter(Base):
    __tablename__ = "config_parameter"
    id: Mapped[int] = mapped_column(primary_key=True)
    pack_code: Mapped[str] = mapped_column(String(40), default="CAR-SA-01")
    key: Mapped[str] = mapped_column(String(80), index=True)   # e.g. S2_ON_CORP_BBB.risk_weight, ccb
    value: Mapped[float] = mapped_column(Numeric(18, 6))
    scope: Mapped[str] = mapped_column(String(24), default="parameter")  # parameter|buffer
    description: Mapped[str] = mapped_column(String(200), default="")


# ---- data-layer element governance (per instance + element) -----------------
# status lifecycle (maker-checker on the shared canonical data layer):
#   draft -> edited -> frozen -> submitted -> certified
#                                   submitted -> rejected -> (edited)
#   certified -> invalidated  (when an approved value later changes)
class ElementGovernance(Base):
    __tablename__ = "element_governance"
    id: Mapped[int] = mapped_column(primary_key=True)
    instance_id: Mapped[int] = mapped_column(ForeignKey("report_instance.id"), index=True)
    element_code: Mapped[str] = mapped_column(String(48), index=True)
    status: Mapped[str] = mapped_column(String(16), default="draft")
    last_updated_by: Mapped[str] = mapped_column(String(80), default="system")
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    submitted_by: Mapped[str | None] = mapped_column(String(80))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(String(80))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reject_reason: Mapped[str] = mapped_column(Text, default="")
    # governed manual override (system/raw value stays in ElementValue.raw_value)
    override_value: Mapped[float | None] = mapped_column(Numeric(24, 3))
    override_reason: Mapped[str] = mapped_column(Text, default="")


# ---- enterprise source systems ---------------------------------------------
class SourceSystem(Base):
    __tablename__ = "source_system"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(24), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    vendor: Mapped[str] = mapped_column(String(48))
    category: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(16), default="connected")  # connected|degraded|offline
    used_in_car: Mapped[bool] = mapped_column(Boolean, default=False)
    steward: Mapped[str] = mapped_column(String(80), default="")
    coverage: Mapped[str] = mapped_column(String(200), default="")
    last_ingest_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ---- report-side sign-off (schedule + summary), distinct from data cert -----
class ScheduleSignoff(Base):
    __tablename__ = "schedule_signoff"
    id: Mapped[int] = mapped_column(primary_key=True)
    instance_id: Mapped[int] = mapped_column(ForeignKey("report_instance.id"), index=True)
    schedule_key: Mapped[str] = mapped_column(String(16))   # Cover|Summary|S1..S6
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|signed_off|reopened
    signed_by: Mapped[str | None] = mapped_column(String(80))
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    comment: Mapped[str] = mapped_column(Text, default="")
