from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AppointmentStatus(StrEnum):
    PAST = "past"
    UPCOMING = "upcoming"
    CANCELLED = "cancelled"


class Appointment(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    date: date
    clinic_id: UUID | None = None
    clinician_id: UUID | None = None
    reason: str = ""
    status: AppointmentStatus = AppointmentStatus.PAST
    reminder_at: datetime | None = None
