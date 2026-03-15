"""Ollama local LLM provider using the Ollama Python client directly."""

from __future__ import annotations

import base64
import logging
from pathlib import Path

import ollama

from netlist_converter.config import get_settings
from netlist_converter.llm.provider import LLMProvider, VisionResponse

logger = logging.getLogger(__name__)

# Vision models tile images into 560x560 px patches.
# Keeping images at/below 560px means 1 tile → minimal encoding time.
_NUM_CTX = 4096
_NUM_PREDICT = 1024


class OllamaProvider(LLMProvider):
    """Local LLM provider using the Ollama Python client directly (no LangChain overhead)."""

    def __init__(self) -> None:
        settings = get_settings()
        self._model_name = settings.ollama_vision_model
        self._embed_model = settings.ollama_embed_model
        self._client = ollama.Client(host=settings.ollama_base_url)
        self._options = ollama.Options(
            temperature=0.0,
            num_ctx=_NUM_CTX,
            num_predict=_NUM_PREDICT,
        )

    def analyze_image(self, image_path: Path, prompt: str) -> VisionResponse:
        raw_bytes = image_path.read_bytes()
        return self.analyze_image_bytes(raw_bytes, prompt)

    def analyze_image_bytes(self, image_bytes: bytes, prompt: str) -> VisionResponse:
        logger.info(
            "Sending %d byte image to %s (num_ctx=%d, num_predict=%d)",
            len(image_bytes), self._model_name, _NUM_CTX, _NUM_PREDICT,
        )
        b64 = base64.b64encode(image_bytes).decode("utf-8")

        response = self._client.chat(
            model=self._model_name,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": [b64],
                }
            ],
            options=self._options,
            stream=False,
        )

        raw = response["message"]["content"]
        logger.info("Model returned %d chars", len(raw))
        return VisionResponse(raw_text=raw, model_name=self._model_name)

    def generate_text(self, prompt: str) -> str:
        response = self._client.chat(
            model=self._model_name,
            messages=[{"role": "user", "content": prompt}],
            options=self._options,
            stream=False,
        )
        return response["message"]["content"]

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        result = []
        for text in texts:
            resp = self._client.embed(model=self._embed_model, input=text)
            result.append(resp["embeddings"][0])
        return result
