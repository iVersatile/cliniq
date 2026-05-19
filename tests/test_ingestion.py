"""Unit tests for the PDF ingestion layer."""

from pathlib import Path

import pytest


def test_read_pdf_born_digital(tmp_path: Path) -> None:
    pytest.skip("Requires a real PDF fixture — add to test_corpus/born_digital/")


def test_read_pdf_ocr_fallback(tmp_path: Path) -> None:
    pytest.skip("Requires an image-only PDF fixture — add to test_corpus/scanned/")
