"""Load PDF and image files, extract page images for vision analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}
SUPPORTED_PDF_EXTENSION = ".pdf"
PDF_RENDER_DPI = 100
MAX_IMAGE_DIMENSION = 560
JPEG_QUALITY = 70


@dataclass
class LoadedPage:
    """A single page/image extracted from an input document."""

    image: Image.Image
    page_number: int
    source_file: str


@dataclass
class LoadedDocument:
    """All pages extracted from a single input file."""

    source_path: Path
    pages: list[LoadedPage] = field(default_factory=list)

    @property
    def page_count(self) -> int:
        return len(self.pages)


def _resize_if_needed(img: Image.Image) -> Image.Image:
    """Down-scale large images while preserving aspect ratio."""
    width, height = img.size
    if width <= MAX_IMAGE_DIMENSION and height <= MAX_IMAGE_DIMENSION:
        return img

    scale = MAX_IMAGE_DIMENSION / max(width, height)
    new_size = (int(width * scale), int(height * scale))
    return img.resize(new_size, Image.LANCZOS)


def _load_pdf(path: Path) -> list[LoadedPage]:
    """Render each PDF page to a PIL Image."""
    pages: list[LoadedPage] = []
    doc = fitz.open(str(path))
    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=PDF_RENDER_DPI)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            img = _resize_if_needed(img)
            pages.append(LoadedPage(
                image=img,
                page_number=page_num + 1,
                source_file=path.name,
            ))
    finally:
        doc.close()
    return pages


def _load_image(path: Path) -> list[LoadedPage]:
    """Load a single image file."""
    img = Image.open(path).convert("RGB")
    img = _resize_if_needed(img)
    page = LoadedPage(image=img, page_number=1, source_file=path.name)
    return [page]


def load_document(path: Path) -> LoadedDocument:
    """Load a PDF or image file and return extracted pages.

    Raises ValueError for unsupported file types.
    """
    suffix = path.suffix.lower()

    if suffix == SUPPORTED_PDF_EXTENSION:
        pages = _load_pdf(path)
    elif suffix in SUPPORTED_IMAGE_EXTENSIONS:
        pages = _load_image(path)
    else:
        supported = ", ".join(sorted(SUPPORTED_IMAGE_EXTENSIONS | {SUPPORTED_PDF_EXTENSION}))
        raise ValueError(f"Unsupported file type '{suffix}'. Supported: {supported}")

    return LoadedDocument(source_path=path, pages=pages)


def image_to_bytes(img: Image.Image, fmt: str = "JPEG") -> bytes:
    """Convert a PIL Image to compressed bytes. JPEG by default to minimize payload."""
    import io
    buf = io.BytesIO()
    if fmt.upper() == "JPEG":
        img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    else:
        img.save(buf, format=fmt)
    return buf.getvalue()
