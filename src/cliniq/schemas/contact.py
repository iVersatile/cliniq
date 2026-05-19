from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class Contact(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    name: str
    address: str = ""
    phone: str = ""
    speciality: str = ""
    is_clinic: bool = True
