from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from time import time

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

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
MAX_BULK_DOCUMENTS = 100


@dataclass(frozen=True)
class RuleBatchFile:
    item_id: str
    filename: str
    content_type: str
    content: bytes


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
                content = await file.read()
                document = document_service.upload_document_bytes(
                    db=db,
                    user=user,
                    title=title,
                    domain=file_domain,
                    content=content,
                    filename=filename,
                    content_type=file.content_type or "application/octet-stream",
                    source_type="file",
                    initial_status="queued",
                )
                item = BatchDocument(
                    batch_id=batch.id,
                    document_id=document.id,
                    filename=document.filename,
                    title=document.title,
                    domain=file_domain,
                    status="queued",
                )
                db.add(item)
                log_pipeline_stage(
                    logger,
                    "BULK_UPLOAD_FILE",
                    audit_id=None,
                    document_id=document.id,
                    domain=file_domain,
                    started_at=file_started,
                    status="queued",
                    batch_id=batch.id,
                    filename=document.filename,
                )
            except Exception as exc:
                batch.failed_documents += 1
                db.add(
                    BatchDocument(
                        batch_id=batch.id,
                        filename=filename,
                        title=title,
                        domain=file_domain,
                        status="failed",
                        error_message=str(exc),
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
                item_started = time()
                document = db.get(UploadedDocument, item.document_id) if item.document_id else None
                batch.running_document = item.filename
                item.status = "processing"
                item.started_at = datetime.utcnow()
                db.commit()
                log_pipeline_stage(
                    logger,
                    "BULK_UPLOAD_FILE",
                    audit_id=None,
                    document_id=item.document_id,
                    domain=document.domain if document else None,
                    started_at=item_started,
                    status="processing",
                    batch_id=batch.id,
                    filename=item.filename,
                )

                try:
                    if document is None:
                        raise RuntimeError("Uploaded document metadata was not found.")
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
                    item.completed_at = datetime.utcnow()
                    item.processing_time_seconds = round(time() - item_started, 4)
                    batch.completed_documents += 1
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
                    )
                except Exception as exc:
                    item.status = "failed"
                    item.error_message = str(exc)
                    item.completed_at = datetime.utcnow()
                    item.processing_time_seconds = round(time() - item_started, 4)
                    batch.failed_documents += 1
                    log_pipeline_stage(
                        logger,
                        "BULK_UPLOAD_FAILED",
                        audit_id=item.audit_id,
                        document_id=item.document_id,
                        domain=document.domain if document else None,
                        started_at=item_started,
                        status="failed",
                        batch_id=batch.id,
                        filename=item.filename,
                        processing_time=item.processing_time_seconds,
                        error=str(exc),
                    )
                finally:
                    db.commit()

            self._finalize_batch(db=db, batch=batch)

    def get_batch(self, *, db: Session, user: User, batch_id: str) -> dict:
        batch = db.get(UploadBatch, batch_id)
        if batch is None or (batch.user_id != user.id and not _is_admin(user)):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found.")
        return _upload_batch_payload(db=db, batch=batch)

    @staticmethod
    def _finalize_batch(*, db: Session, batch: UploadBatch) -> None:
        batch.running_document = None
        if batch.failed_documents and batch.completed_documents:
            batch.status = "completed_with_failures"
        elif batch.failed_documents >= batch.total_documents:
            batch.status = "failed"
        else:
            batch.status = "completed"
        batch.completed_at = datetime.utcnow()
        db.commit()


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
                db.add(item)
                db.flush()
                batch_files.append(
                    RuleBatchFile(
                        item_id=item.id,
                        filename=filename,
                        content_type=file.content_type or "application/octet-stream",
                        content=await file.read(),
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
                )
            except Exception as exc:
                batch.failed_documents += 1
                db.add(
                    RuleUploadBatchItem(
                        batch_id=batch.id,
                        filename=filename,
                        status="failed",
                        error_message=str(exc),
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
        files: list[RuleBatchFile],
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

            for index, batch_file in enumerate(files):
                item_started = time()
                item = db.get(RuleUploadBatchItem, batch_file.item_id)
                if item is None:
                    continue
                file_domain = _value_at(domains, index) or domain
                file_category = _value_at(categories, index) or category
                batch.running_document = batch_file.filename
                item.status = "processing"
                item.started_at = datetime.utcnow()
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
                )
                try:
                    rule_document = rule_service.upload_and_index_rule_bytes(
                        db=db,
                        user=user,
                        content=batch_file.content,
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
                    item.completed_at = datetime.utcnow()
                    item.processing_time_seconds = round(time() - item_started, 4)
                    batch.completed_documents += 1
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
                    )
                except Exception as exc:
                    item.status = "failed"
                    item.error_message = str(exc)
                    item.completed_at = datetime.utcnow()
                    item.processing_time_seconds = round(time() - item_started, 4)
                    batch.failed_documents += 1
                    log_pipeline_stage(
                        logger,
                        "BULK_RULE_UPLOAD_FAILED",
                        audit_id=None,
                        document_id=None,
                        domain=file_domain or file_category,
                        started_at=item_started,
                        status="failed",
                        batch_id=batch.id,
                        filename=batch_file.filename,
                        processing_time=item.processing_time_seconds,
                        error=str(exc),
                    )
                finally:
                    db.commit()

            self._finalize_batch(db=db, batch=batch)

    def get_batch(self, *, db: Session, batch_id: str) -> dict:
        batch = db.get(RuleUploadBatch, batch_id)
        if batch is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule batch not found.")
        return _rule_batch_payload(db=db, batch=batch)

    @staticmethod
    def _finalize_batch(*, db: Session, batch: RuleUploadBatch) -> None:
        batch.running_document = None
        if batch.failed_documents and batch.completed_documents:
            batch.status = "completed_with_failures"
        elif batch.failed_documents >= batch.total_documents:
            batch.status = "failed"
        else:
            batch.status = "completed"
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
        "running_document": batch.running_document,
        "error_message": batch.error_message,
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
                "title": item.title,
                "domain": item.domain or (documents.get(item.document_id or "").domain if item.document_id in documents else None),
                "queue_position": index,
                "status": _current_batch_status(item=item, document=documents.get(item.document_id or "")),
                "current_stage": documents.get(item.document_id or "").processing_stage if item.document_id in documents else item.status,
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
        "running_document": batch.running_document,
        "error_message": batch.error_message,
        "started_at": batch.started_at,
        "completed_at": batch.completed_at,
        "created_at": batch.created_at,
        "documents": [
            {
                "id": item.id,
                "batch_id": item.batch_id,
                "rule_document_id": item.rule_document_id,
                "filename": item.filename,
                "status": item.status,
                "error_message": item.error_message,
                "processing_time_seconds": item.processing_time_seconds,
                "started_at": item.started_at,
                "completed_at": item.completed_at,
                "created_at": item.created_at,
            }
            for item in items
        ],
    }


def _current_batch_status(*, item: BatchDocument, document: UploadedDocument | None) -> str:
    if item.status in {"completed", "failed"}:
        return item.status
    if document and document.processing_stage not in {"uploaded", "queued"}:
        return document.processing_stage
    return item.status


def _title_from_filename(filename: str, index: int) -> str:
    title = Path(filename).name.replace("\\", "_").replace("/", "_")
    title = title.rsplit(".", 1)[0].strip()
    return title or f"Document {index}"


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
