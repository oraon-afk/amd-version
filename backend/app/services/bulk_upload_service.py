from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from time import time

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.logging import get_logger, log_pipeline_stage
from backend.app.db.models.batch import BatchDocument, RuleUploadBatch, RuleUploadBatchItem, UploadBatch
from backend.app.db.models.document import UploadedDocument
from backend.app.db.models.rule import RuleDocument
from backend.app.db.models.user import User
from backend.app.db.session import SessionLocal
from backend.app.schemas.audit import CreateAuditRequest
from backend.app.services.audit_service import audit_service
from backend.app.services.document_service import document_service
from backend.app.services.rule_service import rule_service
from backend.app.workers.audit_workflow import audit_workflow


logger = get_logger(__name__)
MAX_BULK_DOCUMENTS = 2000
BULK_READ_CHUNK_SIZE = 1024 * 1024
DEFAULT_MAX_RETRIES = 2


@dataclass(frozen=True)
class RuleBatchFile:
    item_id: str
    filename: str
    content_type: str
    staging_path: str
    file_size_bytes: int


class BulkComplianceUploadService:
    async def create_batch(
        self,
        *,
        db: Session,
        user: User,
        files: list[UploadFile],
        domain: str | None = None,
        domains: list[str] | None = None,
        file_domains: str | None = None,
        rule_set_id: str | None = None,
    ) -> UploadBatch:
        if not files:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload at least one document.")
        if len(files) > MAX_BULK_DOCUMENTS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bulk upload supports up to {MAX_BULK_DOCUMENTS} documents.",
            )
        domain_by_file = _resolve_per_file_domains(
            files=files,
            values=domains,
            fallback=domain,
            file_domains=file_domains,
        )

        started = time()
        batch = UploadBatch(
            user_id=user.id,
            module="compliance_check",
            status="uploading",
            total_documents=len(files),
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)
        log_pipeline_stage(
            logger,
            "BULK_UPLOAD_START",
            audit_id=None,
            document_id=None,
            domain=", ".join(sorted(set(domain_by_file))),
            started_at=started,
            status="started",
            batch_id=batch.id,
            total_documents=len(files),
            rule_set_id=rule_set_id,
        )

        for index, file in enumerate(files, start=1):
            file_started = time()
            filename = file.filename or f"document-{index}"
            title = _title_from_filename(filename, index)
            file_domain = domain_by_file[index - 1]
            try:
                item = BatchDocument(
                    batch_id=batch.id,
                    filename=_safe_queue_filename(filename),
                    content_type=file.content_type or "application/octet-stream",
                    title=title,
                    domain=file_domain,
                    status="queued",
                    max_retries=DEFAULT_MAX_RETRIES,
                )
                db.add(item)
                db.flush()
                staging_path, file_size_bytes = await _stage_upload_file(
                    file=file,
                    batch_id=batch.id,
                    item_id=item.id,
                    filename=filename,
                )
                item.staging_path = staging_path
                item.file_size_bytes = file_size_bytes
                log_pipeline_stage(
                    logger,
                    "BULK_UPLOAD_FILE",
                    audit_id=None,
                    document_id=None,
                    domain=file_domain,
                    started_at=file_started,
                    status="queued",
                    batch_id=batch.id,
                    filename=item.filename,
                    file_size_bytes=file_size_bytes,
                )
            except Exception as exc:
                batch.failed_documents += 1
                batch.processed_documents += 1
                db.add(
                    BatchDocument(
                        batch_id=batch.id,
                        filename=filename,
                        content_type=file.content_type or "application/octet-stream",
                        title=title,
                        domain=file_domain,
                        status="failed",
                        max_retries=DEFAULT_MAX_RETRIES,
                        error_message=str(exc),
                        last_error_at=datetime.utcnow(),
                        completed_at=datetime.utcnow(),
                        processing_time_seconds=round(time() - file_started, 4),
                    ),
                )
                log_pipeline_stage(
                    logger,
                    "BULK_UPLOAD_FAILED",
                    audit_id=None,
                    document_id=None,
                    domain=file_domain,
                    started_at=file_started,
                    status="failed",
                    batch_id=batch.id,
                    filename=filename,
                    error=str(exc),
                )

        batch.status = "queued" if batch.failed_documents < batch.total_documents else "failed"
        if batch.status == "failed":
            batch.completed_at = datetime.utcnow()
            batch.summary_report = _upload_batch_summary(db=db, batch=batch)
        db.commit()
        db.refresh(batch)
        return batch

    def process_batch(self, *, batch_id: str, rule_set_id: str | None = None) -> None:
        with SessionLocal() as db:
            batch = db.get(UploadBatch, batch_id)
            if batch is None:
                logger.warning("Bulk compliance batch disappeared before processing: %s", batch_id)
                return

            batch.status = "processing"
            batch.started_at = batch.started_at or datetime.utcnow()
            db.commit()

            items = list(
                db.scalars(
                    select(BatchDocument)
                    .where(BatchDocument.batch_id == batch_id, BatchDocument.status == "queued")
                    .order_by(BatchDocument.created_at.asc()),
                ),
            )
            if not items:
                self._finalize_batch(db=db, batch=batch)
                return

            user = db.get(User, batch.user_id)
            if user is None:
                batch.status = "failed"
                batch.error_message = "Batch owner was not found."
                batch.completed_at = datetime.utcnow()
                db.commit()
                return

            for item in items:
                self._process_item_with_retries(
                    db=db,
                    batch=batch,
                    item=item,
                    user=user,
                    rule_set_id=rule_set_id,
                )

            self._finalize_batch(db=db, batch=batch)

    def get_batch(self, *, db: Session, user: User, batch_id: str) -> dict:
        batch = db.get(UploadBatch, batch_id)
        if batch is None or (batch.user_id != user.id and not _is_admin(user)):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found.")
        return _upload_batch_payload(db=db, batch=batch)

    @staticmethod
    def _finalize_batch(*, db: Session, batch: UploadBatch) -> None:
        batch.running_document = None
        batch.processed_documents = batch.completed_documents + batch.failed_documents
        if batch.failed_documents and batch.completed_documents:
            batch.status = "completed"
        elif batch.failed_documents >= batch.total_documents:
            batch.status = "failed"
        else:
            batch.status = "completed"
        batch.summary_report = _upload_batch_summary(db=db, batch=batch)
        batch.completed_at = datetime.utcnow()
        db.commit()

    def _process_item_with_retries(
        self,
        *,
        db: Session,
        batch: UploadBatch,
        item: BatchDocument,
        user: User,
        rule_set_id: str | None,
    ) -> None:
        while item.retry_count <= item.max_retries:
            item_started = time()
            document = db.get(UploadedDocument, item.document_id) if item.document_id else None
            batch.running_document = item.filename
            item.status = "processing"
            item.started_at = item.started_at or datetime.utcnow()
            db.commit()
            log_pipeline_stage(
                logger,
                "BULK_UPLOAD_FILE",
                audit_id=item.audit_id,
                document_id=item.document_id,
                domain=item.domain or (document.domain if document else None),
                started_at=item_started,
                status="processing",
                batch_id=batch.id,
                filename=item.filename,
                attempt=item.retry_count + 1,
                max_retries=item.max_retries,
            )
            try:
                document = self._ensure_uploaded_document(db=db, user=user, item=item, document=document)
                audit = audit_service.create_audit(
                    db=db,
                    user=user,
                    payload=CreateAuditRequest(document_id=document.id, rule_set_id=rule_set_id),
                )
                item.audit_id = audit.id
                db.commit()
                audit = audit_workflow.run(db=db, audit_id=audit.id)
                db.refresh(audit)
                if audit.status == "failed":
                    raise RuntimeError(audit.error_message or "Audit workflow failed.")
                item.status = "completed"
                item.error_message = None
                item.completed_at = datetime.utcnow()
                item.processing_time_seconds = round(time() - item_started, 4)
                batch.completed_documents += 1
                batch.processed_documents = batch.completed_documents + batch.failed_documents
                _cleanup_staged_file(item.staging_path)
                log_pipeline_stage(
                    logger,
                    "BULK_UPLOAD_SUCCESS",
                    audit_id=audit.id,
                    document_id=document.id,
                    domain=document.domain,
                    started_at=item_started,
                    status="completed",
                    batch_id=batch.id,
                    filename=item.filename,
                    processing_time=item.processing_time_seconds,
                    attempt=item.retry_count + 1,
                )
                db.commit()
                return
            except Exception as exc:
                db.rollback()
                item.error_message = str(exc)
                item.last_error_at = datetime.utcnow()
                item.processing_time_seconds = round(time() - item_started, 4)
                log_pipeline_stage(
                    logger,
                    "BULK_UPLOAD_RETRY" if item.retry_count < item.max_retries else "BULK_UPLOAD_FAILED",
                    audit_id=item.audit_id,
                    document_id=item.document_id,
                    domain=item.domain or (document.domain if document else None),
                    started_at=item_started,
                    status="retrying" if item.retry_count < item.max_retries else "failed",
                    batch_id=batch.id,
                    filename=item.filename,
                    processing_time=item.processing_time_seconds,
                    attempt=item.retry_count + 1,
                    max_retries=item.max_retries,
                    error=str(exc),
                )
                if item.retry_count < item.max_retries:
                    item.retry_count += 1
                    item.status = "queued"
                    db.commit()
                    continue

                item.status = "failed"
                item.completed_at = datetime.utcnow()
                batch.failed_documents += 1
                batch.processed_documents = batch.completed_documents + batch.failed_documents
                _cleanup_staged_file(item.staging_path)
                db.commit()
                return

    @staticmethod
    def _ensure_uploaded_document(
        *,
        db: Session,
        user: User,
        item: BatchDocument,
        document: UploadedDocument | None,
    ) -> UploadedDocument:
        if document is not None:
            return document
        if not item.staging_path:
            raise RuntimeError("Queued file is missing its staging path.")
        staged_file = Path(item.staging_path)
        if not staged_file.exists():
            raise RuntimeError("Queued file was not found in staging storage.")
        content = staged_file.read_bytes()
        document = document_service.upload_document_bytes(
            db=db,
            user=user,
            title=item.title,
            domain=item.domain or "",
            content=content,
            filename=item.filename,
            content_type=item.content_type or "application/octet-stream",
            source_type="file",
            initial_status="processing",
        )
        item.document_id = document.id
        db.commit()
        return document


class BulkRuleUploadService:
    async def create_batch(
        self,
        *,
        db: Session,
        user: User,
        files: list[UploadFile],
    ) -> tuple[RuleUploadBatch, list[RuleBatchFile]]:
        if not files:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload at least one rule document.")
        if len(files) > MAX_BULK_DOCUMENTS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bulk upload supports up to {MAX_BULK_DOCUMENTS} documents.",
            )

        started = time()
        batch = RuleUploadBatch(
            user_id=user.id,
            module="rule_management",
            status="queued",
            total_documents=len(files),
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)
        log_pipeline_stage(
            logger,
            "BULK_RULE_UPLOAD_START",
            audit_id=None,
            document_id=None,
            domain=None,
            started_at=started,
            status="started",
            batch_id=batch.id,
            total_documents=len(files),
        )

        batch_files: list[RuleBatchFile] = []
        for index, file in enumerate(files, start=1):
            filename = file.filename or f"rule-document-{index}"
            try:
                item = RuleUploadBatchItem(batch_id=batch.id, filename=filename, status="queued")
                item.content_type = file.content_type or "application/octet-stream"
                item.max_retries = DEFAULT_MAX_RETRIES
                db.add(item)
                db.flush()
                staging_path, file_size_bytes = await _stage_upload_file(
                    file=file,
                    batch_id=batch.id,
                    item_id=item.id,
                    filename=filename,
                    namespace="rule-batches",
                )
                item.staging_path = staging_path
                item.file_size_bytes = file_size_bytes
                batch_files.append(
                    RuleBatchFile(
                        item_id=item.id,
                        filename=filename,
                        content_type=file.content_type or "application/octet-stream",
                        staging_path=staging_path,
                        file_size_bytes=file_size_bytes,
                    ),
                )
                log_pipeline_stage(
                    logger,
                    "BULK_RULE_UPLOAD_FILE",
                    audit_id=None,
                    document_id=None,
                    domain=None,
                    started_at=started,
                    status="queued",
                    batch_id=batch.id,
                    filename=filename,
                    file_size_bytes=file_size_bytes,
                )
            except Exception as exc:
                batch.failed_documents += 1
                batch.processed_documents += 1
                db.add(
                    RuleUploadBatchItem(
                        batch_id=batch.id,
                        filename=filename,
                        content_type=file.content_type or "application/octet-stream",
                        status="failed",
                        max_retries=DEFAULT_MAX_RETRIES,
                        error_message=str(exc),
                        last_error_at=datetime.utcnow(),
                        completed_at=datetime.utcnow(),
                    ),
                )
                log_pipeline_stage(
                    logger,
                    "BULK_RULE_UPLOAD_FAILED",
                    audit_id=None,
                    document_id=None,
                    domain=None,
                    started_at=started,
                    status="failed",
                    batch_id=batch.id,
                    filename=filename,
                    error=str(exc),
                )
        db.commit()
        db.refresh(batch)
        return batch, batch_files

    def process_batch(
        self,
        *,
        batch_id: str,
        files: list[RuleBatchFile] | None = None,
        user_id: str,
        rule_set_id: str,
        domain: str | None = None,
        domains: list[str] | None = None,
        category: str | None = None,
        categories: list[str] | None = None,
        jurisdiction: str | None = None,
        document_type: str = "rules",
        version: str = "v1",
    ) -> None:
        with SessionLocal() as db:
            batch = db.get(RuleUploadBatch, batch_id)
            user = db.get(User, user_id)
            if batch is None or user is None:
                logger.warning("Bulk rule batch or user disappeared before processing: %s", batch_id)
                return
            batch.status = "processing"
            batch.started_at = batch.started_at or datetime.utcnow()
            db.commit()

            if files is None:
                queued_items = list(
                    db.scalars(
                        select(RuleUploadBatchItem)
                        .where(RuleUploadBatchItem.batch_id == batch_id, RuleUploadBatchItem.status == "queued")
                        .order_by(RuleUploadBatchItem.created_at.asc()),
                    ),
                )
                files = [
                    RuleBatchFile(
                        item_id=item.id,
                        filename=item.filename,
                        content_type=item.content_type,
                        staging_path=item.staging_path or "",
                        file_size_bytes=item.file_size_bytes,
                    )
                    for item in queued_items
                ]

            for index, batch_file in enumerate(files):
                item = db.get(RuleUploadBatchItem, batch_file.item_id)
                if item is None:
                    continue
                file_domain = _value_at(domains, index) or domain
                file_category = _value_at(categories, index) or category
                self._process_rule_item_with_retries(
                    db=db,
                    batch=batch,
                    item=item,
                    batch_file=batch_file,
                    user=user,
                    rule_set_id=rule_set_id,
                    file_domain=file_domain,
                    file_category=file_category,
                    jurisdiction=jurisdiction,
                    document_type=document_type,
                    version=version,
                )

            self._finalize_batch(db=db, batch=batch)

    def _process_rule_item_with_retries(
        self,
        *,
        db: Session,
        batch: RuleUploadBatch,
        item: RuleUploadBatchItem,
        batch_file: RuleBatchFile,
        user: User,
        rule_set_id: str,
        file_domain: str | None,
        file_category: str | None,
        jurisdiction: str | None,
        document_type: str,
        version: str,
    ) -> None:
        while item.retry_count <= item.max_retries:
            item_started = time()
            batch.running_document = batch_file.filename
            item.status = "processing"
            item.started_at = item.started_at or datetime.utcnow()
            db.commit()
            log_pipeline_stage(
                logger,
                "BULK_RULE_UPLOAD_FILE",
                audit_id=None,
                document_id=None,
                domain=file_domain or file_category,
                started_at=item_started,
                status="processing",
                batch_id=batch.id,
                filename=batch_file.filename,
                attempt=item.retry_count + 1,
                max_retries=item.max_retries,
            )
            try:
                if not batch_file.staging_path:
                    raise RuntimeError("Queued rule file is missing its staging path.")
                staged_file = Path(batch_file.staging_path)
                if not staged_file.exists():
                    raise RuntimeError("Queued rule file was not found in staging storage.")
                content = staged_file.read_bytes()
                rule_document = rule_service.upload_and_index_rule_bytes(
                        db=db,
                        user=user,
                        content=content,
                        filename=batch_file.filename,
                        content_type=batch_file.content_type,
                        rule_set_id=rule_set_id,
                        domain=file_domain,
                        category=file_category,
                        jurisdiction=jurisdiction,
                        document_type=document_type,
                        version=version,
                )
                item.rule_document_id = rule_document.id
                item.status = "completed"
                item.error_message = None
                item.completed_at = datetime.utcnow()
                item.processing_time_seconds = round(time() - item_started, 4)
                batch.completed_documents += 1
                batch.processed_documents = batch.completed_documents + batch.failed_documents
                _cleanup_staged_file(item.staging_path)
                log_pipeline_stage(
                    logger,
                    "BULK_RULE_UPLOAD_SUCCESS",
                    audit_id=None,
                    document_id=rule_document.id,
                    domain=rule_document.domain,
                    started_at=item_started,
                    status="completed",
                    batch_id=batch.id,
                    filename=batch_file.filename,
                    processing_time=item.processing_time_seconds,
                    attempt=item.retry_count + 1,
                )
                db.commit()
                return
            except Exception as exc:
                db.rollback()
                item.error_message = str(exc)
                item.last_error_at = datetime.utcnow()
                item.processing_time_seconds = round(time() - item_started, 4)
                log_pipeline_stage(
                    logger,
                    "BULK_RULE_UPLOAD_RETRY" if item.retry_count < item.max_retries else "BULK_RULE_UPLOAD_FAILED",
                    audit_id=None,
                    document_id=None,
                    domain=file_domain or file_category,
                    started_at=item_started,
                    status="retrying" if item.retry_count < item.max_retries else "failed",
                    batch_id=batch.id,
                    filename=batch_file.filename,
                    processing_time=item.processing_time_seconds,
                    attempt=item.retry_count + 1,
                    max_retries=item.max_retries,
                    error=str(exc),
                )
                if item.retry_count < item.max_retries:
                    item.retry_count += 1
                    item.status = "queued"
                    db.commit()
                    continue
                item.status = "failed"
                item.completed_at = datetime.utcnow()
                batch.failed_documents += 1
                batch.processed_documents = batch.completed_documents + batch.failed_documents
                _cleanup_staged_file(item.staging_path)
                db.commit()
                return

    def get_batch(self, *, db: Session, batch_id: str) -> dict:
        batch = db.get(RuleUploadBatch, batch_id)
        if batch is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule batch not found.")
        return _rule_batch_payload(db=db, batch=batch)

    @staticmethod
    def _finalize_batch(*, db: Session, batch: RuleUploadBatch) -> None:
        batch.running_document = None
        batch.processed_documents = batch.completed_documents + batch.failed_documents
        if batch.failed_documents and batch.completed_documents:
            batch.status = "completed"
        elif batch.failed_documents >= batch.total_documents:
            batch.status = "failed"
        else:
            batch.status = "completed"
        batch.summary_report = _rule_batch_summary(db=db, batch=batch)
        batch.completed_at = datetime.utcnow()
        db.commit()


def _upload_batch_payload(*, db: Session, batch: UploadBatch) -> dict:
    items = list(
        db.scalars(
            select(BatchDocument)
            .where(BatchDocument.batch_id == batch.id)
            .order_by(BatchDocument.created_at.asc()),
        ),
    )
    documents = {
        document.id: document
        for document in db.scalars(
            select(UploadedDocument).where(
                UploadedDocument.id.in_([item.document_id for item in items if item.document_id]),
            ),
        )
    } if items else {}
    return {
        "id": batch.id,
        "user_id": batch.user_id,
        "module": batch.module,
        "status": batch.status,
        "total_documents": batch.total_documents,
        "completed_documents": batch.completed_documents,
        "failed_documents": batch.failed_documents,
        "processed_documents": batch.completed_documents + batch.failed_documents,
        "pending_documents": max(batch.total_documents - (batch.completed_documents + batch.failed_documents), 0),
        "progress_label": f"Processed {batch.completed_documents + batch.failed_documents} / {batch.total_documents}",
        "running_document": batch.running_document,
        "error_message": batch.error_message,
        "summary_report": batch.summary_report,
        "started_at": batch.started_at,
        "completed_at": batch.completed_at,
        "created_at": batch.created_at,
        "documents": [
            {
                "id": item.id,
                "batch_id": item.batch_id,
                "document_id": item.document_id,
                "audit_id": item.audit_id,
                "filename": item.filename,
                "content_type": item.content_type,
                "file_size_bytes": item.file_size_bytes,
                "title": item.title,
                "domain": item.domain or (documents.get(item.document_id or "").domain if item.document_id in documents else None),
                "queue_position": index,
                "status": _current_batch_status(item=item, document=documents.get(item.document_id or "")),
                "current_stage": documents.get(item.document_id or "").processing_stage if item.document_id in documents else item.status,
                "retry_count": item.retry_count,
                "max_retries": item.max_retries,
                "error_message": item.error_message,
                "processing_time_seconds": item.processing_time_seconds,
                "started_at": item.started_at,
                "completed_at": item.completed_at,
                "created_at": item.created_at,
            }
            for index, item in enumerate(items, start=1)
        ],
    }


def _rule_batch_payload(*, db: Session, batch: RuleUploadBatch) -> dict:
    items = list(
        db.scalars(
            select(RuleUploadBatchItem)
            .where(RuleUploadBatchItem.batch_id == batch.id)
            .order_by(RuleUploadBatchItem.created_at.asc()),
        ),
    )
    return {
        "id": batch.id,
        "user_id": batch.user_id,
        "module": batch.module,
        "status": batch.status,
        "total_documents": batch.total_documents,
        "completed_documents": batch.completed_documents,
        "failed_documents": batch.failed_documents,
        "processed_documents": batch.completed_documents + batch.failed_documents,
        "pending_documents": max(batch.total_documents - (batch.completed_documents + batch.failed_documents), 0),
        "progress_label": f"Processed {batch.completed_documents + batch.failed_documents} / {batch.total_documents}",
        "running_document": batch.running_document,
        "error_message": batch.error_message,
        "summary_report": batch.summary_report,
        "started_at": batch.started_at,
        "completed_at": batch.completed_at,
        "created_at": batch.created_at,
        "documents": [
            {
                "id": item.id,
                "batch_id": item.batch_id,
                "rule_document_id": item.rule_document_id,
                "filename": item.filename,
                "content_type": item.content_type,
                "file_size_bytes": item.file_size_bytes,
                "status": item.status,
                "retry_count": item.retry_count,
                "max_retries": item.max_retries,
                "error_message": item.error_message,
                "processing_time_seconds": item.processing_time_seconds,
                "started_at": item.started_at,
                "completed_at": item.completed_at,
                "created_at": item.created_at,
            }
            for item in items
        ],
    }


def _upload_batch_summary(*, db: Session, batch: UploadBatch) -> dict:
    items = list(
        db.scalars(
            select(BatchDocument)
            .where(BatchDocument.batch_id == batch.id)
            .order_by(BatchDocument.created_at.asc()),
        ),
    )
    return {
        "batch_id": batch.id,
        "module": batch.module,
        "status": batch.status,
        "generated_at": datetime.utcnow().isoformat(),
        "total_documents": batch.total_documents,
        "processed_documents": batch.completed_documents + batch.failed_documents,
        "completed_documents": batch.completed_documents,
        "failed_documents": batch.failed_documents,
        "documents": [
            {
                "filename": item.filename,
                "document_id": item.document_id,
                "audit_id": item.audit_id,
                "domain": item.domain,
                "status": item.status,
                "retry_count": item.retry_count,
                "error_message": item.error_message,
                "processing_time_seconds": item.processing_time_seconds,
            }
            for item in items
        ],
    }


def _rule_batch_summary(*, db: Session, batch: RuleUploadBatch) -> dict:
    items = list(
        db.scalars(
            select(RuleUploadBatchItem)
            .where(RuleUploadBatchItem.batch_id == batch.id)
            .order_by(RuleUploadBatchItem.created_at.asc()),
        ),
    )
    return {
        "batch_id": batch.id,
        "module": batch.module,
        "status": batch.status,
        "generated_at": datetime.utcnow().isoformat(),
        "total_documents": batch.total_documents,
        "processed_documents": batch.completed_documents + batch.failed_documents,
        "completed_documents": batch.completed_documents,
        "failed_documents": batch.failed_documents,
        "documents": [
            {
                "filename": item.filename,
                "rule_document_id": item.rule_document_id,
                "status": item.status,
                "retry_count": item.retry_count,
                "error_message": item.error_message,
                "processing_time_seconds": item.processing_time_seconds,
            }
            for item in items
        ],
    }


def _current_batch_status(*, item: BatchDocument, document: UploadedDocument | None) -> str:
    return item.status


def _title_from_filename(filename: str, index: int) -> str:
    title = Path(filename).name.replace("\\", "_").replace("/", "_")
    title = title.rsplit(".", 1)[0].strip()
    return title or f"Document {index}"


def _safe_queue_filename(filename: str) -> str:
    name = Path(filename).name.strip().replace("\\", "_").replace("/", "_")
    return name or "queued-document"


async def _stage_upload_file(
    *,
    file: UploadFile,
    batch_id: str,
    item_id: str,
    filename: str,
    namespace: str = "compliance-batches",
) -> tuple[str, int]:
    safe_filename = _safe_queue_filename(filename)
    staging_dir = Path(settings.storage_root) / "queue" / namespace / batch_id
    staging_dir.mkdir(parents=True, exist_ok=True)
    staging_path = staging_dir / f"{item_id}-{safe_filename}"
    total_bytes = 0
    with staging_path.open("wb") as output:
        while True:
            chunk = await file.read(BULK_READ_CHUNK_SIZE)
            if not chunk:
                break
            total_bytes += len(chunk)
            output.write(chunk)
    return str(staging_path), total_bytes


def _cleanup_staged_file(staging_path: str | None) -> None:
    if not staging_path:
        return
    try:
        path = Path(staging_path)
        queue_root = (Path(settings.storage_root) / "queue").resolve()
        resolved = path.resolve()
        if queue_root not in resolved.parents:
            logger.warning("Skipped staged file cleanup outside queue root: %s", staging_path)
            return
        if resolved.exists():
            resolved.unlink()
    except Exception:
        logger.warning("Failed to clean staged bulk upload file: %s", staging_path, exc_info=True)


def _resolve_per_file_values(
    *,
    values: list[str] | None,
    fallback: str | None,
    total: int,
    field_name: str,
) -> list[str]:
    cleaned_values = [value.strip() for value in values or [] if value and value.strip()]
    cleaned_fallback = fallback.strip() if fallback and fallback.strip() else None
    if cleaned_values:
        if len(cleaned_values) != total:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Provide one {field_name} value for each uploaded file.",
            )
        return cleaned_values
    if cleaned_fallback:
        return [cleaned_fallback] * total
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Select a {field_name} for every uploaded file.",
    )


def _resolve_per_file_domains(
    *,
    files: list[UploadFile],
    values: list[str] | None,
    fallback: str | None,
    file_domains: str | None,
) -> list[str]:
    mapped_domains = _decode_file_domain_values(files=files, file_domains=file_domains)
    return _resolve_per_file_values(
        values=mapped_domains or values,
        fallback=fallback,
        total=len(files),
        field_name="domain",
    )


def _decode_file_domain_values(*, files: list[UploadFile], file_domains: str | None) -> list[str] | None:
    if not file_domains or not file_domains.strip():
        return None
    try:
        rows = json.loads(file_domains)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file_domains payload.") from exc
    if not isinstance(rows, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="file_domains must be a list.")
    if len(rows) != len(files):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide one domain mapping for each uploaded file.")

    domains: list[str] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Each file domain mapping must be an object.")
        filename = _string_value(row.get("file") or row.get("filename"))
        upload_filename = files[index].filename or f"document-{index + 1}"
        if filename and filename != upload_filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="file_domains order must match the uploaded files.",
            )
        domains.append(_string_value(row.get("domain")))
    return domains


def _string_value(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _value_at(values: list[str] | None, index: int) -> str | None:
    if not values or index >= len(values):
        return None
    value = values[index].strip()
    return value or None


def _is_admin(user: User) -> bool:
    return (user.role or "").upper() == "ADMIN"


bulk_compliance_upload_service = BulkComplianceUploadService()
bulk_rule_upload_service = BulkRuleUploadService()
