from __future__ import annotations

import asyncio
from threading import Lock

from backend.app.core.config import settings

GLOBAL_EMBEDDING_MODEL = None
GLOBAL_EMBEDDING_MODEL_NAME: str | None = None
GLOBAL_EMBEDDING_MODEL_LOCK = Lock()


class EmbeddingService:
    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.embedding_model
        self._model = None
        self._model_lock = Lock()

    @property
    def model(self):
        if self._model is None:
            with GLOBAL_EMBEDDING_MODEL_LOCK:
                global GLOBAL_EMBEDDING_MODEL, GLOBAL_EMBEDDING_MODEL_NAME
                if GLOBAL_EMBEDDING_MODEL is not None and GLOBAL_EMBEDDING_MODEL_NAME == self.model_name:
                    self._model = GLOBAL_EMBEDDING_MODEL
                    return self._model
            with self._model_lock:
                if self._model is None:
                    from sentence_transformers import SentenceTransformer

                    self._model = SentenceTransformer(self.model_name)
                    with GLOBAL_EMBEDDING_MODEL_LOCK:
                        GLOBAL_EMBEDDING_MODEL = self._model
                        GLOBAL_EMBEDDING_MODEL_NAME = self.model_name
        return self._model

    def preload(self) -> bool:
        _ = self.model
        return True

    def dimensions(self) -> int:
        return len(self.embed_query("embedding warmup"))

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self.model.encode(
            texts,
            batch_size=settings.embedding_batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [vector.tolist() for vector in vectors]

    async def embed_texts_async(self, texts: list[str]) -> list[list[float]]:
        return await asyncio.to_thread(self.embed_texts, texts)

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]


embedding_service = EmbeddingService()
