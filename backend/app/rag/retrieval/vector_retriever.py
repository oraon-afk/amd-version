from __future__ import annotations

from backend.app.core.config import settings
from backend.app.rag.indexing.embeddings import EmbeddingService, embedding_service
from backend.app.rag.indexing.qdrant_store import QdrantStore, qdrant_store
from backend.app.rag.retrieval.types import RetrievalResult


class VectorRetriever:
    def __init__(
        self,
        *,
        store: QdrantStore = qdrant_store,
        embeddings: EmbeddingService = embedding_service,
    ) -> None:
        self.store = store
        self.embeddings = embeddings

    def search(
        self,
        *,
        collection_name: str,
        query: str,
        filters: dict | None = None,
        top_k: int = 8,
    ) -> list[RetrievalResult]:
        query_vector = self.embeddings.embed_query(query)
        results = self.store.search(
            collection_name=collection_name,
            query_vector=query_vector,
            filters=filters,
            top_k=top_k,
        )
        return [
            RetrievalResult(
                chunk_id=str(result.payload.get("chunk_id", result.point_id)),
                text=str(result.payload.get("text", "")),
                score=result.score,
                source="vector",
                payload=result.payload,
                point_id=result.point_id,
            )
            for result in results
            if result.payload.get("text") and result.score >= settings.semantic_similarity_threshold
        ]
