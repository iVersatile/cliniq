"""Image preprocessing pipeline for OCR quality improvement."""

from __future__ import annotations

from PIL import Image, ImageEnhance, ImageFilter


def preprocess_image(img: Image.Image) -> Image.Image:
    """Preprocess image for OCR via contrast enhancement, sharpening, and binarization."""
    img = img.convert("L")
    img = ImageEnhance.Contrast(img).enhance(1.5)
    img = img.filter(ImageFilter.SHARPEN)
    img = img.point(lambda x: 0 if x < 128 else 255, "1")
    return img.convert("L")
