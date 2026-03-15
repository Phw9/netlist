"""Cloud LLM providers (OpenAI, Anthropic) - optional module.

Requires the 'cloud' optional dependency group:
    uv pip install -e ".[cloud]"
"""

from __future__ import annotations

from pathlib import Path

from netlist_converter.config import LLMProviderType, get_settings
from netlist_converter.llm.provider import LLMProvider, VisionResponse


class CloudProvider(LLMProvider):
    """Cloud-based LLM provider supporting OpenAI and Anthropic."""

    def __init__(self) -> None:
        settings = get_settings()
        self._provider_type = settings.llm_provider
        self._chat_model = self._build_chat_model()
        self._model_name = self._get_model_name()

    def _build_chat_model(self):
        settings = get_settings()
        if self._provider_type == LLMProviderType.OPENAI:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model="gpt-4o",
                api_key=settings.openai_api_key,
                temperature=0.1,
            )
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model="claude-sonnet-4-20250514",
            api_key=settings.anthropic_api_key,
            temperature=0.1,
        )

    def _get_model_name(self) -> str:
        if self._provider_type == LLMProviderType.OPENAI:
            return "gpt-4o"
        return "claude-sonnet-4-20250514"

    def analyze_image(self, image_path: Path, prompt: str) -> VisionResponse:
        b64 = self._encode_image_to_base64(image_path)
        return self._invoke_vision(b64, prompt)

    def analyze_image_bytes(self, image_bytes: bytes, prompt: str) -> VisionResponse:
        import base64
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        return self._invoke_vision(b64, prompt)

    def generate_text(self, prompt: str) -> str:
        from langchain_core.messages import HumanMessage
        message = HumanMessage(content=prompt)
        response = self._chat_model.invoke([message])
        return str(response.content)

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        settings = get_settings()
        if self._provider_type == LLMProviderType.OPENAI:
            from langchain_openai import OpenAIEmbeddings
            embedder = OpenAIEmbeddings(api_key=settings.openai_api_key)
        else:
            from langchain_ollama import OllamaEmbeddings
            embedder = OllamaEmbeddings(model=settings.ollama_embed_model)
        return embedder.embed_documents(texts)

    def _invoke_vision(self, image_b64: str, prompt: str) -> VisionResponse:
        from langchain_core.messages import HumanMessage
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                },
            ],
        )
        response = self._chat_model.invoke([message])
        return VisionResponse(raw_text=str(response.content), model_name=self._model_name)
