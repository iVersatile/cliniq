from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic import ValidationError

from cliniq.adapters.base import LLMAdapter
from cliniq.ingestion.pdf_reader import DocumentText
from cliniq.schemas.medical_note import MedicalNote, NoteType

if TYPE_CHECKING:
    from cliniq.extraction.engine import ExtractionResult

log = logging.getLogger(__name__)

_SYSTEM_OUTPATIENT = """\
You are a clinical record parser specialising in outpatient correspondence.
Extract structured data from the letter below and return a single JSON object.

Rules:
- Return JSON only — no prose, no markdown fences.
- Never hallucinate. If a field is absent from the text, use null or omit it.
- `type` must be "outpatient_letter".
- `diagnoses`: array of {code, system, label}. Use ICD-10 codes where determinable; \
otherwise set system to "other" and leave code as a short descriptor.
- `sections`: object mapping section headings (lower_snake_case) to their text content.
  Common headings: history, examination, investigations, assessment, plan, follow_up.
- `summary`: one sentence capturing the clinical purpose of the letter.
- `date`: ISO 8601 date (YYYY-MM-DD) of the letter, if present.
- `source_file`: leave as empty string — caller will populate.
"""


def extract_medical_note_outpatient(
    doc: DocumentText,
    adapter: LLMAdapter,
    result: ExtractionResult,
) -> None:
    schema = MedicalNote.model_json_schema()
    try:
        raw = adapter.complete_json(
            system=_SYSTEM_OUTPATIENT,
            user=doc.full_text,
            schema=schema,
        )
        raw.setdefault("source_file", str(doc.source_file))
        raw["type"] = NoteType.OUTPATIENT_LETTER
        note = MedicalNote.model_validate(raw)
        result.notes.append(note)
    except (ValidationError, ValueError, KeyError) as exc:
        log.warning("extract_medical_note_outpatient: parse failed (%s)", exc)


def extract_medical_note(
    doc: DocumentText,
    adapter: LLMAdapter,
    result: ExtractionResult,
) -> None:
    extract_medical_note_outpatient(doc, adapter, result)
