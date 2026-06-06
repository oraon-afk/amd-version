from __future__ import annotations

from time import time

from backend.app.core.config import settings
from backend.app.core.logging import get_logger, log_pipeline_stage
from backend.app.rag.indexing.qdrant_store import QdrantStore, qdrant_store
from backend.app.rag.retrieval.bm25_retriever import BM25Retriever
from backend.app.rag.retrieval.context_validator import ContextValidator, context_validator
from backend.app.rag.retrieval.reranker import Reranker, reranker
from backend.app.rag.retrieval.types import RetrievalResult
from backend.app.rag.retrieval.vector_retriever import VectorRetriever

logger = get_logger(__name__)


class HybridRetriever:
    def __init__(
        self,
        *,
        store: QdrantStore = qdrant_store,
        vector_retriever: VectorRetriever | None = None,
        bm25_retriever: BM25Retriever | None = None,
        reranker_: Reranker = reranker,
        validator: ContextValidator = context_validator,
    ) -> None:
        self.store = store
        self.vector_retriever = vector_retriever or VectorRetriever(store=store)
        self.bm25_retriever = bm25_retriever or BM25Retriever()
        self.reranker = reranker_
        self.validator = validator

    def search(
        self,
        *,
        collection_name: str,
        query: str,
        filters: dict | None = None,
        vector_top_k: int | None = None,
        bm25_top_k: int | None = None,
        final_top_k: int | None = None,
        audit_id: str | None = None,
        document_id: str | None = None,
        domain: str | None = None,
    ) -> list[RetrievalResult]:
        started = time()
        vector_top_k = vector_top_k or settings.top_k_vector
        bm25_top_k = bm25_top_k or settings.top_k_bm25
        final_top_k = final_top_k or settings.final_top_k

        vector_results: list[RetrievalResult] = []
        bm25_results: list[RetrievalResult] = []

        if settings.enable_hybrid_retrieval:
            try:
                vector_results = self.vector_retriever.search(
                    collection_name=collection_name,
                    query=query,
                    filters=filters,
                    top_k=vector_top_k,
                )
            except Exception as exc:
                logger.warning("vector retrieval failed: %s", exc)

            try:
                payloads = self.store.scroll_payloads(collection_name=collection_name, filters=filters)
                bm25_results = self.bm25_retriever.search(
                    query=query,
                    chunks=payloads,
                    top_k=bm25_top_k,
                )
            except Exception as exc:
                logger.warning("bm25 retrieval failed: %s", exc)
        else:
            vector_results = self.vector_retriever.search(
                collection_name=collection_name,
                query=query,
                filters=filters,
                top_k=vector_top_k,
            )

        merged = self._prioritize_results(
            self._merge_results(vector_results, bm25_results),
            domain=domain,
        )
        if not settings.enable_reranking:
            logger.warning("RERANKER_DISABLED_USING_HYBRID_RESULTS")
            reranked = merged[:final_top_k]
        else:
            try:
                reranked = self.reranker.rerank(
                    query=query,
                    results=merged,
                    top_k=final_top_k,
                    audit_id=audit_id,
                    document_id=document_id,
                    domain=domain,
                )
            except Exception as exc:
                logger.exception("RERANKER_FAILURE_USING_HYBRID_RESULTS")
                log_pipeline_stage(
                    logger,
                    "RERANKING",
                    audit_id=audit_id,
                    document_id=document_id,
                    domain=domain,
                    started_at=started,
                    status="failed",
                    error=str(exc),
                    fallback="hybrid_results",
                    input_count=len(merged),
                    output_count=min(len(merged), final_top_k),
                )
                reranked = merged[:final_top_k]
        validated = self.validator.validate(reranked)
        log_pipeline_stage(
            logger,
            "RETRIEVAL",
            audit_id=audit_id,
            document_id=document_id,
            domain=domain,
            started_at=started,
            status="completed",
            collection=collection_name,
            filter_keys=sorted((filters or {}).keys()),
            vector_count=len(vector_results),
            bm25_count=len(bm25_results),
            merged_count=len(merged),
            output_count=len(validated),
            reranker_enabled=settings.enable_reranking,
        )
        return validated

    @staticmethod
    def _merge_results(
        vector_results: list[RetrievalResult],
        bm25_results: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        merged: dict[str, RetrievalResult] = {}

        for result in vector_results:
            result.score = max(0.0, min(1.0, result.score))
            merged[result.chunk_id] = result

        for result in bm25_results:
            existing = merged.get(result.chunk_id)
            if existing:
                existing.score = (0.65 * existing.score) + (0.35 * result.score)
                existing.source = "hybrid"
            else:
                result.score = 0.35 * result.score
                merged[result.chunk_id] = result

        return sorted(merged.values(), key=lambda result: result.score, reverse=True)

    @staticmethod
    def _prioritize_results(
        results: list[RetrievalResult],
        *,
        domain: str | None,
    ) -> list[RetrievalResult]:
        deduped: dict[str, RetrievalResult] = {}
        domain_lower = str(domain or "").strip().lower()
        for result in results:
            payload = result.payload or {}
            if domain_lower and str(payload.get("domain") or "").strip().lower() == domain_lower:
                result.score = min(1.0, float(result.score or 0.0) + 0.08)
            if str(payload.get("source_type") or "").strip().lower() == "compliance_rule":
                result.score = min(1.0, float(result.score or 0.0) + 0.02)

            key = HybridRetriever._normalized_clause_key(result.text) or result.chunk_id
            existing = deduped.get(key)
            if existing is None or float(result.score or 0.0) > float(existing.score or 0.0):
                deduped[key] = result
        return sorted(deduped.values(), key=lambda result: result.score, reverse=True)

    @staticmethod
    def _normalized_clause_key(text: str) -> str:
        tokens = [token for token in str(text or "").lower().split() if token]
        return " ".join(tokens[:140])


hybrid_retriever = HybridRetriever()
