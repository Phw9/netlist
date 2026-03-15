"""Tests for document_loader module."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from PIL import Image

from netlist_converter.core.document_loader import (
    MAX_IMAGE_DIMENSION,
    LoadedDocument,
    image_to_bytes,
    load_document,
)


def _create_test_image(path: Path, width: int = 200, height: int = 150) -> Path:
    """Helper to create a simple test image file."""
    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    img.save(str(path))
    return path


class TestLoadImage:
    def test_load_png(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = _create_test_image(Path(tmpdir) / "test.png")
            doc = load_document(img_path)

        assert isinstance(doc, LoadedDocument)
        assert doc.page_count == 1
        assert doc.pages[0].page_number == 1
        assert doc.pages[0].source_file == "test.png"

    def test_load_jpg(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = _create_test_image(Path(tmpdir) / "test.jpg")
            doc = load_document(img_path)

        assert doc.page_count == 1

    def test_unsupported_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_path = Path(tmpdir) / "test.xyz"
            bad_path.write_text("not an image")
            with pytest.raises(ValueError, match="Unsupported file type"):
                load_document(bad_path)

    def test_large_image_resize(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            big_path = _create_test_image(Path(tmpdir) / "big.png", width=4000, height=3000)
            doc = load_document(big_path)

        page = doc.pages[0]
        width, height = page.image.size
        assert max(width, height) <= MAX_IMAGE_DIMENSION


class TestImageToBytes:
    def test_png_bytes(self) -> None:
        img = Image.new("RGB", (100, 100), color=(0, 255, 0))
        data = image_to_bytes(img, "PNG")
        assert len(data) > 0
        assert data[:4] == b'\x89PNG'
