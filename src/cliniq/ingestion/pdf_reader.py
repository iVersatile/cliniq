"""Two-tier PDF reader: pdfplumber text-layer → pytesseract fallback."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber


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
    doc = DocumentText(source_file=path)
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                doc.pages.append(PageText(page_number=i, text=text, via_ocr=False))
            else:
                from cliniq.ingestion.ocr import ocr_page

                doc.pages.append(ocr_page(page, page_number=i))
    return doc
