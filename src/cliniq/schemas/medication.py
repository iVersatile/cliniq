from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class Medication(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    name: str
    dose: str = ""
    frequency: str = ""
    start_date: date | None = None
    end_date: date | None = None
    prescribed_by: UUID | None = None
    prescribed_by_name: str | None = None
    duration_label: str | None = None
    citation: str | None = None
