"""pytesseract OCR fallback for image-only PDF pages."""

from __future__ import annotations

import logging

import pytesseract  # type: ignore[import-untyped]
from PIL import Image

from cliniq.ingestion.pdf_reader import PageText

log = logging.getLogger(__name__)

_HANDWRITING_MARKER = "[HANDWRITTEN — review manually]"
_LOW_CONF_THRESHOLD = 60


def ocr_page(page: object, page_number: int) -> PageText:
    """Render a pdfplumber page to image and run Tesseract OCR."""
    from cliniq.ingestion.preprocessing import preprocess_image

    raw: Image.Image = page.to_image(resolution=300).original  # type: ignore[attr-defined]
    img = preprocess_image(raw)
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

    confidences = [int(c) for c in data["conf"] if str(c).lstrip("-").isdigit() and int(c) >= 0]
    avg_conf = sum(confidences) / len(confidences) if confidences else 0
    text = pytesseract.image_to_string(img).strip()
    low_conf = avg_conf < _LOW_CONF_THRESHOLD

    log.debug(
        "ocr_page: p%d avg_conf=%.1f low_confidence=%s is_handwritten=%s",
        page_number,
        avg_conf,
        low_conf,
        not text.strip(),
    )
    if low_conf:
        log.warning(
            "ocr_page: p%d low OCR confidence (%.1f < %d)",
            page_number,
            avg_conf,
            _LOW_CONF_THRESHOLD,
        )

    return PageText(
        page_number=page_number,
        text=text or _HANDWRITING_MARKER,
        via_ocr=True,
        low_confidence=low_conf,
        is_handwritten=not text.strip(),
    )
