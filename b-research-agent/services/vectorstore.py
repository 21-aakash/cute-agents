from __future__ import annotations

import logging
import uuid
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from services.config import settings
from services.embedder import Embedder

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self, client: QdrantClient | None = None) -> None:
        try:
            self.client = client or QdrantClient(
                url=settings.qdrant_url,
                timeout=3.0,
                check_compatibility=False,
            )
            self._ensure_collections()
        except Exception as e:
            logger.warning("Could not connect to Qdrant at %s (%s). Falling back to in-memory vector store.", settings.qdrant_url, e)
            self.client = QdrantClient(":memory:")
            self._ensure_collections()

    def _ensure_collections(self) -> None:
        try:
            for name in (
                settings.qdrant_collection_documents,
                settings.qdrant_collection_memory,
                settings.qdrant_collection_vault,
            ):
                if not self.client.collection_exists(name):
                    self.client.create_collection(
                        collection_name=name,
                        vectors_config=qmodels.VectorParams(
                            size=settings.embedding_dim,
                            distance=qmodels.Distance.COSINE,
                        ),
                    )
        except Exception as e:
            logger.warning("Could not ensure vector collections: %s", e)

    def upsert_document_chunks(
        self,
        workspace_id: str,
        doc_id: str,
        chunks: list[dict[str, Any]],
        embedder: Embedder,
    ) -> int:
        if not chunks:
            return 0
        texts = [c["text"] for c in chunks]
        vectors = embedder.embed_passages(texts)
        points = []
        for i, chunk in enumerate(chunks):
            payload = {**chunk, "workspace_id": workspace_id, "doc_id": doc_id}
            points.append(
                qmodels.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vectors[i],
                    payload=payload,
                )
            )
        self.client.upsert(collection_name=settings.qdrant_collection_documents, points=points)
        return len(points)

    def search_documents(
        self,
        workspace_id: str,
        vector: list[float],
        top_k: int,
        filter_doc_ids: list[str] | None = None,
    ) -> list[Any]:
        conditions: list[Any] = [
            qmodels.FieldCondition(
                key="workspace_id",
                match=qmodels.MatchValue(value=workspace_id),
            )
        ]
        if filter_doc_ids:
            conditions.append(
                qmodels.FieldCondition(
                    key="doc_id",
                    match=qmodels.MatchAny(any=filter_doc_ids),
                )
            )
        result = self.client.search(
            collection_name=settings.qdrant_collection_documents,
            query_vector=vector,
            limit=top_k,
            query_filter=qmodels.Filter(must=conditions),
        )
        return result

    def search_memory(
        self,
        workspace_id: str,
        vector: list[float],
        top_k: int,
    ) -> list[Any]:
        return self.client.search(
            collection_name=settings.qdrant_collection_memory,
            query_vector=vector,
            limit=top_k,
            query_filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="workspace_id",
                        match=qmodels.MatchValue(value=workspace_id),
                    )
                ]
            ),
        )

    def persist_finding(
        self,
        workspace_id: str,
        session_id: str,
        query: str,
        finding: str,
        embedder: Embedder,
    ) -> None:
        vector = embedder.embed_passage(finding)
        payload = {
            "workspace_id": workspace_id,
            "session_id": session_id,
            "query": query,
            "finding": finding,
        }
        self.client.upsert(
            collection_name=settings.qdrant_collection_memory,
            points=[qmodels.PointStruct(id=str(uuid.uuid4()), vector=vector, payload=payload)],
        )

    def delete_document_chunks(self, workspace_id: str, doc_id: str) -> None:
        self.client.delete(
            collection_name=settings.qdrant_collection_documents,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="workspace_id",
                            match=qmodels.MatchValue(value=workspace_id),
                        ),
                        qmodels.FieldCondition(
                            key="doc_id",
                            match=qmodels.MatchValue(value=doc_id),
                        ),
                    ]
                )
            ),
        )

    def reset_memory(self, workspace_id: str) -> None:
        self.client.delete(
            collection_name=settings.qdrant_collection_memory,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="workspace_id",
                            match=qmodels.MatchValue(value=workspace_id),
                        )
                    ]
                )
            ),
        )

    def health_ok(self) -> bool:
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False
