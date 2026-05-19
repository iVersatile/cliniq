"""Unit tests for preprocess_image() from cliniq.ingestion.preprocessing."""

from __future__ import annotations

import PIL.Image


def test_output_is_pil_image() -> None:
    """Test that preprocess_image returns a PIL.Image.Image instance."""
    from cliniq.ingestion.preprocessing import preprocess_image

    # Arrange
    input_img = PIL.Image.new("RGB", (100, 100), color=(128, 128, 128))

    # Act
    result = preprocess_image(input_img)

    # Assert
    assert isinstance(result, PIL.Image.Image)


def test_output_mode_is_L() -> None:
    """Test that output mode is 'L' (grayscale, not '1' or 'RGB')."""
    from cliniq.ingestion.preprocessing import preprocess_image

    # Arrange
    input_img = PIL.Image.new("RGB", (100, 100), color=(64, 64, 64))

    # Act
    result = preprocess_image(input_img)

    # Assert
    assert result.mode == "L", f"Expected output mode 'L' but got '{result.mode}'"


def test_output_size_unchanged() -> None:
    """Test that width and height remain the same as input."""
    from cliniq.ingestion.preprocessing import preprocess_image

    # Arrange
    input_width = 320
    input_height = 240
    input_img = PIL.Image.new("RGB", (input_width, input_height), color=(100, 100, 100))

    # Act
    result = preprocess_image(input_img)

    # Assert
    assert result.width == input_width
    assert result.height == input_height
    assert result.size == (input_width, input_height)


def test_rgb_input_converted() -> None:
    """Test that RGB input is converted to grayscale mode 'L' output."""
    from cliniq.ingestion.preprocessing import preprocess_image

    # Arrange
    input_img = PIL.Image.new("RGB", (50, 50), color=(200, 100, 50))
    assert input_img.mode == "RGB"

    # Act
    result = preprocess_image(input_img)

    # Assert
    assert result.mode == "L"
    assert isinstance(result, PIL.Image.Image)


def test_binarisation_high_pixel_becomes_white() -> None:
    """Test that pure white (255,255,255) RGB produces all pixels at 255."""
    from cliniq.ingestion.preprocessing import preprocess_image

    # Arrange
    input_img = PIL.Image.new("RGB", (10, 10), color=(255, 255, 255))

    # Act
    result = preprocess_image(input_img)

    # Assert
    # After binarization with threshold 128, white (255) should remain 255
    pixels = list(result.getdata())
    assert all(pixel == 255 for pixel in pixels), (
        f"Expected all pixels to be 255 (white), but got {set(pixels)}"
    )
