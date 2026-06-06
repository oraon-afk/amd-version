from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from backend.app.db.models.rule import ComplianceRule, RuleDocument
from backend.app.db.models.user import User
from backend.app.rag.indexing.embeddings import embedding_service
from backend.app.rag.indexing.qdrant_store import qdrant_store
from backend.app.rag.ingestion.chunker import chunk_pages
from backend.app.rag.ingestion.pdf_parser import parse_document_bytes
from backend.app.services.audit_log_service import audit_log_service
from backend.app.storage.s3_client import s3_storage
from backend.app.utils.file_validation import validate_upload_file


def _safe_filename(filename: str) -> str:
    name = Path(filename).name.strip().replace("\\", "_").replace("/", "_")
    return name or "rule-document"


class RuleService:
    async def upload_and_index_rule(
        self,
        *,
        db: Session,
        user: User,
        file: UploadFile,
        rule_set_id: str,
        domain: str | None = None,
        category: str | None = None,
        jurisdiction: str | None = None,
        document_type: str = "rules",
        version: str = "v1",
    ) -> RuleDocument:
        return self.upload_and_index_rule_bytes(
            db=db,
            user=user,
            content=await file.read(),
            filename=file.filename or "rule-document",
            content_type=file.content_type or "application/octet-stream",
            rule_set_id=rule_set_id,
            domain=domain,
            category=category,
            jurisdiction=jurisdiction,
            document_type=document_type,
            version=version,
        )

    def upload_and_index_rule_bytes(
        self,
        *,
        db: Session,
        user: User,
        content: bytes,
        filename: str,
        content_type: str,
        rule_set_id: str,
        domain: str | None = None,
        category: str | None = None,
        jurisdiction: str | None = None,
        document_type: str = "rules",
        version: str = "v1",
    ) -> RuleDocument:
        filename = _safe_filename(filename or "rule-document")
        content_type = content_type or "application/octet-stream"
        validate_upload_file(filename=filename, content_type=content_type, content=content)

        rule_document_id = str(uuid4())
        normalized_domain = _normalize_domain(domain or category or "legal")
        category = _normalize_category(category or normalized_domain)
        document_type = (document_type or "rules").strip().lower()
        version = (version or "v1").strip()
        key = f"{settings.s3_rule_prefix.strip('/')}/{user.id}/{rule_document_id}/{filename}"
        try:
            uploaded = s3_storage.upload_bytes(
                bucket=settings.rule_bucket,
                key=key,
                content=content,
                content_type=content_type,
                metadata={
                    "uploaded-by": str(user.id),
                    "role-type": user.role.upper(),
                    "domain": normalized_domain,
                    "document-type": document_type,
                    "rule-set-id": rule_set_id,
                    "version": version,
                },
            )
        except Exception as exc:
            logger.exception("S3 rule upload failed for user %s and file %s", user.id, filename)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Permanent rule storage failed in S3: {exc}",
            ) from exc

        rule_document = RuleDocument(
            id=rule_document_id,
            user_id=user.id,
            rule_set_id=rule_set_id,
            domain=normalized_domain,
            category=category,
            jurisdiction=jurisdiction,
            document_type=document_type,
            version=version,
            filename=filename,
            content_type=content_type,
            s3_uri=uploaded.uri,
            storage_path=uploaded.key,
            sha256=sha256(content).hexdigest(),
            status="indexing",
        )
        try:
            db.add(rule_document)
            db.commit()
            db.refresh(rule_document)
        except SQLAlchemyError as exc:
            db.rollback()
            logger.exception("Rule document metadata insert failed for user %s and file %s", user.id, filename)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database failed to save rule document metadata.",
            ) from exc

        pages = parse_document_bytes(content=content, filename=filename, content_type=content_type)
        full_text = "\n\n".join(page["text"] for page in pages).strip()
        if not full_text:
            rule_document.status = "failed"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rule document did not contain readable text.",
            )
        chunks = chunk_pages(
            pages=pages,
            document_id=rule_document.id,
            filename=filename,
            source_type="compliance_rule",
            extra_metadata={
                "rule_document_id": rule_document.id,
                "rule_set_id": rule_set_id,
                "domain": normalized_domain,
                "category": category,
                "jurisdiction": jurisdiction,
                "uploaded_by": user.id,
                "upload_date": datetime.utcnow().isoformat(),
                "document_type": document_type,
                "version": version,
                "source": uploaded.uri,
                "role_type": "ADMIN",
            },
        )
        embeddings = embedding_service.embed_texts([chunk["text"] for chunk in chunks])
        try:
            qdrant_store.upsert_chunks(
                collection_name=settings.qdrant_rule_collection,
                chunks=chunks,
                embeddings=embeddings,
            )
        except Exception as exc:
            rule_document.status = "failed"
            db.commit()
            logger.exception("Qdrant rule indexing failed for rule document %s", rule_document.id)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Qdrant indexing failed: {exc}",
            ) from exc

        rule_document.status = "indexed"
        rule_document.indexed_at = datetime.utcnow()
        db.add(
            ComplianceRule(
                rule_document_id=rule_document.id,
                category=category,
                title=Path(filename).stem[:255],
                description=f"Imported from {filename}",
                rule_text=full_text,
                reference=filename,
                version=version,
                created_by=user.id,
            ),
        )
        db.commit()
        db.refresh(rule_document)
        audit_log_service.log(
            db=db,
            user=user,
            action="rule_document.uploaded",
            entity_type="rule_document",
            entity_id=rule_document.id,
            metadata={"category": category, "document_type": document_type, "version": version},
        )
        return rule_document


def _normalize_category(category: str) -> str:
    cleaned = category.strip()
    if not cleaned:
        return "Internal Policies"
    allowed_by_lower = {item.lower(): item for item in settings.rule_category_list}
    return allowed_by_lower.get(cleaned.lower(), cleaned)


def _normalize_domain(domain: str) -> str:
    return domain.strip().lower().replace("_", "-")


logger = get_logger(__name__)
rule_service = RuleService()
