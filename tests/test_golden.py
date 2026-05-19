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
    assert note.diagnoses[0].code == "R51"
    assert note.diagnoses[0].citation is not None


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
    assert note.diagnoses[0].code == "Z00.0"
    assert note.diagnoses[0].citation is not None


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
    assert note.diagnoses[0].code == "J30.1"
    assert note.diagnoses[0].citation is not None


# ---------------------------------------------------------------------------
# Medications
# ---------------------------------------------------------------------------


def test_golden_medications_validate() -> None:
    data = _load("medications.json")
    doc = _make_doc("iofpm_consult_notes_001_mock.pdf")
    result = ExtractionResult(source=doc.source_file)

    extract_medications(doc, _mock_adapter(data), result)

    assert len(result.medications) == 2
    assert result.medications[0].name == "Lansoprazole"
    assert result.medications[0].citation is not None
    assert result.medications[1].name == "Cetirizine"


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------


def test_golden_contacts_validate() -> None:
    data = _load("contacts.json")
    doc = _make_doc("ccl_mri_request_001_mock.pdf")
    result = ExtractionResult(source=doc.source_file)

    extract_contacts(doc, _mock_adapter(data), result)

    assert len(result.contacts) == 1
    assert result.contacts[0].name == "Institute of Preventative Medicine"
    assert result.contacts[0].is_clinic is True


# ---------------------------------------------------------------------------
# Appointments
# ---------------------------------------------------------------------------


def test_golden_appointments_validate() -> None:
    data = _load("appointments.json")
    doc = _make_doc("iofpm_consult_notes_001_mock.pdf")
    result = ExtractionResult(source=doc.source_file)

    extract_appointments(doc, _mock_adapter(data), result)

    assert len(result.appointments) == 1
    assert str(result.appointments[0].date) == "2022-03-10"
    assert result.appointments[0].status.value == "upcoming"


# ---------------------------------------------------------------------------
# Schema-contract tests (breaking-change gate)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "golden_file",
    ["outpatient_note.json", "discharge_note.json", "lab_report_note.json"],
)
def test_golden_medical_note_schema_contract(golden_file: str) -> None:
    data = _load(golden_file)
    MedicalNote.model_validate(data)


@pytest.mark.parametrize("golden_file", ["medications.json"])
def test_golden_medication_schema_contract(golden_file: str) -> None:
    data = _load(golden_file)
    assert isinstance(data, list)
    for item in data:
        Medication.model_validate(item)


@pytest.mark.parametrize("golden_file", ["contacts.json"])
def test_golden_contact_schema_contract(golden_file: str) -> None:
    data = _load(golden_file)
    assert isinstance(data, list)
    for item in data:
        Contact.model_validate(item)


@pytest.mark.parametrize("golden_file", ["appointments.json"])
def test_golden_appointment_schema_contract(golden_file: str) -> None:
    data = _load(golden_file)
    assert isinstance(data, list)
    for item in data:
        Appointment.model_validate(item)
