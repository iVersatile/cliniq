from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Contact(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    address: str = ""
    phone: str = ""
    speciality: str = ""
    is_clinic: bool = True
