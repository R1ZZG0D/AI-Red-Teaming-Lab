from __future__ import annotations

from lab.shared.config import Settings
from lab.shared.llm.base import LLMBackend
from lab.shared.llm.mock_backend import MockLLMBackend


def build_llm_backend(settings: Settings) -> LLMBackend:
    if settings.llm_backend == "openai" and settings.openai_api_key:
        from lab.shared.llm.openai_backend import OpenAIBackend

        return OpenAIBackend(settings)
    return MockLLMBackend(settings)
