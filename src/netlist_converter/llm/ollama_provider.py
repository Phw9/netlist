"""Ollama local LLM provider using the Ollama Python client directly."""

from __future__ import annotations

import base64
import logging
from pathlib import Path

import ollama

from netlist_converter.config import get_settings
from netlist_converter.llm.provider import LLMProvider, VisionResponse

logger = logging.getLogger(__name__)

# Context window: prompt tokens (~800) + image tokens (~400) + output tokens.
# llama3.2-vision 10.7B can generate ~3000 tokens reliably before drifting.
_NUM_CTX = 8192
_NUM_PREDICT = 3000

# System message: strict JSON enforcement
_SYSTEM_PROMPT = (
    "You are a circuit analysis tool. "
    "You MUST respond with ONLY a valid JSON object. "
    "No explanations, no markdown code fences, no text outside the JSON. "
    "Raw JSON only. Start your response with '{' and end with '}'."
)

# Preferred model order: try llama3.2-vision first (better quality), fall back to llava:7b
_VISION_MODEL_PRIORITY = ["llama3.2-vision:latest", "llama3.2-vision", "llava:7b"]


def _select_vision_model(client: ollama.Client, configured: str) -> str:
    """Return configured model if available, else fall back to priority list."""
    try:
        models_resp = client.list()
        available = {m.model for m in models_resp.models}
        if configured in available:
            return configured
        for preferred in _VISION_MODEL_PRIORITY:
            if preferred in available:
                logger.info("Configured model '%s' not found; using '%s'", configured, preferred)
                return preferred
    except Exception:
        pass
    return configured


class OllamaProvider(LLMProvider):
    """Local LLM provider using the Ollama Python client directly."""

    def __init__(self) -> None:
        settings = get_settings()
        self._embed_model = settings.ollama_embed_model
        self._client = ollama.Client(host=settings.ollama_base_url)
        self._model_name = _select_vision_model(self._client, settings.ollama_vision_model)
        self._options = ollama.Options(
            temperature=0.0,
            num_ctx=_NUM_CTX,
            num_predict=_NUM_PREDICT,
        )
        logger.info("OllamaProvider: vision=%s, embed=%s", self._model_name, self._embed_model)

    def analyze_image(self, image_path: Path, prompt: str) -> VisionResponse:
        raw_bytes = image_path.read_bytes()
        return self.analyze_image_bytes(raw_bytes, prompt)

    def analyze_image_bytes(self, image_bytes: bytes, prompt: str) -> VisionResponse:
        logger.info(
            "Sending %d byte image to %s (num_predict=%d)",
            len(image_bytes), self._model_name, _NUM_PREDICT,
        )
        b64 = base64.b64encode(image_bytes).decode("utf-8")

        response = self._client.chat(
            model=self._model_name,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": prompt,
                    "images": [b64],
                },
            ],
            options=self._options,
            stream=False,
        )

        raw = response.message.content
        logger.info("Model '%s' returned %d chars", self._model_name, len(raw))
        return VisionResponse(raw_text=raw, model_name=self._model_name)

    def generate_text(self, prompt: str) -> str:
        response = self._client.chat(
            model=self._model_name,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            options=self._options,
            stream=False,
        )
        return response.message.content

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        result = []
        for text in texts:
            resp = self._client.embed(model=self._embed_model, input=text)
            result.append(resp.embeddings[0])
        return result
