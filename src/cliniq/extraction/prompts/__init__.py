from __future__ import annotations

from typing import TYPE_CHECKING

from cliniq.adapters.base import LLMAdapter
from cliniq.extraction.prompts.appointment import extract_appointments
from cliniq.extraction.prompts.contact import extract_contacts
from cliniq.extraction.prompts.medical_note import (
    classify_note_type,
    extract_medical_note_discharge,
    extract_medical_note_lab_report,
    extract_outpatient_note,
)
from cliniq.extraction.prompts.medication import extract_medications
from cliniq.ingestion.pdf_reader import DocumentText
from cliniq.schemas.medical_note import NoteType

if TYPE_CHECKING:
    from cliniq.extraction.engine import ExtractionResult

_NOTE_EXTRACTORS = {
    NoteType.OUTPATIENT_LETTER: extract_outpatient_note,
    NoteType.DISCHARGE_SUMMARY: extract_medical_note_discharge,
    NoteType.LAB_REPORT: extract_medical_note_lab_report,
}


def extract_all(
    doc: DocumentText,
    adapter: LLMAdapter,
    result: ExtractionResult,
) -> None:
    extract_contacts(doc, adapter, result)
    extract_medications(doc, adapter, result)
    extract_appointments(doc, adapter, result)
    note_type = classify_note_type(doc.full_text)
    extractor = _NOTE_EXTRACTORS.get(note_type, extract_outpatient_note)
    extractor(doc, adapter, result)
