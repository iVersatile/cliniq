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
- `diagnoses`: array of {code, system, label, citation}. Use ICD-10 codes where determinable; \
otherwise set system to "other" and leave code as a short descriptor. \
`citation`: verbatim source clause stating this diagnosis, otherwise null.
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


_SYSTEM_DISCHARGE = """\
You are a clinical record parser specialising in hospital discharge summaries.
Extract structured data from the document below and return a single JSON object.

Rules:
- Return JSON only — no prose, no markdown fences.
- Never hallucinate. If a field is absent from the text, use null or omit it.
- `type` must be "discharge_summary".
- `diagnoses`: array of {code, system, label, citation}. List primary diagnosis first, then \
secondary. Use ICD-10 codes where determinable; otherwise set system to "other". \
`citation`: verbatim source clause stating this diagnosis, otherwise null.
- `sections`: object mapping section headings (lower_snake_case) to their text content.
  Common headings: presenting_complaint, past_medical_history, investigations,
  procedures, discharge_medications, discharge_plan, follow_up.
- `summary`: one sentence capturing the primary reason for admission and outcome.
- `date`: ISO 8601 discharge date (YYYY-MM-DD), if present.
- `source_file`: leave as empty string — caller will populate.
"""


def extract_medical_note_discharge(
    doc: DocumentText,
    adapter: LLMAdapter,
    result: ExtractionResult,
) -> None:
    schema = MedicalNote.model_json_schema()
    try:
        raw = adapter.complete_json(
            system=_SYSTEM_DISCHARGE,
            user=doc.full_text,
            schema=schema,
        )
        raw.setdefault("source_file", str(doc.source_file))
        raw["type"] = NoteType.DISCHARGE_SUMMARY
        note = MedicalNote.model_validate(raw)
        result.notes.append(note)
    except (ValidationError, ValueError, KeyError) as exc:
        log.warning("extract_medical_note_discharge: parse failed (%s)", exc)


_SYSTEM_LAB_REPORT = """\
You are a clinical record parser specialising in laboratory reports.
Extract structured data from the report below and return a single JSON object.

Rules:
- Return JSON only — no prose, no markdown fences.
- Never hallucinate. If a field is absent from the text, use null or omit it.
- `type` must be "lab_report".
- `diagnoses`: array of {code, system, label, citation}. Only populate when the report explicitly \
states a diagnosis or interpretation (e.g. "consistent with iron-deficiency anaemia"). \
Use ICD-10 codes where determinable; otherwise system = "other". \
`citation`: verbatim source clause stating this diagnosis, otherwise null.
- `sections`: object mapping section headings (lower_snake_case) to their text content.
  Common headings: specimen, requested_by, results, reference_ranges, interpretation, comment.
  Preserve result tables as plain text in the relevant section.
- `summary`: one sentence naming the test panel and the headline finding (e.g. normal / \
abnormal / critical value present).
- `date`: ISO 8601 collection or report date (YYYY-MM-DD), if present.
- `source_file`: leave as empty string — caller will populate.
"""


def extract_medical_note_lab_report(
    doc: DocumentText,
    adapter: LLMAdapter,
    result: ExtractionResult,
) -> None:
    schema = MedicalNote.model_json_schema()
    try:
        raw = adapter.complete_json(
            system=_SYSTEM_LAB_REPORT,
            user=doc.full_text,
            schema=schema,
        )
        raw.setdefault("source_file", str(doc.source_file))
        raw["type"] = NoteType.LAB_REPORT
        note = MedicalNote.model_validate(raw)
        result.notes.append(note)
    except (ValidationError, ValueError, KeyError) as exc:
        log.warning("extract_medical_note_lab_report: parse failed (%s)", exc)


def extract_medical_note(
    doc: DocumentText,
    adapter: LLMAdapter,
    result: ExtractionResult,
) -> None:
    extract_medical_note_outpatient(doc, adapter, result)
