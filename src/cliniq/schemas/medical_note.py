from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class NoteType(StrEnum):
    OUTPATIENT_LETTER = "outpatient_letter"
    DISCHARGE_SUMMARY = "discharge_summary"
    LAB_REPORT = "lab_report"
    RADIOLOGY = "radiology"
    GP_NOTE = "gp_note"
    PRESCRIPTION = "prescription"
    OTHER = "other"


class Diagnosis(BaseModel):
    code: str
    system: Literal["ICD-10", "SNOMED-CT", "other"] = "ICD-10"
    label: str


class NoteFlag(StrEnum):
    HANDWRITTEN_SECTION = "HANDWRITTEN_SECTION"
    LOW_OCR_CONFIDENCE = "LOW_OCR_CONFIDENCE"


class MedicalNote(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    date: date
    source_file: str
    clinic_id: UUID | None = None
    clinician_id: UUID | None = None
    type: NoteType = NoteType.OTHER
    summary: str = ""
    diagnoses: list[Diagnosis] = Field(default_factory=list)
    medication_ids: list[UUID] = Field(default_factory=list)
    next_appointment_id: UUID | None = None
    flags: list[NoteFlag] = Field(default_factory=list)
    raw_text: str = ""
    sections: dict[str, str] = Field(default_factory=dict)
