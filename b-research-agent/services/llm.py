from __future__ import annotations

import json
import logging
import time
from typing import Any, Iterator

import httpx

from services.config import settings
from services.openai_client import get_openai_client

logger = logging.getLogger(__name__)


def _completion_limit_kwargs(max_tokens: int, model: str) -> dict[str, int]:
    """Handles max_tokens vs max_completion_tokens for different provider models."""
    m = model.lower()
    if m.startswith("o3") or m.startswith("o4") or m.startswith("gpt-5"):
        return {"max_completion_tokens": max_tokens}
    return {"max_tokens": max_tokens}


def _supports_custom_temperature(model: str) -> bool:
    """Reasoning models (o1, o3, o4) only accept default temperature."""
    m = model.lower()
    if m.startswith(("o1", "o3", "o4", "gpt-5")):
        return False
    return True


def _openai_chat_kwargs(*, model: str, temperature: float, max_tokens: int) -> dict[str, Any]:
    kwargs: dict[str, Any] = _completion_limit_kwargs(max_tokens, model)
    if _supports_custom_temperature(model):
        kwargs["temperature"] = temperature
    return kwargs


class LLMClient:
    def complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        role: str = "default",
    ) -> str:
        provider = settings.llm_provider.lower()
        if provider in ("openai", "gemini"):
            return self._openai_complete(
                system, user, temperature=temperature, max_tokens=max_tokens, role=role
            )
        return self._ollama_complete(system, user, temperature=temperature)

    def stream(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        role: str = "default",
    ) -> Iterator[str]:
        provider = settings.llm_provider.lower()
        if provider in ("openai", "gemini"):
            yield from self._openai_stream(
                system, user, temperature=temperature, max_tokens=max_tokens, role=role
            )
        else:
            yield self._ollama_complete(system, user, temperature=temperature)

    def complete_json(
        self,
        system: str,
        user: str,
        *,
        fallback: dict[str, Any],
        temperature: float = 0.1,
        role: str = "default",
    ) -> dict[str, Any]:
        raw = self.complete(
            system=system + "\n\nReturn valid JSON only.",
            user=user,
            temperature=temperature,
            role=role,
        )
        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(raw[start:end])
        except json.JSONDecodeError:
            logger.warning("LLM returned invalid JSON for role=%s; using fallback", role)
        return fallback

    def _ollama_complete(self, system: str, user: str, *, temperature: float) -> str:
        payload = {
            "model": settings.ollama_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {"temperature": temperature},
        }
        start = time.perf_counter()
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{settings.ollama_host}/api/chat", json=payload)
            resp.raise_for_status()
            content = resp.json()["message"]["content"]
        logger.info(
            "ollama.complete model=%s role=default latency_ms=%.0f chars=%d",
            settings.ollama_model,
            (time.perf_counter() - start) * 1000,
            len(content),
        )
        return content

    def _openai_complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float,
        max_tokens: int,
        role: str,
    ) -> str:
        client = get_openai_client()
        model = settings.model_for(role)
        start = time.perf_counter()
        logger.info("llm.complete start role=%s model=%s provider=%s", role, model, settings.llm_provider)
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                **_openai_chat_kwargs(model=model, temperature=temperature, max_tokens=max_tokens),
            )
            content = response.choices[0].message.content or ""
            logger.info(
                "llm.complete ok role=%s model=%s latency_ms=%.0f chars=%d",
                role,
                model,
                (time.perf_counter() - start) * 1000,
                len(content),
            )
            return content
        except Exception:
            logger.exception(
                "llm.complete failed role=%s model=%s latency_ms=%.0f",
                role,
                model,
                (time.perf_counter() - start) * 1000,
            )
            raise

    def _openai_stream(
        self,
        system: str,
        user: str,
        *,
        temperature: float,
        max_tokens: int,
        role: str,
    ) -> Iterator[str]:
        client = get_openai_client()
        model = settings.model_for(role)
        start = time.perf_counter()
        logger.info("llm.stream start role=%s model=%s provider=%s", role, model, settings.llm_provider)
        try:
            stream = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                **_openai_chat_kwargs(model=model, temperature=temperature, max_tokens=max_tokens),
                stream=True,
            )
            chars = 0
            for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta.content or ""
                    if delta:
                        chars += len(delta)
                        yield delta
            logger.info(
                "llm.stream ok role=%s model=%s latency_ms=%.0f chars=%d",
                role,
                model,
                (time.perf_counter() - start) * 1000,
                chars,
            )
        except Exception:
            logger.exception(
                "llm.stream failed role=%s model=%s latency_ms=%.0f",
                role,
                model,
                (time.perf_counter() - start) * 1000,
            )
            raise
