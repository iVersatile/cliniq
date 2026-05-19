"""Unit tests for Pydantic schemas."""

import json
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from cliniq.schemas.appointment import Appointment
from cliniq.schemas.contact import Contact
from cliniq.schemas.medical_note import Diagnosis, MedicalNote, NoteType
from cliniq.schemas.medication import Medication
from cliniq.schemas.symptom import Symptom

FIXTURES = Path(__file__).parent / "fixtures" / "schemas"


# ---------------------------------------------------------------------------
# Fixture-based round-trip validation
# ---------------------------------------------------------------------------


def test_medical_note_fixture() -> None:
    data = json.loads((FIXTURES / "medical_note.json").read_text())
    note = MedicalNote.model_validate(data)
    assert note.type == NoteType.OUTPATIENT_LETTER
    assert note.diagnoses[0].code == "I10"


def test_contact_fixture() -> None:
    data = json.loads((FIXTURES / "contact.json").read_text())
    contact = Contact.model_validate(data)
    assert contact.is_clinic is True
    assert contact.speciality == "Cardiology"


def test_appointment_fixture() -> None:
    data = json.loads((FIXTURES / "appointment.json").read_text())
    appt = Appointment.model_validate(data)
    assert str(appt.date) == "2025-06-12"
    assert appt.status.value == "upcoming"


def test_medication_fixture() -> None:
    data = json.loads((FIXTURES / "medication.json").read_text())
    med = Medication.model_validate(data)
    assert med.name == "Amlodipine"
    assert med.end_date is None


def test_symptom_fixture() -> None:
    data = json.loads((FIXTURES / "symptom.json").read_text())
    symptom = Symptom.model_validate(data)
    assert symptom.symptom == "persistent dizziness on standing"
    assert len(symptom.linked_note_ids) == 1


# ---------------------------------------------------------------------------
# Frozen / immutability enforcement
# ---------------------------------------------------------------------------


def test_medical_note_frozen() -> None:
    note = MedicalNote(date=date(2025, 3, 14), source_file="letter.pdf")
    with pytest.raises((ValidationError, TypeError)):
        note.summary = "mutated"  # type: ignore[misc]


def test_contact_frozen() -> None:
    c = Contact(name="Royal Free Hospital")
    with pytest.raises((ValidationError, TypeError)):
        c.name = "mutated"  # type: ignore[misc]


def test_appointment_frozen() -> None:
    appt = Appointment(date=date(2025, 6, 12))
    with pytest.raises((ValidationError, TypeError)):
        appt.reason = "mutated"  # type: ignore[misc]


def test_medication_frozen() -> None:
    med = Medication(name="Amlodipine")
    with pytest.raises((ValidationError, TypeError)):
        med.name = "mutated"  # type: ignore[misc]


def test_symptom_frozen() -> None:
    s = Symptom(symptom="headache")
    with pytest.raises((ValidationError, TypeError)):
        s.symptom = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Pre-existing behaviour tests (kept)
# ---------------------------------------------------------------------------


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
