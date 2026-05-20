from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic import ValidationError

from cliniq.adapters.base import LLMAdapter
from cliniq.ingestion.pdf_reader import DocumentText
from cliniq.schemas.condition import Condition

if TYPE_CHECKING:
    from cliniq.extraction.engine import ExtractionResult

log = logging.getLogger(__name__)

_SYSTEM = """\
You are a clinical record parser specialising in medical condition extraction.
Extract every medical condition mentioned in the clinical text and return a JSON array of objects.

Rules:
- Return a JSON array only — no prose, no markdown fences.
- Each element must be a condition object.
- Never hallucinate. If a field is absent from the text, use null or omit it.
- `name`: condition name as written (use standard clinical terminology where clear).
- `body_site`: anatomical site or system if stated (e.g. "biliary", "cardiovascular"),
  otherwise null.
- `status`: one of "active", "monitoring", "resolved", "unknown".
  Use "active" for ongoing conditions under treatment or causing symptoms.
  Use "monitoring" for stable conditions kept under review.
  Use "resolved" for conditions explicitly stated as cured or no longer present.
  Use "unknown" when status is not determinable.
- `diagnosed_date`: ISO 8601 date (YYYY-MM-DD) when the condition was first diagnosed, if stated.
- `last_review_date`: ISO 8601 date of the most recent clinical review of this condition, if stated.
- `history`: array of timeline events. Each event:
    - `event_date`: ISO 8601 date (YYYY-MM-DD) of the event, if stated.
    - `measurement`: objective finding, test result, or measurement at that time, if present.
    - `notes`: clinician notes or narrative for this event, if present.
  Include at minimum one history entry per condition if any event data is available.
- `citation`: verbatim sentence from the source text first mentioning this condition,
  otherwise null.
- Include active, monitoring, and resolved conditions.
- Do not invent conditions not explicitly stated in the text.
"""


def extract_conditions(
    doc: DocumentText,
    adapter: LLMAdapter,
    result: ExtractionResult,
) -> None:
    schema = {"type": "array", "items": Condition.model_json_schema()}
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
                result.conditions.append(Condition.model_validate(item))
            except ValidationError as exc:
                log.warning("extract_conditions: skipping item — parse failed (%s)", exc)
    except (ValueError, KeyError) as exc:
        log.warning("extract_conditions: parse failed (%s)", exc)
