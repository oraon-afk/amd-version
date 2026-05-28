from __future__ import annotations

import re
from functools import lru_cache

from backend.app.rag.retrieval.types import RetrievalResult


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


class BM25Retriever:
    def search(
        self,
        *,
        query: str,
        chunks: list[dict],
        top_k: int = 8,
    ) -> list[RetrievalResult]:
        if not chunks:
            return []

        corpus = [tokenize(str(chunk.get("text", ""))) for chunk in chunks]
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        bm25 = self._build_bm25(tuple(tuple(tokens) for tokens in corpus))
        bm25_scores = bm25.get_scores(query_tokens)
        query_set = set(query_tokens)
        scores = []
        for index, raw_score in enumerate(bm25_scores):
            token_set = set(corpus[index])
            overlap = len(query_set & token_set) / max(len(query_set), 1)
            scores.append(float(raw_score) + overlap)

        ranked = sorted(enumerate(scores), key=lambda item: float(item[1]), reverse=True)[:top_k]
        max_score = max((float(score) for _, score in ranked), default=1.0) or 1.0

        results = []
        for index, score in ranked:
            if score <= 0:
                continue
            chunk = chunks[index]
            results.append(
                RetrievalResult(
                    chunk_id=str(chunk.get("chunk_id", chunk.get("_point_id", index))),
                    text=str(chunk.get("text", "")),
                    score=float(score) / max_score,
                    source="bm25",
                    payload=chunk,
                    point_id=chunk.get("_point_id"),
                ),
            )
        return results

    @staticmethod
    @lru_cache(maxsize=32)
    def _build_bm25(corpus: tuple[tuple[str, ...], ...]):
        from rank_bm25 import BM25Okapi

        return BM25Okapi([list(tokens) for tokens in corpus])
