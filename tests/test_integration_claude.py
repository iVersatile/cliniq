"""Integration tests: all extraction prompts against the real Claude API.

Skipped automatically when ANTHROPIC_API_KEY is absent.
Run with: ANTHROPIC_API_KEY=sk-... pytest -m integration
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from cliniq.adapters.claude import ClaudeAdapter
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

_SKIP = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)

_FIXTURE_DIR = Path(__file__).parent / "fixtures"

# Short synthetic clinical texts — no real patient data
_OUTPATIENT_TEXT = (
    "Dear Dr Jones,\n"
    "Thank you for referring Mr [PATIENT] (DOB: [DOB]) to cardiology clinic.\n"
    "He was seen on 14 March 2025. Blood pressure was 142/88 mmHg.\n"
    "Impression: Hypertension (ICD-10 I10), well controlled on Amlodipine 5 mg once daily.\n"
    "Please arrange a follow-up appointment on 12 June 2025.\n"
    "Yours sincerely, Dr Smith, Consultant Cardiologist.\n"
    "Royal Free Hospital, Pond Street, London NW3 2QG. Tel: 020 7794 0500."
)

_DISCHARGE_TEXT = (
    "DISCHARGE SUMMARY\n"
    "Patient admitted with NSTEMI on 10 April 2025.\n"
    "Primary diagnosis: NSTEMI (ICD-10 I21.4).\n"
    "Treatment: PCI performed. Discharged on dual antiplatelet therapy: "
    "Aspirin 75 mg once daily + Ticagrelor 90 mg twice daily.\n"
    "Discharge date: 14 April 2025.\n"
    "Follow-up: Cardiology outpatients in 6 weeks."
)

_LAB_TEXT = (
    "HAEMATOLOGY REPORT — dated 1 May 2025\n"
    "Full Blood Count:\n"
    "  Haemoglobin: 9.2 g/dL (low; ref 13.5-17.5)\n"
    "  MCV: 72 fL (low; ref 80-100)\n"
    "  Ferritin: 4 ng/mL (low; ref 12-300)\n"
    "Interpretation: Microcytic anaemia consistent with iron deficiency (ICD-10 D50.9)."
)


def _make_doc(text: str, source: str = "test.pdf") -> DocumentText:
    return DocumentText(
        source_file=Path(source),
        pages=[PageText(page_number=1, text=text, via_ocr=False)],
    )


@pytest.fixture(scope="module")
def adapter() -> ClaudeAdapter:
    pytest.importorskip("anthropic", reason="anthropic package not installed")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")
    return ClaudeAdapter()


@pytest.mark.integration
@_SKIP
def test_extract_medical_note_outpatient(adapter: ClaudeAdapter) -> None:
    doc = _make_doc(_OUTPATIENT_TEXT)
    result = ExtractionResult(source=Path("test.pdf"))
    extract_medical_note(doc, adapter, result)
    assert len(result.notes) == 1
    note = result.notes[0]
    assert note.summary
    assert note.date is not None


@pytest.mark.integration
@_SKIP
def test_extract_medical_note_discharge(adapter: ClaudeAdapter) -> None:
    doc = _make_doc(_DISCHARGE_TEXT)
    result = ExtractionResult(source=Path("test.pdf"))
    extract_medical_note_discharge(doc, adapter, result)
    assert len(result.notes) == 1
    note = result.notes[0]
    assert note.type.value == "discharge_summary"
    assert note.date is not None


@pytest.mark.integration
@_SKIP
def test_extract_medical_note_lab_report(adapter: ClaudeAdapter) -> None:
    doc = _make_doc(_LAB_TEXT)
    result = ExtractionResult(source=Path("test.pdf"))
    extract_medical_note_lab_report(doc, adapter, result)
    assert len(result.notes) == 1
    note = result.notes[0]
    assert note.type.value == "lab_report"


@pytest.mark.integration
@_SKIP
def test_extract_medications(adapter: ClaudeAdapter) -> None:
    doc = _make_doc(_OUTPATIENT_TEXT)
    result = ExtractionResult(source=Path("test.pdf"))
    extract_medications(doc, adapter, result)
    assert len(result.medications) >= 1
    names = [m.name.lower() for m in result.medications]
    assert any("amlodipine" in n for n in names)


@pytest.mark.integration
@_SKIP
def test_extract_contacts(adapter: ClaudeAdapter) -> None:
    doc = _make_doc(_OUTPATIENT_TEXT)
    result = ExtractionResult(source=Path("test.pdf"))
    extract_contacts(doc, adapter, result)
    assert len(result.contacts) >= 1


@pytest.mark.integration
@_SKIP
def test_extract_appointments(adapter: ClaudeAdapter) -> None:
    doc = _make_doc(_OUTPATIENT_TEXT)
    result = ExtractionResult(source=Path("test.pdf"))
    extract_appointments(doc, adapter, result)
    assert len(result.appointments) >= 1
    statuses = {a.status.value for a in result.appointments}
    assert "upcoming" in statuses


@pytest.mark.integration
@_SKIP
def test_extract_all_from_fixture_referral(adapter: ClaudeAdapter) -> None:
    """Smoke test: full extraction pipeline on the lister referral fixture PDF."""
    from cliniq.extraction.engine import extract_document
    from cliniq.ingestion.pdf_reader import read_pdf

    pdf = _FIXTURE_DIR / "lister_referral_001_mock.pdf"
    if not pdf.exists():
        pytest.skip("fixture PDF not found")

    doc = read_pdf(pdf)
    result = extract_document(doc, adapter)
    assert result is not None
