from __future__ import annotations

from functools import lru_cache
from openai import OpenAI

from services.config import settings


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAI:
    api_key = settings.active_api_key()
    if not api_key and settings.llm_provider.lower() in ("openai", "gemini"):
        raise ValueError(
            f"API key is required for provider '{settings.llm_provider}'. "
            "Please set GEMINI_API_KEY or OPENAI_API_KEY in your .env file."
        )
    return OpenAI(
        api_key=api_key or "placeholder-key",
        base_url=settings.active_base_url(),
        timeout=settings.openai_timeout,
        max_retries=2,
    )
