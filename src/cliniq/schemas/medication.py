from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Medication(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    dose: str = ""
    frequency: str = ""
    start_date: date | None = None
    end_date: date | None = None
    prescribed_by: UUID | None = None
