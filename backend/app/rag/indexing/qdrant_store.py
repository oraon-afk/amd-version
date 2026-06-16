from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import sleep
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from backend.app.core.config import settings
from backend.app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class VectorSearchResult:
    point_id: str
    score: float
    payload: dict[str, Any]


class QdrantStore:
    def __init__(self) -> None:
        self._client: QdrantClient | None = None
        self._vector_names: dict[str, str | None] = {}

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            qdrant_url = settings.local_qdrant_url or settings.qdrant_url
            if not qdrant_url:
                raise RuntimeError("QDRANT_URL is required for Qdrant operations.")
            self._client = QdrantClient(
                url=qdrant_url,
                api_key=settings.qdrant_api_key if not settings.local_qdrant_url else None,
                timeout=settings.qdrant_timeout_seconds,
            )
        return self._client

    def check_connection(self) -> bool:
        collections = {collection.name for collection in self.client.get_collections().collections}
        required = {_collection_name(settings.qdrant_rule_collection), _collection_name(settings.qdrant_upload_collection)}
        missing = sorted(required - collections)
        if missing:
            raise RuntimeError(f"Missing Qdrant collections: {', '.join(missing)}")
        return True

    def ensure_collections(self, *, vector_size: int = 384) -> None:
        existing = {collection.name for collection in self.client.get_collections().collections}
        for collection_name in (_collection_name(settings.qdrant_upload_collection), _collection_name(settings.qdrant_rule_collection)):
            if collection_name not in existing:
                logger.info("qdrant.create_collection collection=%s", collection_name)
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
                )
            self._ensure_payload_indexes(collection_name)

    def _ensure_payload_indexes(self, collection_name: str) -> None:
        collection_name = _collection_name(collection_name)
        schema = self.client.get_collection(collection_name).payload_schema or {}
        fields = {
            "source_type",
            "document_id",
            "chunk_id",
            "domain",
            "source",
            "section",
            "section_title",
            "role_type",
            "uploaded_by",
            "user_id",
            "audit_id",
            "rule_set_id",
        }
        for field in fields:
            if field in schema:
                continue
            logger.info("qdrant.create_payload_index collection=%s field=%s", collection_name, field)
            self.client.create_payload_index(
                collection_name=collection_name,
                field_name=field,
                field_schema=PayloadSchemaType.KEYWORD,
            )

    def upsert_chunks(
        self,
        *,
        collection_name: str,
        chunks: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> list[str]:
        collection_name = _collection_name(collection_name)
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")

        vector_name = self._get_vector_name(collection_name)
        points = []
        point_ids = []
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            chunk_id = str(chunk["chunk_id"])
            point_id = str(uuid5(NAMESPACE_URL, chunk_id))
            point_ids.append(point_id)
            vector: list[float] | dict[str, list[float]]
            vector = {vector_name: embedding} if vector_name else embedding
            points.append(PointStruct(id=point_id, vector=vector, payload=chunk))

        if points:
            logger.info(
                "qdrant.upsert collection=%s points=%s",
                collection_name,
                len(points),
            )
            self._retry(lambda: self.client.upsert(collection_name=collection_name, points=points))
        return point_ids

    async def upsert_chunks_async(
        self,
        *,
        collection_name: str,
        chunks: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> list[str]:
        return await asyncio.to_thread(
            self.upsert_chunks,
            collection_name=collection_name,
            chunks=chunks,
            embeddings=embeddings,
        )

    def search(
        self,
        *,
        collection_name: str,
        query_vector: list[float],
        filters: dict[str, Any] | None = None,
        top_k: int = 8,
    ) -> list[VectorSearchResult]:
        collection_name = _collection_name(collection_name)
        vector_name = self._get_vector_name(collection_name)
        query_filter = self._build_filter(filters)
        logger.info(
            "qdrant.search collection=%s top_k=%s filters=%s",
            collection_name,
            top_k,
            sorted((filters or {}).keys()),
        )

        if hasattr(self.client, "query_points"):
            response = self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                using=vector_name,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
            )
            points = response.points
        else:
            query = (vector_name, query_vector) if vector_name else query_vector
            points = self.client.search(
                collection_name=collection_name,
                query_vector=query,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
            )

        return [
            VectorSearchResult(
                point_id=str(point.id),
                score=float(point.score or 0.0),
                payload=dict(point.payload or {}),
            )
            for point in points
        ]

    def scroll_payloads(
        self,
        *,
        collection_name: str,
        filters: dict[str, Any] | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        collection_name = _collection_name(collection_name)
        query_filter = self._build_filter(filters)
        offset = None
        payloads: list[dict[str, Any]] = []

        while True:
            points, offset = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=query_filter,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for point in points:
                payload = dict(point.payload or {})
                payload["_point_id"] = str(point.id)
                payloads.append(payload)
            if offset is None:
                break

        return payloads

    def _get_vector_name(self, collection_name: str) -> str | None:
        collection_name = _collection_name(collection_name)
        if collection_name in self._vector_names:
            return self._vector_names[collection_name]

        collection = self.client.get_collection(collection_name)
        vectors = collection.config.params.vectors
        vector_name: str | None = None
        if isinstance(vectors, dict):
            if "dense" in vectors:
                vector_name = "dense"
            else:
                vector_name = next(iter(vectors.keys()), None)
        self._vector_names[collection_name] = vector_name
        return vector_name

    @staticmethod
    def _build_filter(filters: dict[str, Any] | None) -> Filter | None:
        if not filters:
            return None

        conditions = []
        for key, value in filters.items():
            if value is None:
                continue
            if isinstance(value, list | tuple | set):
                conditions.append(
                    FieldCondition(key=key, match=MatchAny(any=[item for item in value])),
                )
            else:
                conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
        if not conditions:
            return None
        return Filter(must=conditions)

    @staticmethod
    def _retry(operation, *, attempts: int | None = None):
        max_attempts = max(1, int(attempts or settings.qdrant_retry_attempts or 1))
        last_exc = None
        for attempt in range(max_attempts):
            try:
                return operation()
            except Exception as exc:
                last_exc = exc
                if attempt == max_attempts - 1:
                    break
                sleep(max(0.0, settings.qdrant_retry_backoff_seconds) * (attempt + 1))
        raise last_exc


def _collection_name(value: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        raise ValueError("Qdrant collection name is not configured.")
    return cleaned


qdrant_store = QdrantStore()
