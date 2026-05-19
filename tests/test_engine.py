"""Tests for the ExtractionEngine orchestration layer."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from cliniq.extraction.engine import ExtractionEngine, ExtractionResult
from cliniq.ingestion.pdf_reader import DocumentText, PageText


def _stub_doc(path: Path) -> DocumentText:
    doc = DocumentText(source_file=path)
    doc.pages.append(PageText(page_number=1, text="Patient: John Smith", via_ocr=False))
    return doc


def test_extraction_engine_returns_result(tmp_path: Path) -> None:
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    adapter = MagicMock()
    # read_pdf is a top-level import in engine.py; extract_all is a lazy import
    with patch("cliniq.extraction.engine.read_pdf", return_value=_stub_doc(pdf)):
        with patch("cliniq.extraction.prompts.extract_all") as mock_extract:
            engine = ExtractionEngine(adapter=adapter)
            result = engine.process(pdf)

    assert isinstance(result, ExtractionResult)
    assert result.source == pdf
    mock_extract.assert_called_once()


def test_extraction_result_write_calls_writers(tmp_path: Path) -> None:
    result = ExtractionResult(source=tmp_path / "doc.pdf")
    # write_result and write_markdown are lazy imports inside ExtractionResult.write()
    with patch("cliniq.output.json_writer.write_result") as mock_json:
        with patch("cliniq.output.markdown_writer.write_markdown") as mock_md:
            result.write(tmp_path)
    mock_json.assert_called_once_with(result, tmp_path)
    mock_md.assert_called_once_with(result, tmp_path)


def test_extraction_result_empty_lists(tmp_path: Path) -> None:
    result = ExtractionResult(source=tmp_path / "x.pdf")
    assert result.notes == []
    assert result.contacts == []
    assert result.medications == []
    assert result.appointments == []
    assert result.symptoms == []
