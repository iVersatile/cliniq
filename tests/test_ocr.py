"""Unit tests for cliniq.ingestion.ocr — isolated from real Tesseract/PDFs."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from cliniq.ingestion.ocr import (
    _HANDWRITING_MARKER,
    _LOW_CONF_THRESHOLD,
    _parse_confidences,
    ocr_page,
)

# ---------------------------------------------------------------------------
# _parse_confidences
# ---------------------------------------------------------------------------


def test_parse_confidences_filters_negatives() -> None:
    assert _parse_confidences(["-1", "50", "80"]) == [50, 80]


def test_parse_confidences_skips_non_numeric() -> None:
    assert _parse_confidences(["abc", "", None, "75"]) == [75]  # type: ignore[list-item]


def test_parse_confidences_empty_input() -> None:
    assert _parse_confidences([]) == []


def test_parse_confidences_all_negative() -> None:
    assert _parse_confidences(["-1", "-2"]) == []


def test_parse_confidences_zero_included() -> None:
    assert _parse_confidences(["0", "1"]) == [0, 1]


# ---------------------------------------------------------------------------
# ocr_page — happy path via mocks
# ---------------------------------------------------------------------------


def _make_page_mock() -> MagicMock:
    from PIL import Image

    img = Image.new("RGB", (100, 100), color=255)
    page_image_mock = MagicMock()
    page_image_mock.original = img
    page_mock = MagicMock()
    page_mock.to_image.return_value = page_image_mock
    return page_mock


def _tess_data(confs: list[int]) -> dict:  # type: ignore[type-arg]
    return {"conf": confs}


@patch("cliniq.ingestion.ocr.pytesseract.image_to_string", return_value="Hello world")
@patch("cliniq.ingestion.ocr.pytesseract.image_to_data")
def test_ocr_page_normal(mock_data: MagicMock, mock_str: MagicMock) -> None:
    mock_data.return_value = _tess_data([90, 85, 88])

    result = ocr_page(_make_page_mock(), page_number=1)

    assert result.page_number == 1
    assert result.text == "Hello world"
    assert result.via_ocr is True
    assert result.low_confidence is False
    assert result.is_handwritten is False


@patch("cliniq.ingestion.ocr.pytesseract.image_to_string", return_value="blurry text")
@patch("cliniq.ingestion.ocr.pytesseract.image_to_data")
def test_ocr_page_low_confidence(mock_data: MagicMock, mock_str: MagicMock) -> None:
    mock_data.return_value = _tess_data([30, 40, 20])

    result = ocr_page(_make_page_mock(), page_number=2)

    assert result.low_confidence is True
    assert result.is_handwritten is False
    assert result.text == "blurry text"


@patch("cliniq.ingestion.ocr.pytesseract.image_to_string", return_value="")
@patch("cliniq.ingestion.ocr.pytesseract.image_to_data")
def test_ocr_page_handwritten_marker(mock_data: MagicMock, mock_str: MagicMock) -> None:
    mock_data.return_value = _tess_data([10, 5])

    result = ocr_page(_make_page_mock(), page_number=3)

    assert result.text == _HANDWRITING_MARKER
    assert result.is_handwritten is True
    assert result.via_ocr is True


@patch("cliniq.ingestion.ocr.pytesseract.image_to_string", return_value="x")
@patch("cliniq.ingestion.ocr.pytesseract.image_to_data")
def test_ocr_page_empty_confidences_means_low(mock_data: MagicMock, mock_str: MagicMock) -> None:
    mock_data.return_value = _tess_data([])

    result = ocr_page(_make_page_mock(), page_number=4)

    assert result.low_confidence is True


@patch(
    "cliniq.ingestion.ocr.pytesseract.image_to_data",
    side_effect=RuntimeError("tesseract not found"),
)
def test_ocr_page_tesseract_error_returns_fallback(mock_data: MagicMock) -> None:
    result = ocr_page(_make_page_mock(), page_number=5)

    assert result.text == _HANDWRITING_MARKER
    assert result.low_confidence is True
    assert result.is_handwritten is True
    assert result.via_ocr is True


def test_low_conf_threshold_is_60() -> None:
    assert _LOW_CONF_THRESHOLD == 60
