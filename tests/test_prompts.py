"""Tests for extraction prompts."""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock

from cliniq.extraction.engine import ExtractionResult
from cliniq.extraction.prompts import extract_all
from cliniq.extraction.prompts.appointment import extract_appointments
from cliniq.extraction.prompts.contact import extract_contacts
from cliniq.extraction.prompts.medical_note import (
    extract_medical_note,
    extract_medical_note_discharge,
    extract_medical_note_lab_report,
)
from cliniq.extraction.prompts.medication import extract_medications
from cliniq.ingestion.pdf_reader import DocumentText, PageText


def _stub_args() -> tuple[MagicMock, MagicMock, MagicMock]:
    doc = MagicMock()
    adapter = MagicMock()
    result = MagicMock()
    return doc, adapter, result


def _make_doc(text: str) -> DocumentText:
    return DocumentText(
        source_file=Path("test.pdf"),
        pages=[PageText(page_number=1, text=text, via_ocr=False)],
    )


def test_extract_all_calls_each_prompt() -> None:
    doc, adapter, result = _stub_args()
    extract_all(doc, adapter, result)


def test_extract_contacts_no_raise() -> None:
    extract_contacts(*_stub_args())


def test_extract_medications_no_raise() -> None:
    extract_medications(*_stub_args())


def test_extract_appointments_no_raise() -> None:
    extract_appointments(*_stub_args())


def test_extract_medical_note_no_raise() -> None:
    extract_medical_note(*_stub_args())


def test_extract_medical_note_outpatient_appends_note() -> None:
    """Adapter returns valid MedicalNote dict → note appended to result."""
    doc = _make_doc("Dear Dr Smith, patient reviewed in cardiology clinic.")
    adapter = MagicMock()
    adapter.complete_json.return_value = {
        "date": "2025-03-14",
        "source_file": "",
        "type": "outpatient_letter",
        "summary": "Cardiology outpatient review.",
        "diagnoses": [{"code": "I10", "system": "ICD-10", "label": "Hypertension"}],
        "sections": {"assessment": "BP well controlled."},
    }
    result = ExtractionResult(source=Path("test.pdf"))

    extract_medical_note(doc, adapter, result)

    assert len(result.notes) == 1
    note = result.notes[0]
    assert note.type.value == "outpatient_letter"
    assert note.diagnoses[0].code == "I10"
    assert note.diagnoses[0].citation is None
    adapter.complete_json.assert_called_once()


def test_extract_medical_note_outpatient_diagnosis_citation_populated() -> None:
    """When adapter returns diagnosis citation, it is preserved on the Diagnosis object."""
    doc = _make_doc("Patient has essential hypertension. BP 155/95.")
    adapter = MagicMock()
    adapter.complete_json.return_value = {
        "date": "2025-03-14",
        "source_file": "",
        "type": "outpatient_letter",
        "summary": "Cardiology outpatient review.",
        "diagnoses": [
            {
                "code": "I10",
                "system": "ICD-10",
                "label": "Hypertension",
                "citation": "Patient has essential hypertension.",
            }
        ],
        "sections": {},
    }
    result = ExtractionResult(source=Path("test.pdf"))

    extract_medical_note(doc, adapter, result)

    assert len(result.notes) == 1
    assert result.notes[0].diagnoses[0].citation == "Patient has essential hypertension."


def test_extract_medical_note_outpatient_bad_response_logs_warning(caplog: MagicMock) -> None:
    """Adapter returns unparseable dict → no note appended, no exception raised."""
    doc = _make_doc("Some text.")
    adapter = MagicMock()
    adapter.complete_json.return_value = {"bad": "payload"}  # missing required `date`
    result = ExtractionResult(source=Path("test.pdf"))

    with caplog.at_level(logging.WARNING, logger="cliniq.extraction.prompts.medical_note"):
        extract_medical_note(doc, adapter, result)

    assert result.notes == []
    assert any("parse failed" in r.message for r in caplog.records)


def test_extract_medical_note_discharge_appends_note() -> None:
    """Adapter returns valid discharge summary dict → note appended with discharge_summary type."""
    doc = _make_doc("Discharge summary: Patient admitted with NSTEMI, discharged day 4.")
    adapter = MagicMock()
    adapter.complete_json.return_value = {
        "date": "2025-04-10",
        "source_file": "",
        "type": "discharge_summary",
        "summary": "Patient admitted with NSTEMI, discharged after 4 days.",
        "diagnoses": [{"code": "I21.4", "system": "ICD-10", "label": "NSTEMI"}],
        "sections": {"discharge_plan": "Dual antiplatelet therapy for 12 months."},
    }
    result = ExtractionResult(source=Path("test.pdf"))

    extract_medical_note_discharge(doc, adapter, result)

    assert len(result.notes) == 1
    note = result.notes[0]
    assert note.type.value == "discharge_summary"
    assert note.diagnoses[0].code == "I21.4"
    adapter.complete_json.assert_called_once()


def test_extract_medical_note_discharge_bad_response_logs_warning(caplog: MagicMock) -> None:
    """Adapter returns unparseable dict → no note appended, warning logged."""
    doc = _make_doc("Some discharge text.")
    adapter = MagicMock()
    adapter.complete_json.return_value = {"bad": "payload"}
    result = ExtractionResult(source=Path("test.pdf"))

    with caplog.at_level(logging.WARNING, logger="cliniq.extraction.prompts.medical_note"):
        extract_medical_note_discharge(doc, adapter, result)

    assert result.notes == []
    assert any("parse failed" in r.message for r in caplog.records)


def test_extract_medical_note_lab_report_appends_note() -> None:
    """Adapter returns valid lab report dict → note appended with lab_report type."""
    doc = _make_doc("Full blood count: Hb 9.2 g/dL (low). Iron 4 umol/L (low).")
    adapter = MagicMock()
    adapter.complete_json.return_value = {
        "date": "2025-05-01",
        "source_file": "",
        "type": "lab_report",
        "summary": "FBC shows microcytic anaemia consistent with iron deficiency.",
        "diagnoses": [{"code": "D50.9", "system": "ICD-10", "label": "Iron-deficiency anaemia"}],
        "sections": {"results": "Hb 9.2 g/dL\nIron 4 umol/L"},
    }
    result = ExtractionResult(source=Path("test.pdf"))

    extract_medical_note_lab_report(doc, adapter, result)

    assert len(result.notes) == 1
    note = result.notes[0]
    assert note.type.value == "lab_report"
    assert note.diagnoses[0].code == "D50.9"
    adapter.complete_json.assert_called_once()


def test_extract_medical_note_lab_report_bad_response_logs_warning(caplog: MagicMock) -> None:
    """Adapter returns unparseable dict → no note appended, warning logged."""
    doc = _make_doc("Some lab text.")
    adapter = MagicMock()
    adapter.complete_json.return_value = {"bad": "payload"}
    result = ExtractionResult(source=Path("test.pdf"))

    with caplog.at_level(logging.WARNING, logger="cliniq.extraction.prompts.medical_note"):
        extract_medical_note_lab_report(doc, adapter, result)

    assert result.notes == []
    assert any("parse failed" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Medication
# ---------------------------------------------------------------------------


def test_extract_medications_appends_items() -> None:
    """Adapter returns valid medication list → all items appended to result."""
    doc = _make_doc("Amlodipine 5 mg once daily. Ramipril 10 mg once daily.")
    adapter = MagicMock()
    adapter.complete_json.return_value = [
        {"name": "Amlodipine", "dose": "5 mg", "frequency": "once daily"},
        {"name": "Ramipril", "dose": "10 mg", "frequency": "once daily"},
    ]
    result = ExtractionResult(source=Path("test.pdf"))

    extract_medications(doc, adapter, result)

    assert len(result.medications) == 2
    assert result.medications[0].name == "Amlodipine"
    assert result.medications[1].name == "Ramipril"
    adapter.complete_json.assert_called_once()


def test_extract_medications_citation_populated() -> None:
    """When adapter returns citation text, it is preserved on the Medication object."""
    doc = _make_doc("Start Amlodipine 5 mg once daily for hypertension management.")
    adapter = MagicMock()
    adapter.complete_json.return_value = [
        {
            "name": "Amlodipine",
            "dose": "5 mg",
            "frequency": "once daily",
            "citation": "Start Amlodipine 5 mg once daily for hypertension management.",
        }
    ]
    result = ExtractionResult(source=Path("test.pdf"))

    extract_medications(doc, adapter, result)

    expected_citation = "Start Amlodipine 5 mg once daily for hypertension management."
    assert len(result.medications) == 1
    assert result.medications[0].citation == expected_citation


def test_extract_medications_bad_response_logs_warning(caplog: MagicMock) -> None:
    """Adapter returns non-list → no items appended, warning logged."""
    doc = _make_doc("Some medication text.")
    adapter = MagicMock()
    adapter.complete_json.return_value = {"bad": "payload"}
    result = ExtractionResult(source=Path("test.pdf"))

    with caplog.at_level(logging.WARNING, logger="cliniq.extraction.prompts.medication"):
        extract_medications(doc, adapter, result)

    assert result.medications == []
    assert any("parse failed" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Contact
# ---------------------------------------------------------------------------


def test_extract_contacts_appends_items() -> None:
    """Adapter returns valid contact list → all items appended to result."""
    doc = _make_doc("Royal Free Hospital Cardiology Clinic, Pond Street, London NW3 2QG.")
    adapter = MagicMock()
    adapter.complete_json.return_value = [
        {"name": "Royal Free Hospital", "speciality": "Cardiology", "is_clinic": True},
    ]
    result = ExtractionResult(source=Path("test.pdf"))

    extract_contacts(doc, adapter, result)

    assert len(result.contacts) == 1
    assert result.contacts[0].name == "Royal Free Hospital"
    assert result.contacts[0].is_clinic is True
    adapter.complete_json.assert_called_once()


def test_extract_contacts_bad_response_logs_warning(caplog: MagicMock) -> None:
    """Adapter returns non-list → no items appended, warning logged."""
    doc = _make_doc("Some contact text.")
    adapter = MagicMock()
    adapter.complete_json.return_value = {"bad": "payload"}
    result = ExtractionResult(source=Path("test.pdf"))

    with caplog.at_level(logging.WARNING, logger="cliniq.extraction.prompts.contact"):
        extract_contacts(doc, adapter, result)

    assert result.contacts == []
    assert any("parse failed" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Appointment
# ---------------------------------------------------------------------------


def test_extract_appointments_appends_items() -> None:
    """Adapter returns valid appointment list → all items appended to result."""
    doc = _make_doc("Please attend cardiology outpatients on 12 June 2025 for BP review.")
    adapter = MagicMock()
    adapter.complete_json.return_value = [
        {"date": "2025-06-12", "reason": "BP review", "status": "upcoming"},
    ]
    result = ExtractionResult(source=Path("test.pdf"))

    extract_appointments(doc, adapter, result)

    assert len(result.appointments) == 1
    assert str(result.appointments[0].date) == "2025-06-12"
    assert result.appointments[0].status.value == "upcoming"
    adapter.complete_json.assert_called_once()


def test_extract_appointments_bad_response_logs_warning(caplog: MagicMock) -> None:
    """Adapter returns non-list → no items appended, warning logged."""
    doc = _make_doc("Some appointment text.")
    adapter = MagicMock()
    adapter.complete_json.return_value = {"bad": "payload"}
    result = ExtractionResult(source=Path("test.pdf"))

    with caplog.at_level(logging.WARNING, logger="cliniq.extraction.prompts.appointment"):
        extract_appointments(doc, adapter, result)

    assert result.appointments == []
    assert any("parse failed" in r.message for r in caplog.records)


def test_extract_appointments_skips_invalid_item(caplog: MagicMock) -> None:
    """List with one valid + one invalid item → valid kept, invalid skipped, warning logged."""
    doc = _make_doc("Appointments on 12 June 2025 and some bad data.")
    adapter = MagicMock()
    adapter.complete_json.return_value = [
        {"date": "2025-06-12", "reason": "BP review", "status": "upcoming"},
        {"date": "not-a-date", "status": "invalid_status"},
    ]
    result = ExtractionResult(source=Path("test.pdf"))

    with caplog.at_level(logging.WARNING, logger="cliniq.extraction.prompts.appointment"):
        extract_appointments(doc, adapter, result)

    assert len(result.appointments) == 1
    assert str(result.appointments[0].date) == "2025-06-12"
    assert any("skipping item" in r.message for r in caplog.records)


def test_extract_contacts_skips_invalid_item(caplog: MagicMock) -> None:
    """List with one valid + one invalid item → valid kept, invalid skipped, warning logged."""
    doc = _make_doc("Royal Free Hospital and some bad data.")
    adapter = MagicMock()
    adapter.complete_json.return_value = [
        {"name": "Royal Free Hospital", "is_clinic": True},
        {"is_clinic": "not-a-bool-field-that-breaks-schema", "name": 12345},
    ]
    result = ExtractionResult(source=Path("test.pdf"))

    with caplog.at_level(logging.WARNING, logger="cliniq.extraction.prompts.contact"):
        extract_contacts(doc, adapter, result)

    assert len(result.contacts) == 1
    assert result.contacts[0].name == "Royal Free Hospital"
    assert any("skipping item" in r.message for r in caplog.records)


def test_extract_medications_skips_invalid_item(caplog: MagicMock) -> None:
    """List with one valid + one invalid item → valid kept, invalid skipped, warning logged."""
    doc = _make_doc("Amlodipine 5 mg once daily. And some corrupted entry.")
    adapter = MagicMock()
    adapter.complete_json.return_value = [
        {"name": "Amlodipine", "dose": "5 mg", "frequency": "once daily"},
        {"dose": 99999, "frequency": None, "extra_unknown_required": True},
    ]
    result = ExtractionResult(source=Path("test.pdf"))

    with caplog.at_level(logging.WARNING, logger="cliniq.extraction.prompts.medication"):
        extract_medications(doc, adapter, result)

    assert len(result.medications) == 1
    assert result.medications[0].name == "Amlodipine"
    assert any("skipping item" in r.message for r in caplog.records)
