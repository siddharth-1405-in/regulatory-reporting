"""Pydantic v2 request/response schemas."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class CreateInstance(BaseModel):
    period_label: str
    period_end: date
    bank_name: str
    actor: str = "maker"


class IngestRequest(BaseModel):
    domain: str
    source_label: str = "manual"
    values: dict[str, float]
    actor: str = "maker"


class CertifyRequest(BaseModel):
    actor: str = "checker"


class ActorRequest(BaseModel):
    actor: str = "checker"
    reason: str = ""


class SetParameter(BaseModel):
    key: str
    value: float
    scope: str = "parameter"
    description: str = ""


class InstanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    period_label: str
    period_end: date
    bank_name: str
    currency: str
    units: str
    status: str
    created_at: datetime
