from __future__ import annotations

from functools import lru_cache
from typing import Protocol

from services.config import settings
from services.openai_client import get_openai_client


class Embedder(Protocol):
    def embed_query(self, text: str) -> list[float]: ...
    def embed_passage(self, text: str) -> list[float]: ...
    def embed_passages(self, texts: list[str]) -> list[list[float]]: ...


class LocalEmbedder:
    def __init__(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ImportError(
                "Local embedding requires `sentence-transformers`. "
                "Install it with `pip install sentence-transformers` or set EMBEDDING_PROVIDER=openai in .env"
            ) from e
        self._model = SentenceTransformer(settings.embedding_model)

    def embed_query(self, text: str) -> list[float]:
        prefixed = f"{settings.bge_query_prefix}{text}"
        return self._model.encode(prefixed, normalize_embeddings=True).tolist()

    def embed_passage(self, text: str) -> list[float]:
        return self._model.encode(text, normalize_embeddings=True).tolist()

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vectors]


class OpenAIEmbedder:
    """Uses the configured OpenAI-compatible or Gemini embedding endpoint."""

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        client = get_openai_client()
        response = client.embeddings.create(
            model=settings.openai_embedding_model,
            input=texts,
        )
        ordered = sorted(response.data, key=lambda row: row.index)
        return [row.embedding for row in ordered]

    def embed_query(self, text: str) -> list[float]:
        return self._embed_batch([text])[0]

    def embed_passage(self, text: str) -> list[float]:
        return self.embed_query(text)

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        batch_size = 64
        out: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            out.extend(self._embed_batch(texts[i : i + batch_size]))
        return out


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    provider = settings.embedding_provider.lower()
    if provider in ("openai", "gemini"):
        return OpenAIEmbedder()
    if provider == "local":
        return LocalEmbedder()
    raise ValueError(f"Unknown EMBEDDING_PROVIDER: {settings.embedding_provider}")
