"""Two-tier PDF reader: pdfplumber text-layer → pytesseract fallback."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber

log = logging.getLogger(__name__)


@dataclass
class PageText:
    page_number: int
    text: str
    via_ocr: bool
    low_confidence: bool = False
    is_handwritten: bool = False


@dataclass
class DocumentText:
    source_file: Path
    pages: list[PageText] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.text for p in self.pages)


def read_pdf(path: Path) -> DocumentText:
    """Extract text from a PDF, falling back to OCR for image-only pages."""
    log.debug("read_pdf: opening %s", path)
    doc = DocumentText(source_file=path)
    try:
        with pdfplumber.open(path) as pdf:
            total = len(pdf.pages)
            for i, page in enumerate(pdf.pages, start=1):
                try:
                    text = page.extract_text() or ""
                except Exception as exc:
                    log.error(
                        "read_pdf: p%d/%d text extraction failed (%s: %s) — skipping page",
                        i,
                        total,
                        type(exc).__name__,
                        exc,
                    )
                    continue
                if text.strip():
                    log.debug("read_pdf: p%d/%d text-layer (%d chars)", i, total, len(text))
                    doc.pages.append(PageText(page_number=i, text=text, via_ocr=False))
                else:
                    log.debug("read_pdf: p%d/%d no text layer — falling back to OCR", i, total)
                    from cliniq.ingestion.ocr import ocr_page

                    doc.pages.append(ocr_page(page, page_number=i))
    except Exception as exc:
        raise ValueError(f"read_pdf: failed to open or parse '{path}': {exc}") from exc
    log.debug("read_pdf: done — %d pages", len(doc.pages))
    return doc
