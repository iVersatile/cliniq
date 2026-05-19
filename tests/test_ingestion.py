"""Parametrised integration tests: read_pdf() against the test corpus."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cliniq.ingestion.pdf_reader import read_pdf

CORPUS_ROOT = Path(__file__).parent.parent / "test_corpus"
BORN_DIGITAL = sorted((CORPUS_ROOT / "born_digital").glob("*.pdf"))
SCANNED = sorted((CORPUS_ROOT / "scanned").glob("*.pdf"))
REAL_WORLD = sorted((CORPUS_ROOT / "real_world").glob("*.pdf"))


def _load_gt(pdf: Path) -> dict:  # type: ignore[type-arg]
    gt_path = pdf.parent / "ground_truth" / (pdf.stem + ".json")
    return json.loads(gt_path.read_text())


@pytest.mark.parametrize("pdf", BORN_DIGITAL, ids=[p.stem for p in BORN_DIGITAL])
def test_born_digital_text_layer(pdf: Path) -> None:
    gt = _load_gt(pdf)
    doc = read_pdf(pdf)

    assert len(doc.pages) == gt["page_count"]
    for page, gt_page in zip(doc.pages, gt["pages"]):
        msg = f"{pdf.name} p{page.page_number}: expected text layer, got OCR"
        assert page.via_ocr is False, msg
        assert page.text.strip(), f"{pdf.name} p{page.page_number}: empty text"
        assert len(page.text) == gt_page["text_length"]


@pytest.mark.parametrize("pdf", SCANNED, ids=[p.stem for p in SCANNED])
def test_scanned_ocr_fallback(pdf: Path) -> None:
    gt = _load_gt(pdf)
    doc = read_pdf(pdf)

    assert len(doc.pages) == gt["page_count"]
    for page, gt_page in zip(doc.pages, gt["pages"]):
        assert page.via_ocr is True, f"{pdf.name} p{page.page_number}: expected OCR path"
        assert gt_page["text_nonempty"], f"{pdf.name}: ground truth has empty text"
        assert page.text.strip() or page.is_handwritten, f"{pdf.name}: OCR returned no text"


@pytest.mark.parametrize("pdf", REAL_WORLD, ids=[p.stem for p in REAL_WORLD])
def test_real_world_mixed(pdf: Path) -> None:
    gt = _load_gt(pdf)
    doc = read_pdf(pdf)

    assert len(doc.pages) == gt["page_count"]
    for page, gt_page in zip(doc.pages, gt["pages"]):
        if not gt_page["via_ocr"]:
            assert page.via_ocr is False, f"{pdf.name} p{page.page_number}: expected text layer"
            assert len(page.text) == gt_page["text_length"]
        else:
            assert page.via_ocr is True, f"{pdf.name} p{page.page_number}: expected OCR path"
            if gt_page["text_nonempty"]:
                has_text = page.text.strip() or page.is_handwritten
                assert has_text, f"{pdf.name} p{page.page_number}: OCR returned no text"


ALL_PDFS = BORN_DIGITAL + SCANNED + REAL_WORLD


@pytest.mark.parametrize("pdf", ALL_PDFS, ids=[p.stem for p in ALL_PDFS])
def test_no_unhandled_exception(pdf: Path) -> None:
    doc = read_pdf(pdf)
    assert doc.pages, f"{pdf.name}: returned 0 pages"
