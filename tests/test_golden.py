"""Golden-file tests for extraction prompts."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cliniq.extraction.engine import ExtractionResult
from cliniq.extraction.prompts.appointment import extract_appointments
from cliniq.extraction.prompts.contact import extract_contacts
from cliniq.extraction.prompts.medical_note import (
    extract_medical_note,
    extract_medical_note_discharge,
    extract_medical_note_lab_report,
)
from cliniq.extraction.prompts.medication import extract_medications
from cliniq.ingestion.pdf_reader import DocumentText, PageText
from cliniq.schemas.appointment import Appointment
from cliniq.schemas.contact import Contact
from cliniq.schemas.medical_note import MedicalNote, NoteType
from cliniq.schemas.medication import Medication

FIXTURES = Path(__file__).parent / "fixtures"
GOLDEN = FIXTURES / "golden"

# Auto-discovered golden files for parametrized schema-contract tests.
_NOTE_FILES = sorted(GOLDEN.glob("*_note.json"))
_MEDICATION_FILES = sorted(GOLDEN.glob("medications*.json"))
_CONTACT_FILES = sorted(GOLDEN.glob("contacts*.json"))
_APPOINTMENT_FILES = sorted(GOLDEN.glob("appointments*.json"))

# Fields generated at instantiation time — excluded from roundtrip comparison.
_NOTE_EXCLUDE = {"id", "clinic_id", "clinician_id", "medication_ids", "next_appointment_id"}
_ID_EXCLUDE = {"id"}


def _load(name: str) -> object:
    return json.loads((GOLDEN / name).read_text())


def _mock_adapter(golden_data: object) -> MagicMock:
    adapter = MagicMock()
    adapter.complete_json.return_value = golden_data
    return adapter


def _make_doc(source_file: str) -> DocumentText:
    pdf = FIXTURES / source_file
    return DocumentText(
        source_file=pdf,
        pages=[PageText(page_number=1, text="stub", via_ocr=False)],
    )


# ---------------------------------------------------------------------------
# Outpatient note
# ---------------------------------------------------------------------------


def test_golden_outpatient_note_validates() -> None:
    data = _load("outpatient_note.json")
    doc = _make_doc("ccl_mri_request_001_mock.pdf")
    result = ExtractionResult(source=doc.source_file)

    extract_medical_note(doc, _mock_adapter(data), result)

    assert len(result.notes) == 1
    note = result.notes[0]
    assert note.type == NoteType.OUTPATIENT_LETTER
    expected = MedicalNote.model_validate(data)
    assert note.model_dump(exclude=_NOTE_EXCLUDE) == expected.model_dump(exclude=_NOTE_EXCLUDE)


# ---------------------------------------------------------------------------
# Discharge note
# ---------------------------------------------------------------------------


def test_golden_discharge_note_validates() -> None:
    data = _load("discharge_note.json")
    doc = _make_doc("iofpm_healthcheck_001_mock.pdf")
    result = ExtractionResult(source=doc.source_file)

    extract_medical_note_discharge(doc, _mock_adapter(data), result)

    assert len(result.notes) == 1
    note = result.notes[0]
    assert note.type == NoteType.DISCHARGE_SUMMARY
    expected = MedicalNote.model_validate(data)
    assert note.model_dump(exclude=_NOTE_EXCLUDE) == expected.model_dump(exclude=_NOTE_EXCLUDE)


# ---------------------------------------------------------------------------
# Lab report
# ---------------------------------------------------------------------------


def test_golden_lab_report_validates() -> None:
    data = _load("lab_report_note.json")
    doc = _make_doc("allergy_isac_001_mock.pdf")
    result = ExtractionResult(source=doc.source_file)

    extract_medical_note_lab_report(doc, _mock_adapter(data), result)

    assert len(result.notes) == 1
    note = result.notes[0]
    assert note.type == NoteType.LAB_REPORT
    expected = MedicalNote.model_validate(data)
    assert note.model_dump(exclude=_NOTE_EXCLUDE) == expected.model_dump(exclude=_NOTE_EXCLUDE)


# ---------------------------------------------------------------------------
# Medications
# ---------------------------------------------------------------------------


def test_golden_medications_validate() -> None:
    data = _load("medications.json")
    doc = _make_doc("iofpm_consult_notes_001_mock.pdf")
    result = ExtractionResult(source=doc.source_file)

    extract_medications(doc, _mock_adapter(data), result)

    assert isinstance(data, list)
    assert len(result.medications) == len(data)
    for actual, raw in zip(result.medications, data):
        expected = Medication.model_validate(raw).model_dump(exclude=_ID_EXCLUDE)
        assert actual.model_dump(exclude=_ID_EXCLUDE) == expected


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------


def test_golden_contacts_validate() -> None:
    data = _load("contacts.json")
    doc = _make_doc("ccl_mri_request_001_mock.pdf")
    result = ExtractionResult(source=doc.source_file)

    extract_contacts(doc, _mock_adapter(data), result)

    assert isinstance(data, list)
    assert len(result.contacts) == len(data)
    for actual, raw in zip(result.contacts, data):
        expected = Contact.model_validate(raw).model_dump(exclude=_ID_EXCLUDE)
        assert actual.model_dump(exclude=_ID_EXCLUDE) == expected


# ---------------------------------------------------------------------------
# Appointments
# ---------------------------------------------------------------------------


def test_golden_appointments_validate() -> None:
    data = _load("appointments.json")
    doc = _make_doc("iofpm_consult_notes_001_mock.pdf")
    result = ExtractionResult(source=doc.source_file)

    extract_appointments(doc, _mock_adapter(data), result)

    assert isinstance(data, list)
    assert len(result.appointments) == len(data)
    for actual, raw in zip(result.appointments, data):
        expected = Appointment.model_validate(raw).model_dump(exclude=_ID_EXCLUDE)
        assert actual.model_dump(exclude=_ID_EXCLUDE) == expected


# ---------------------------------------------------------------------------
# Schema-contract tests — auto-discover golden files (P1-13)
# Breaking-change gate: model_validate fails if required field removed/renamed.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("golden_path", _NOTE_FILES, ids=lambda p: p.name)
def test_golden_medical_note_schema_contract(golden_path: Path) -> None:
    data = json.loads(golden_path.read_text())
    MedicalNote.model_validate(data)


@pytest.mark.parametrize("golden_path", _MEDICATION_FILES, ids=lambda p: p.name)
def test_golden_medication_schema_contract(golden_path: Path) -> None:
    data = json.loads(golden_path.read_text())
    assert isinstance(data, list)
    for item in data:
        Medication.model_validate(item)


@pytest.mark.parametrize("golden_path", _CONTACT_FILES, ids=lambda p: p.name)
def test_golden_contact_schema_contract(golden_path: Path) -> None:
    data = json.loads(golden_path.read_text())
    assert isinstance(data, list)
    for item in data:
        Contact.model_validate(item)


@pytest.mark.parametrize("golden_path", _APPOINTMENT_FILES, ids=lambda p: p.name)
def test_golden_appointment_schema_contract(golden_path: Path) -> None:
    data = json.loads(golden_path.read_text())
    assert isinstance(data, list)
    for item in data:
        Appointment.model_validate(item)
