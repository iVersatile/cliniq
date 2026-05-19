"""Unit tests for Pydantic schemas."""

from datetime import date

from cliniq.schemas.contact import Contact
from cliniq.schemas.medical_note import Diagnosis, MedicalNote, NoteType
from cliniq.schemas.medication import Medication


def test_medical_note_defaults() -> None:
    note = MedicalNote(date=date(2025, 3, 14), source_file="letter.pdf")
    assert note.type == NoteType.OTHER
    assert note.diagnoses == []
    assert note.flags == []


def test_medical_note_with_diagnosis() -> None:
    note = MedicalNote(
        date=date(2025, 3, 14),
        source_file="letter.pdf",
        diagnoses=[Diagnosis(code="I10", label="Hypertension")],
    )
    data = note.model_dump(mode="json")
    assert data["diagnoses"][0]["code"] == "I10"


def test_medication_roundtrip() -> None:
    med = Medication(name="Amlodipine", dose="5mg", frequency="once daily")
    assert Medication.model_validate(med.model_dump()).name == "Amlodipine"


def test_contact_is_clinic_default() -> None:
    c = Contact(name="Royal Free Hospital")
    assert c.is_clinic is True
