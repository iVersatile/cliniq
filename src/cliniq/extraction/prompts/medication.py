from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic import ValidationError

from cliniq.adapters.base import LLMAdapter
from cliniq.ingestion.pdf_reader import DocumentText
from cliniq.schemas.medication import Medication

if TYPE_CHECKING:
    from cliniq.extraction.engine import ExtractionResult

log = logging.getLogger(__name__)

_SYSTEM = """\
You are a clinical record parser specialising in medication extraction.
Extract every medication mentioned in the clinical text and return a JSON array of objects.

Rules:
- Return a JSON array only — no prose, no markdown fences.
- Each element must be a medication object.
- Never hallucinate. If a field is absent from the text, use null or omit it.
- `name`: drug name as written (generic preferred; include brand name in parentheses if present).
- `dose`: dose string exactly as written (e.g. "5 mg", "10 mg/5 mL").
- `frequency`: frequency string exactly as written (e.g. "once daily", "BD", "PRN").
- `start_date`: ISO 8601 date if an initiation date is explicitly stated, otherwise null.
- `end_date`: ISO 8601 date if a stop date or duration end is explicitly stated, otherwise null.
- `citation`: verbatim sentence from the source text mentioning this medication, otherwise null.
- Include medications that were started, continued, changed, or stopped during the encounter.
- Do not include medications mentioned only as allergies or remote past history.
"""


def extract_medications(
    doc: DocumentText,
    adapter: LLMAdapter,
    result: ExtractionResult,
) -> None:
    schema = {"type": "array", "items": Medication.model_json_schema()}
    try:
        raw = adapter.complete_json(
            system=_SYSTEM,
            user=doc.full_text,
            schema=schema,
        )
        if not isinstance(raw, list):
            raise ValueError(f"expected list, got {type(raw).__name__}")
        for item in raw:
            try:
                result.medications.append(Medication.model_validate(item))
            except ValidationError as exc:
                log.warning("extract_medications: skipping item — parse failed (%s)", exc)
    except (ValueError, KeyError) as exc:
        log.warning("extract_medications: parse failed (%s)", exc)
