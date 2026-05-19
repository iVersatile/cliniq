from __future__ import annotations

from typing import TYPE_CHECKING

from cliniq.adapters.base import LLMAdapter
from cliniq.extraction.prompts.appointment import extract_appointments
from cliniq.extraction.prompts.contact import extract_contacts
from cliniq.extraction.prompts.medical_note import extract_outpatient_note
from cliniq.extraction.prompts.medication import extract_medications
from cliniq.ingestion.pdf_reader import DocumentText

if TYPE_CHECKING:
    from cliniq.extraction.engine import ExtractionResult


def extract_all(
    doc: DocumentText,
    adapter: LLMAdapter,
    result: ExtractionResult,
) -> None:
    extract_contacts(doc, adapter, result)
    extract_medications(doc, adapter, result)
    extract_appointments(doc, adapter, result)
    extract_outpatient_note(doc, adapter, result)
