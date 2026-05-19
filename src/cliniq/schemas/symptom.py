from __future__ import annotations

from datetime import date
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class SeverityTrend(StrEnum):
    IMPROVING = "improving"
    STABLE = "stable"
    WORSENING = "worsening"
    RESOLVED = "resolved"
    UNKNOWN = "unknown"


class Symptom(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    symptom: str
    first_noted: date | None = None
    last_noted: date | None = None
    severity_trend: SeverityTrend = SeverityTrend.UNKNOWN
    linked_note_ids: list[UUID] = Field(default_factory=list)
