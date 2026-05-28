from __future__ import annotations

import math
from threading import Lock
from time import time

from backend.app.core.config import settings
from backend.app.core.logging import get_logger, log_pipeline_stage
from backend.app.rag.retrieval.types import RetrievalResult

logger = get_logger(__name__)

GLOBAL_RERANKER_MODEL = None
GLOBAL_RERANKER_MODEL_NAME: str | None = None
GLOBAL_RERANKER_MODEL_FAILED: set[str] = set()
GLOBAL_RERANKER_MODEL_LOCK = Lock()


class Reranker:
    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.reranker_model
        self._model = None
        self._model_failed = False
        self._model_lock = Lock()

    @property
    def model(self):
        if self._model is None and not self._model_failed:
            with GLOBAL_RERANKER_MODEL_LOCK:
                global GLOBAL_RERANKER_MODEL, GLOBAL_RERANKER_MODEL_NAME
                if GLOBAL_RERANKER_MODEL is not None and GLOBAL_RERANKER_MODEL_NAME == self.model_name:
                    self._model = GLOBAL_RERANKER_MODEL
                    return self._model
                if self.model_name in GLOBAL_RERANKER_MODEL_FAILED:
                    self._model_failed = True
                    return None
            with self._model_lock:
                if self._model is not None or self._model_failed:
                    return self._model
                try:
                    from sentence_transformers import CrossEncoder

                    self._model = CrossEncoder(self.model_name)
                    with GLOBAL_RERANKER_MODEL_LOCK:
                        GLOBAL_RERANKER_MODEL = self._model
                        GLOBAL_RERANKER_MODEL_NAME = self.model_name
                    logger.info("reranker.model_loaded model=%s", self.model_name)
                except Exception as exc:
                    self._model_failed = True
                    self._model = None
                    with GLOBAL_RERANKER_MODEL_LOCK:
                        GLOBAL_RERANKER_MODEL_FAILED.add(self.model_name)
                    logger.warning("reranker.model_load_failed model=%s error=%s", self.model_name, exc)
        return self._model

    def preload(self) -> bool:
        if not settings.enable_reranking:
            logger.warning("RERANKER_DISABLED_USING_HYBRID_RESULTS")
            return False
        try:
            return self.model is not None
        except Exception as exc:
            logger.exception("reranker.preload_failed model=%s error=%s", self.model_name, exc)
            return False

    def rerank(
        self,
        *,
        query: str,
        results: list[RetrievalResult],
        top_k: int,
        audit_id: str | None = None,
        document_id: str | None = None,
        domain: str | None = None,
    ) -> list[RetrievalResult]:
        started = time()
        if not results:
            log_pipeline_stage(
                logger,
                "RERANKING",
                audit_id=audit_id,
                document_id=document_id,
                domain=domain,
                started_at=started,
                status="skipped",
                input_count=0,
                output_count=0,
            )
            return []

        if not settings.enable_reranking:
            logger.warning("RERANKER_DISABLED_USING_HYBRID_RESULTS")
            return sorted(results, key=lambda result: result.score, reverse=True)[:top_k]

        try:
            model = self.model
        except Exception as exc:
            logger.exception("reranker.model_access_failed model=%s error=%s", self.model_name, exc)
            model = None

        if model is not None:
            try:
                pairs = [(query, result.text) for result in results]
                scores = self._normalize_cross_encoder_scores(model.predict(pairs))
                for result, score in zip(results, scores, strict=True):
                    result.score = float(score)
                    result.payload["rerank_score"] = float(score)
                reranked = sorted(results, key=lambda result: result.score, reverse=True)[:top_k]
                log_pipeline_stage(
                    logger,
                    "RERANKING",
                    audit_id=audit_id,
                    document_id=document_id,
                    domain=domain,
                    started_at=started,
                    status="completed",
                    input_count=len(results),
                    output_count=len(reranked),
                    model=self.model_name,
                )
                return reranked
            except Exception as exc:
                self._model_failed = True
                with GLOBAL_RERANKER_MODEL_LOCK:
                    GLOBAL_RERANKER_MODEL_FAILED.add(self.model_name)
                logger.exception("reranker.predict_failed model=%s error=%s", self.model_name, exc)
                log_pipeline_stage(
                    logger,
                    "RERANKING",
                    audit_id=audit_id,
                    document_id=document_id,
                    domain=domain,
                    started_at=started,
                    status="failed",
                    input_count=len(results),
                    output_count=min(len(results), top_k),
                    model=self.model_name,
                    error=str(exc),
                    fallback="hybrid_results",
                )

        reranked = sorted(results, key=lambda result: result.score, reverse=True)[:top_k]
        log_pipeline_stage(
            logger,
            "RERANKING",
            audit_id=audit_id,
            document_id=document_id,
            domain=domain,
            started_at=started,
            status="fallback",
            input_count=len(results),
            output_count=len(reranked),
            model="hybrid_results",
        )
        return reranked

    @staticmethod
    def _normalize_cross_encoder_scores(scores) -> list[float]:
        numeric_scores = []
        for score in scores:
            try:
                value = float(score)
            except (TypeError, ValueError):
                value = 0.0
            if not math.isfinite(value):
                value = 0.0
            numeric_scores.append(value)
        if any(score < 0.0 or score > 1.0 for score in numeric_scores):
            return [
                max(0.0, min(1.0, 1.0 / (1.0 + math.exp(-max(-15.0, min(15.0, score))))))
                for score in numeric_scores
            ]
        return [max(0.0, min(1.0, score)) for score in numeric_scores]


reranker = Reranker()
