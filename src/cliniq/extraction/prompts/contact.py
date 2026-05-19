from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic import ValidationError

from cliniq.adapters.base import LLMAdapter
from cliniq.ingestion.pdf_reader import DocumentText
from cliniq.schemas.contact import Contact

if TYPE_CHECKING:
    from cliniq.extraction.engine import ExtractionResult

log = logging.getLogger(__name__)

_SYSTEM = """\
You are a clinical record parser specialising in contact extraction.
Extract every clinic and clinician contact mentioned in the clinical text and return \
a JSON array of objects.

Rules:
- Return a JSON array only — no prose, no markdown fences.
- Each element must be a contact object.
- Never hallucinate. If a field is absent from the text, use null or omit it.
- `name`: full name of the clinic or clinician.
- `address`: full postal address if present, otherwise omit.
- `phone`: phone or fax number if present, otherwise omit.
- `speciality`: medical speciality (e.g. "Cardiology", "Nephrology") if determinable.
- `is_clinic`: true if the contact is an institution or clinic; false if an individual clinician.
- Extract both the sending and receiving parties when both appear in the document.
"""


def extract_contacts(
    doc: DocumentText,
    adapter: LLMAdapter,
    result: ExtractionResult,
) -> None:
    schema = {"type": "array", "items": Contact.model_json_schema()}
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
                result.contacts.append(Contact.model_validate(item))
            except ValidationError as exc:
                log.warning("extract_contacts: skipping item — parse failed (%s)", exc)
    except (ValueError, KeyError) as exc:
        log.warning("extract_contacts: parse failed (%s)", exc)
