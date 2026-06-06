from datetime import datetime, timedelta
from hashlib import sha256
import logging
from pathlib import Path
from time import time
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.logging import get_logger, log_once, log_pipeline_stage
from backend.app.db.models.document import ComplianceDomain, DocumentRecord, UploadedDocument
from backend.app.db.models.user import User
from backend.app.db.session import database_error_root_cause, recover_from_database_error
from backend.app.services.audit_log_service import audit_log_service
from backend.app.storage.s3_client import s3_storage
from backend.app.utils.file_validation import validate_upload_file


def _safe_filename(filename: str) -> str:
    name = Path(filename).name.strip().replace("\\", "_").replace("/", "_")
    return name or "uploaded-document"


class DocumentService:
    async def upload_document(
        self,
        *,
        db: Session,
        user: User,
        title: str,
        domain: str,
        file: UploadFile | None = None,
        raw_text: str | None = None,
    ) -> UploadedDocument:
        title = title.strip()
        domain = _normalize_domain(domain)
        if not title:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Document title is required.")
        if not domain:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Document domain is required.")

        source_type = "text" if raw_text and raw_text.strip() else "file"
        if source_type == "text":
            content = raw_text.strip().encode("utf-8")
            filename = _safe_filename(f"{title}.txt")
            content_type = "text/plain"
        else:
            if file is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload a file or paste raw text.")
            content = await file.read()
            filename = _safe_filename(file.filename or "uploaded-document")
            content_type = file.content_type or "application/octet-stream"

        return self.upload_document_bytes(
            db=db,
            user=user,
            title=title,
            domain=domain,
            content=content,
            filename=filename,
            content_type=content_type,
            source_type=source_type,
        )

    def upload_document_bytes(
        self,
        *,
        db: Session,
        user: User,
        title: str,
        domain: str,
        content: bytes,
        filename: str,
        content_type: str,
        source_type: str = "file",
        initial_status: str = "uploaded",
    ) -> UploadedDocument:
        title = title.strip()
        domain = _normalize_domain(domain)
        filename = _safe_filename(filename)
        content_type = content_type or "application/octet-stream"
        source_type = source_type or "file"
        if not title:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Document title is required.")
        if not domain:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Document domain is required.")
        validate_upload_file(filename=filename, content_type=content_type, content=content)

        role_type = user.role.upper()
        document_id = str(uuid4())
        prefix = settings.s3_temp_upload_prefix.strip("/")
        key = f"{prefix}/{user.id}/{document_id}/{filename}"
        metadata = {
            "uploaded-by": str(user.id),
            "role-type": role_type,
            "domain": domain,
            "source-type": source_type,
            "module": "compliance_check",
        }
        metadata["retention-hours"] = str(settings.temp_document_retention_hours)
        try:
            upload_started = time()
            uploaded = s3_storage.upload_bytes(
                bucket=settings.upload_bucket,
                key=key,
                content=content,
                content_type=content_type,
                metadata=metadata,
                expires_at=datetime.utcnow() + timedelta(hours=settings.temp_document_retention_hours),
            )
            log_pipeline_stage(
                logger,
                "UPLOAD",
                audit_id=None,
                document_id=document_id,
                domain=domain,
                started_at=upload_started,
                status="completed",
                bucket=settings.upload_bucket,
                key=uploaded.key,
                source_type=source_type,
            )
        except Exception as exc:
            log_pipeline_stage(
                logger,
                "UPLOAD",
                audit_id=None,
                document_id=document_id,
                domain=domain,
                started_at=upload_started,
                status="failed",
                source_type=source_type,
                error=str(exc),
            )
            log_once(
                logger,
                logging.WARNING,
                "document_s3_upload_failed",
                "DOCUMENT_S3_UPLOAD_FAILED user_id=%s filename=%s root_cause=%s",
                user.id,
                filename,
                exc,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"S3 document storage failed: {exc}",
            ) from exc

        expires_at = datetime.utcnow() + timedelta(hours=settings.temp_document_retention_hours)
        document = UploadedDocument(
            id=document_id,
            user_id=user.id,
            title=title,
            domain=domain,
            role_type=role_type,
            source_type=source_type,
            s3_key=uploaded.key,
            qdrant_collection=settings.qdrant_upload_collection,
            upload_status=initial_status,
            processing_stage=initial_status,
            cleanup_status="scheduled",
            file_name=filename,
            file_type=content_type,
            filename=filename,
            content_type=content_type,
            s3_uri=uploaded.uri,
            sha256=sha256(content).hexdigest(),
            status=initial_status,
            expires_at=expires_at,
        )
        try:
            db_started = time()
            db.add(document)
            db.add(
                DocumentRecord(
                    id=document.id,
                    user_id=document.user_id,
                    filename=document.filename,
                    s3_path=document.s3_uri,
                    upload_time=document.created_at,
                    expiry_time=document.expires_at,
                    status=document.status,
                    document_type=document.source_type,
                    title=document.title,
                    domain=document.domain,
                    role_type=document.role_type,
                    source_type=document.source_type,
                    file_name=document.file_name,
                    file_type=document.file_type,
                    s3_key=document.s3_key,
                    qdrant_collection=document.qdrant_collection,
                    upload_status=document.upload_status,
                    processing_stage=document.processing_stage,
                    created_at=document.created_at,
                ),
            )
            db.commit()
            db.refresh(document)
            log_pipeline_stage(
                logger,
                "DB_WRITE",
                audit_id=None,
                document_id=document.id,
                domain=document.domain,
                started_at=db_started,
                status="completed",
                table="uploaded_documents,documents",
            )
            audit_log_service.log(
                db=db,
                user=user,
                action="document.uploaded",
                entity_type="uploaded_document",
                entity_id=document.id,
                metadata={"filename": filename, "domain": domain, "source_type": source_type},
            )
        except SQLAlchemyError as exc:
            db.rollback()
            recover_from_database_error(exc)
            log_once(
                logger,
                logging.WARNING,
                "document_metadata_database_unavailable",
                "DOCUMENT_METADATA_DATABASE_UNAVAILABLE user_id=%s filename=%s root_cause=%s",
                user.id,
                filename,
                database_error_root_cause(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database failed to save uploaded document metadata.",
            ) from exc
        return document

    def list_documents(self, *, db: Session, user: User) -> list[UploadedDocument]:
        return list(
            db.scalars(
                select(UploadedDocument)
                .where(UploadedDocument.user_id == user.id)
                .order_by(UploadedDocument.created_at.desc()),
            ),
        )

    def list_domains(self, *, db: Session) -> list[ComplianceDomain]:
        return list(db.scalars(select(ComplianceDomain).order_by(ComplianceDomain.name.asc())))


def _normalize_domain(domain: str) -> str:
    return domain.strip().lower().replace("_", "-")


logger = get_logger(__name__)
document_service = DocumentService()
