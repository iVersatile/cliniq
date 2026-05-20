from __future__ import annotations

from datetime import date
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class ConditionStatus(StrEnum):
    ACTIVE = "active"
    MONITORING = "monitoring"
    RESOLVED = "resolved"
    UNKNOWN = "unknown"


class ConditionEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_date: date | None = None
    measurement: str | None = None
    notes: str | None = None
    clinician_id: UUID | None = None
    source_note_id: UUID | None = None


class Condition(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    name: str
    body_site: str | None = None
    status: ConditionStatus = ConditionStatus.UNKNOWN
    diagnosed_date: date | None = None
    last_review_date: date | None = None
    linked_medication_ids: list[UUID] = Field(default_factory=list)
    history: list[ConditionEvent] = Field(default_factory=list)
    citation: str | None = None
