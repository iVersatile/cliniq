"""Tests for extraction prompts."""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock

from cliniq.extraction.engine import ExtractionResult
from cliniq.extraction.prompts import extract_all
from cliniq.extraction.prompts.appointment import extract_appointments
from cliniq.extraction.prompts.contact import extract_contacts
from cliniq.extraction.prompts.medical_note import extract_medical_note
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
    adapter.complete_json.assert_called_once()


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
