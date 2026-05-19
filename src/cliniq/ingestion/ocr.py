"""pytesseract OCR fallback for image-only PDF pages."""

from __future__ import annotations

import logging

import pytesseract  # type: ignore[import-untyped]
from pdfplumber.page import Page
from PIL import Image

from cliniq.ingestion.pdf_reader import PageText

log = logging.getLogger(__name__)

_HANDWRITING_MARKER = "[HANDWRITTEN — review manually]"

# Tesseract reports per-word confidence 0–100.  Empirically, scanned clinical
# documents with good scan quality score 70–95; degraded scans or mixed
# handwriting fall below 60.  60 is conservative enough to flag borderline pages
# without excessive false positives on typical NHS correspondence.
_LOW_CONF_THRESHOLD = 60


def _parse_confidences(raw: list[str | int]) -> list[int]:
    """Return non-negative integer confidences from a pytesseract conf column."""
    result = []
    for val in raw:
        try:
            c = int(val)
        except (ValueError, TypeError):
            continue
        if c >= 0:
            result.append(c)
    return result


def ocr_page(page: Page, page_number: int) -> PageText:
    """Render a pdfplumber page to image and run Tesseract OCR."""
    from cliniq.ingestion.preprocessing import preprocess_image

    try:
        raw: Image.Image = page.to_image(resolution=300).original
        img = preprocess_image(raw)
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        confidences = _parse_confidences(data["conf"])
        avg_conf = sum(confidences) / len(confidences) if confidences else 0
        text = pytesseract.image_to_string(img).strip()
    except Exception as exc:
        log.error("ocr_page: p%d OCR failed (%s: %s)", page_number, type(exc).__name__, exc)
        return PageText(
            page_number=page_number,
            text=_HANDWRITING_MARKER,
            via_ocr=True,
            low_confidence=True,
            is_handwritten=True,
        )

    low_conf = avg_conf < _LOW_CONF_THRESHOLD
    is_handwritten = not text

    log.debug(
        "ocr_page: p%d avg_conf=%.1f low_confidence=%s is_handwritten=%s",
        page_number,
        avg_conf,
        low_conf,
        is_handwritten,
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
        is_handwritten=is_handwritten,
    )
