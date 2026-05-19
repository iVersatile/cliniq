"""Tests for the ExtractionEngine orchestration layer."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cliniq.extraction.engine import ExtractionEngine, ExtractionResult
from cliniq.extraction.prompts.medical_note import classify_note_type
from cliniq.ingestion.pdf_reader import DocumentText, PageText
from cliniq.schemas.medical_note import NoteType

GOLDEN = Path(__file__).parent / "fixtures" / "golden"


def _stub_doc(path: Path) -> DocumentText:
    doc = DocumentText(source_file=path)
    doc.pages.append(PageText(page_number=1, text="Patient: John Smith", via_ocr=False))
    return doc


def test_extraction_engine_returns_result(tmp_path: Path) -> None:
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    adapter = MagicMock()
    # read_pdf is a top-level import in engine.py; extract_all is a lazy import
    with patch("cliniq.extraction.engine.read_pdf", return_value=_stub_doc(pdf)):
        with patch("cliniq.extraction.prompts.extract_all") as mock_extract:
            engine = ExtractionEngine(adapter=adapter)
            result = engine.process(pdf)

    assert isinstance(result, ExtractionResult)
    assert result.source == pdf
    mock_extract.assert_called_once()


def test_extraction_result_write_calls_writers(tmp_path: Path) -> None:
    result = ExtractionResult(source=tmp_path / "doc.pdf")
    # write_result and write_markdown are lazy imports inside ExtractionResult.write()
    with patch("cliniq.output.json_writer.write_result") as mock_json:
        with patch("cliniq.output.markdown_writer.write_markdown") as mock_md:
            result.write(tmp_path)
    mock_json.assert_called_once_with(result, tmp_path)
    mock_md.assert_called_once_with(result, tmp_path)


def test_extraction_result_empty_lists(tmp_path: Path) -> None:
    result = ExtractionResult(source=tmp_path / "x.pdf")
    assert result.notes == []
    assert result.contacts == []
    assert result.medications == []
    assert result.appointments == []
    assert result.symptoms == []


# ---------------------------------------------------------------------------
# classify_note_type — heuristic routing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("laboratory report specimen reference range", NoteType.LAB_REPORT),
        ("Lab Report: Haematology Panel\nSpecimen collected 2024-01-10", NoteType.LAB_REPORT),
        ("Discharge Summary\nDate of Admission: 2024-01-01", NoteType.DISCHARGE_SUMMARY),
        ("The patient was admitted and discharged home on 2024-01-05", NoteType.DISCHARGE_SUMMARY),
        ("Dear Dr Smith, reviewed in outpatient clinic.", NoteType.OUTPATIENT_LETTER),
        ("", NoteType.OUTPATIENT_LETTER),
    ],
)
def test_classify_note_type(text: str, expected: NoteType) -> None:
    assert classify_note_type(text) == expected


# ---------------------------------------------------------------------------
# ExtractionEngine end-to-end with mock adapter (full prompt → schema chain)
# ---------------------------------------------------------------------------


def _make_doc(text: str, path: Path) -> DocumentText:
    doc = DocumentText(source_file=path)
    doc.pages.append(PageText(page_number=1, text=text, via_ocr=False))
    return doc


def _adapter_for(golden_map: dict[str, object]) -> MagicMock:
    """Return mock adapter whose complete_json returns golden data keyed by schema type."""
    adapter = MagicMock()

    def _side_effect(system: str, user: str, schema: dict) -> object:  # noqa: ARG001
        if "array" in str(schema.get("type", "")):
            item_schema = schema.get("items", {})
            title = item_schema.get("title", "")
        else:
            title = schema.get("title", "")
        return golden_map.get(title, [] if schema.get("type") == "array" else {})

    adapter.complete_json.side_effect = _side_effect
    return adapter


def test_engine_full_chain_outpatient(tmp_path: Path) -> None:
    note_data = json.loads((GOLDEN / "outpatient_note.json").read_text())
    contacts_data = json.loads((GOLDEN / "contacts.json").read_text())
    medications_data = json.loads((GOLDEN / "medications.json").read_text())
    appointments_data = json.loads((GOLDEN / "appointments.json").read_text())

    pdf = tmp_path / "letter.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    doc = _make_doc("Dear Dr Smith, outpatient clinic review.", pdf)

    def _complete_json(system: str, user: str, schema: dict) -> object:  # noqa: ARG001
        title = schema.get("title") or schema.get("items", {}).get("title", "")
        mapping = {
            "MedicalNote": note_data,
            "Contact": contacts_data,
            "Medication": medications_data,
            "Appointment": appointments_data,
        }
        return mapping.get(title, [])

    adapter = MagicMock()
    adapter.complete_json.side_effect = _complete_json

    with patch("cliniq.extraction.engine.read_pdf", return_value=doc):
        engine = ExtractionEngine(adapter=adapter)
        result = engine.process(pdf)

    assert len(result.notes) == 1
    assert result.notes[0].type == NoteType.OUTPATIENT_LETTER
    assert len(result.contacts) == len(contacts_data)
    assert len(result.medications) == len(medications_data)
    assert len(result.appointments) == len(appointments_data)


def test_engine_full_chain_discharge(tmp_path: Path) -> None:
    note_data = json.loads((GOLDEN / "discharge_note.json").read_text())
    pdf = tmp_path / "discharge.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    doc = _make_doc("Discharge Summary\nDate of Admission: 2024-01-01\nDischarged home.", pdf)

    adapter = MagicMock()
    adapter.complete_json.return_value = note_data

    with patch("cliniq.extraction.engine.read_pdf", return_value=doc):
        result = ExtractionEngine(adapter=adapter).process(pdf)

    assert len(result.notes) == 1
    assert result.notes[0].type == NoteType.DISCHARGE_SUMMARY


def test_engine_full_chain_lab_report(tmp_path: Path) -> None:
    note_data = json.loads((GOLDEN / "lab_report_note.json").read_text())
    pdf = tmp_path / "lab.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    doc = _make_doc("Laboratory Report\nSpecimen: Serum\nReference Range: 0-5 U/L", pdf)

    adapter = MagicMock()
    adapter.complete_json.return_value = note_data

    with patch("cliniq.extraction.engine.read_pdf", return_value=doc):
        result = ExtractionEngine(adapter=adapter).process(pdf)

    assert len(result.notes) == 1
    assert result.notes[0].type == NoteType.LAB_REPORT
