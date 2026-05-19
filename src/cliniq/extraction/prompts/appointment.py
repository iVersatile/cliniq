from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic import ValidationError

from cliniq.adapters.base import LLMAdapter
from cliniq.ingestion.pdf_reader import DocumentText
from cliniq.schemas.appointment import Appointment

if TYPE_CHECKING:
    from cliniq.extraction.engine import ExtractionResult

log = logging.getLogger(__name__)

_SYSTEM = """\
You are a clinical record parser specialising in appointment extraction.
Extract every appointment (past and future) mentioned in the clinical text and return \
a JSON array of objects.

Rules:
- Return a JSON array only — no prose, no markdown fences.
- Each element must be an appointment object.
- Never hallucinate. If a field is absent from the text, use null or omit it.
- `date`: ISO 8601 date (YYYY-MM-DD) of the appointment.
- `reason`: brief description of the purpose (e.g. "blood pressure review", "post-op follow-up").
- `status`: one of "past", "upcoming", or "cancelled".
  Infer from context: appointments described as future or with "please attend" are "upcoming";
  appointments described as having occurred are "past"; explicitly cancelled ones are "cancelled".
- Do not invent appointments; only extract those explicitly mentioned in the text.
"""


def extract_appointments(
    doc: DocumentText,
    adapter: LLMAdapter,
    result: ExtractionResult,
) -> None:
    schema = {"type": "array", "items": Appointment.model_json_schema()}
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
                appt = Appointment.model_validate(item)
                result.appointments.append(appt)
            except ValidationError as exc:
                log.warning("extract_appointments: skipping item — parse failed (%s)", exc)
    except (ValueError, KeyError) as exc:
        log.warning("extract_appointments: parse failed (%s)", exc)
