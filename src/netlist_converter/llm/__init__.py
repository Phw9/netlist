"""LLM provider abstraction layer."""

from __future__ import annotations

from netlist_converter.config import LLMProviderType, get_settings
from netlist_converter.llm.provider import LLMProvider, VisionResponse


def create_llm_provider() -> LLMProvider:
    """Factory: build the appropriate LLM provider from settings."""
    settings = get_settings()

    if settings.llm_provider == LLMProviderType.OLLAMA:
        from netlist_converter.llm.ollama_provider import OllamaProvider
        return OllamaProvider()

    from netlist_converter.llm.cloud_provider import CloudProvider
    return CloudProvider()


__all__ = ["LLMProvider", "VisionResponse", "create_llm_provider"]
