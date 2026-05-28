from __future__ import annotations

from dataclasses import dataclass
from time import time

from sqlalchemy import delete
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.logging import get_logger, log_pipeline_stage
from backend.app.db.models.audit import AuditRun
from backend.app.db.models.document import DocumentChunk, UploadedDocument
from backend.app.db.transactions import commit_or_rollback
from backend.app.rag.indexing.embeddings import EmbeddingService, embedding_service
from backend.app.rag.indexing.qdrant_store import QdrantStore, qdrant_store
from backend.app.rag.ingestion.chunker import chunk_pages
from backend.app.rag.ingestion.pdf_parser import parse_document_bytes
from backend.app.storage.s3_client import s3_storage

logger = get_logger(__name__)


@dataclass
class ProcessedDocument:
    document: UploadedDocument
    pages: list[dict]
    chunks: list[dict]
    full_text: str


class DocumentAgent:
    def __init__(
        self,
        *,
        store: QdrantStore = qdrant_store,
        embeddings: EmbeddingService = embedding_service,
    ) -> None:
        self.store = store
        self.embeddings = embeddings

    def process_upload(
        self,
        *,
        db: Session,
        document: UploadedDocument,
        audit_id: str | None = None,
    ) -> ProcessedDocument:
        self._mark_stage(db=db, document=document, audit_id=audit_id, stage="extracting")

        stage_started = time()
        try:
            content = s3_storage.read_uri_bytes(document.s3_uri)
            pages = parse_document_bytes(
                content=content,
                filename=document.filename,
                content_type=document.content_type,
            )
            full_text = "\n\n".join(page["text"] for page in pages)
            if not full_text.strip():
                raise ValueError("Document extraction produced no readable text.")
        except Exception as exc:
            log_pipeline_stage(
                logger,
                "EXTRACTION",
                audit_id=audit_id,
                document_id=document.id,
                domain=document.domain,
                started_at=stage_started,
                status="failed",
                error=str(exc),
            )
            raise
        log_pipeline_stage(
            logger,
            "EXTRACTION",
            audit_id=audit_id,
            document_id=document.id,
            domain=document.domain,
            started_at=stage_started,
            status="completed",
            page_count=len(pages),
            text_chars=len(full_text),
        )

        self._mark_stage(db=db, document=document, audit_id=audit_id, stage="chunking")
        stage_started = time()
        try:
            chunks = chunk_pages(
                pages=pages,
                document_id=document.id,
                filename=document.filename,
                source_type="uploaded_document",
                extra_metadata={
                    "title": document.title,
                    "domain": document.domain,
                    "role_type": document.role_type,
                    "user_id": document.user_id,
                    "uploaded_by": document.user_id,
                    "source": document.s3_key or document.s3_uri,
                    "audit_id": audit_id,
                    "expires_at": document.expires_at.isoformat(),
                },
            )
            if not chunks:
                raise ValueError("Document chunking produced no chunks.")
        except Exception as exc:
            log_pipeline_stage(
                logger,
                "CHUNKING",
                audit_id=audit_id,
                document_id=document.id,
                domain=document.domain,
                started_at=stage_started,
                status="failed",
                error=str(exc),
            )
            raise
        log_pipeline_stage(
            logger,
            "CHUNKING",
            audit_id=audit_id,
            document_id=document.id,
            domain=document.domain,
            started_at=stage_started,
            status="completed",
            chunk_count=len(chunks),
        )

        document.extracted_text = full_text
        self._mark_stage(db=db, document=document, audit_id=audit_id, stage="embedding")

        stage_started = time()
        try:
            embeddings = self.embeddings.embed_texts([chunk["text"] for chunk in chunks])
        except Exception as exc:
            log_pipeline_stage(
                logger,
                "EMBEDDING",
                audit_id=audit_id,
                document_id=document.id,
                domain=document.domain,
                started_at=stage_started,
                status="failed",
                chunk_count=len(chunks),
                embedding_model=self.embeddings.model_name,
                error=str(exc),
            )
            raise
        log_pipeline_stage(
            logger,
            "EMBEDDING",
            audit_id=audit_id,
            document_id=document.id,
            domain=document.domain,
            started_at=stage_started,
            status="completed",
            chunk_count=len(chunks),
            embedding_model=self.embeddings.model_name,
        )

        stage_started = time()
        try:
            vector_ids = self.store.upsert_chunks(
                collection_name=settings.qdrant_upload_collection,
                chunks=chunks,
                embeddings=embeddings,
            )
            if len(vector_ids) != len(chunks):
                raise RuntimeError(
                    f"Qdrant upsert returned {len(vector_ids)} IDs for {len(chunks)} chunks.",
                )
        except Exception as exc:
            log_pipeline_stage(
                logger,
                "QDRANT_UPSERT",
                audit_id=audit_id,
                document_id=document.id,
                domain=document.domain,
                started_at=stage_started,
                status="failed",
                collection=settings.qdrant_upload_collection,
                point_count=len(chunks),
                error=str(exc),
            )
            raise
        for chunk, vector_id in zip(chunks, vector_ids, strict=True):
            chunk["qdrant_point_id"] = vector_id
        log_pipeline_stage(
            logger,
            "QDRANT_UPSERT",
            audit_id=audit_id,
            document_id=document.id,
            domain=document.domain,
            started_at=stage_started,
            status="completed",
            collection=settings.qdrant_upload_collection,
            point_count=len(vector_ids),
        )

        db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
        for index, (chunk, vector_id) in enumerate(zip(chunks, vector_ids, strict=True)):
            db.add(
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=index,
                    chunk_text=chunk["text"],
                    embedding_model=self.embeddings.model_name,
                    vector_id=vector_id,
                ),
            )

        commit_or_rollback(db)
        return ProcessedDocument(document=document, pages=pages, chunks=chunks, full_text=full_text)

    @staticmethod
    def _mark_stage(
        *,
        db: Session,
        document: UploadedDocument,
        audit_id: str | None,
        stage: str,
    ) -> None:
        document.upload_status = stage
        document.status = stage
        document.processing_stage = stage
        if audit_id:
            audit = db.get(AuditRun, audit_id)
            if audit is not None:
                audit.status = stage
        commit_or_rollback(db)


document_agent = DocumentAgent()
