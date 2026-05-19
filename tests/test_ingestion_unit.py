"""Unit tests for pdf_reader and ocr modules using mocks."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from cliniq.ingestion.pdf_reader import DocumentText, PageText, read_pdf


def _make_pdfplumber_page(text: str) -> MagicMock:
    page = MagicMock()
    page.extract_text.return_value = text if text else None
    return page


def _mock_pdf(pages: list[MagicMock]) -> MagicMock:
    pdf = MagicMock()
    pdf.__enter__ = MagicMock(return_value=pdf)
    pdf.__exit__ = MagicMock(return_value=False)
    pdf.pages = pages
    return pdf


def test_read_pdf_text_layer(tmp_path: Path) -> None:
    pdf_path = tmp_path / "born_digital.pdf"
    pdf_path.write_bytes(b"%PDF")

    pages = [_make_pdfplumber_page("Discharge summary text")]
    with patch("cliniq.ingestion.pdf_reader.pdfplumber.open", return_value=_mock_pdf(pages)):
        doc = read_pdf(pdf_path)

    assert len(doc.pages) == 1
    assert doc.pages[0].via_ocr is False
    assert "Discharge summary" in doc.pages[0].text


def test_read_pdf_ocr_fallback(tmp_path: Path) -> None:
    pdf_path = tmp_path / "scanned.pdf"
    pdf_path.write_bytes(b"%PDF")

    pages = [_make_pdfplumber_page("")]  # no text layer
    ocr_result = PageText(page_number=1, text="OCR extracted text", via_ocr=True)

    with patch("cliniq.ingestion.pdf_reader.pdfplumber.open", return_value=_mock_pdf(pages)):
        with patch("cliniq.ingestion.ocr.ocr_page", return_value=ocr_result):
            doc = read_pdf(pdf_path)

    assert len(doc.pages) == 1
    assert doc.pages[0].via_ocr is True


def test_document_text_full_text_property(tmp_path: Path) -> None:
    doc = DocumentText(source_file=tmp_path / "x.pdf")
    doc.pages = [
        PageText(page_number=1, text="Page one", via_ocr=False),
        PageText(page_number=2, text="Page two", via_ocr=False),
    ]
    assert doc.full_text == "Page one\n\nPage two"


def test_read_pdf_multiple_pages(tmp_path: Path) -> None:
    pdf_path = tmp_path / "multi.pdf"
    pdf_path.write_bytes(b"%PDF")

    pages = [
        _make_pdfplumber_page("Page 1 text"),
        _make_pdfplumber_page("Page 2 text"),
        _make_pdfplumber_page("Page 3 text"),
    ]
    with patch("cliniq.ingestion.pdf_reader.pdfplumber.open", return_value=_mock_pdf(pages)):
        doc = read_pdf(pdf_path)

    assert len(doc.pages) == 3
    assert all(not p.via_ocr for p in doc.pages)


def test_page_text_defaults() -> None:
    p = PageText(page_number=1, text="hello", via_ocr=False)
    assert p.low_confidence is False
    assert p.is_handwritten is False
