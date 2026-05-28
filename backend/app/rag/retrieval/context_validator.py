from __future__ import annotations

from backend.app.core.config import settings
from backend.app.rag.retrieval.types import RetrievalResult


class ContextValidator:
    def validate(self, results: list[RetrievalResult]) -> list[RetrievalResult]:
        if not settings.enable_context_validation:
            return results

        validated = []
        for result in results:
            if len(result.text.split()) < 20:
                continue
            if result.score < settings.semantic_similarity_threshold:
                continue
            validated.append(result)
        return validated

    def has_enough_context(self, results: list[RetrievalResult]) -> bool:
        if not results:
            return False
        best_score = max(result.score for result in results)
        return best_score >= max(settings.min_confidence_threshold * 0.5, 0.25)


context_validator = ContextValidator()
