"""Abstract LLM provider interface."""

from __future__ import annotations

import base64
from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel


class VisionResponse(BaseModel):
    """Structured response from a vision LLM call."""

    raw_text: str
    model_name: str


class LLMProvider(ABC):
    """Protocol for interchangeable LLM backends."""

    @abstractmethod
    def analyze_image(self, image_path: Path, prompt: str) -> VisionResponse:
        """Send an image with a text prompt and return the LLM response."""

    @abstractmethod
    def analyze_image_bytes(self, image_bytes: bytes, prompt: str) -> VisionResponse:
        """Send raw image bytes with a text prompt and return the LLM response."""

    @abstractmethod
    def generate_text(self, prompt: str) -> str:
        """Generate text from a prompt without image input."""

    @abstractmethod
    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for a list of texts."""

    @staticmethod
    def _encode_image_to_base64(image_path: Path) -> str:
        """Read an image file and return its base64-encoded string."""
        raw = image_path.read_bytes()
        return base64.b64encode(raw).decode("utf-8")
