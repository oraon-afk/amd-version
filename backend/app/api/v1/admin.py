from __future__ import annotations

from datetime import datetime
from time import time
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from qdrant_client.models import FieldCondition, Filter, MatchValue
from sqlalchemy import delete, false, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.auth.auth_dependencies import require_admin
from backend.app.core.config import settings
from backend.app.core.logging import get_logger, log_pipeline_stage
from backend.app.db.models.audit import (
    AuditReport,
    AuditResult,
    AuditRun,
    EvidenceLink,
    Finding,
    ReportRecord,
)
from backend.app.db.models.batch import BatchDocument
from backend.app.db.models.document import ComplianceDomain, DocumentChunk, DocumentRecord, UploadedDocument
from backend.app.db.models.log import AuditLog
from backend.app.db.models.rule import ComplianceRule, RuleDocument
from backend.app.db.models.user import User
from backend.app.db.session import get_db
from backend.app.rag.indexing.embeddings import embedding_service
from backend.app.rag.indexing.qdrant_store import qdrant_store
from backend.app.schemas.document import DocumentResponse
from backend.app.schemas.rule import RuleUploadBatchResponse
from backend.app.services.audit_log_service import audit_log_service
from backend.app.services.bulk_upload_service import bulk_rule_upload_service
from backend.app.services.document_service import document_service
from backend.app.services.rule_service import rule_service
from backend.app.storage.s3_client import s3_storage

router = APIRouter(prefix="/admin", tags=["admin"])
logger = get_logger(__name__)


class ComplianceRuleCreate(BaseModel):
    category: str = Field(min_length=2, max_length=100)
    title: str = Field(min_length=2, max_length=255)
    description: str | None = None
    rule_text: str = Field(min_length=5)
    reference: str | None = None
    version: str = "v1"


class RuleCategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = None


@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[dict[str, Any]]:
    users = db.scalars(select(User).order_by(User.created_at.desc())).all()
    return [_user_payload(user) for user in users]


@router.get("/documents")
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, list[dict[str, Any]]]:
    uploaded = db.scalars(select(UploadedDocument).order_by(UploadedDocument.created_at.desc())).all()
    rules = db.scalars(select(RuleDocument).order_by(RuleDocument.created_at.desc())).all()
    return {
        "uploaded_documents": [_uploaded_document_payload(item) for item in uploaded],
        "rule_documents": [_rule_document_payload(item) for item in rules],
    }


@router.post("/rules/upload")
async def upload_rule_document(
    file: UploadFile = File(...),
    rule_set_id: str = Form(default="default"),
    category: str = Form(default="Internal Policies"),
    jurisdiction: str | None = Form(default=None),
    document_type: str = Form(default="rules"),
    version: str = Form(default="v1"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    rule = await rule_service.upload_and_index_rule(
        db=db,
        user=current_user,
        file=file,
        rule_set_id=rule_set_id,
        category=category,
        jurisdiction=jurisdiction,
        document_type=document_type,
        version=version,
    )
    return _rule_document_payload(rule)


@router.post("/rules/bulk-upload", response_model=RuleUploadBatchResponse)
async def bulk_upload_rule_documents(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    rule_set_id: str = Form(default="default"),
    domain: str | None = Form(default=None),
    domains: list[str] | None = Form(default=None),
    category: str = Form(default="Internal Policies"),
    categories: list[str] | None = Form(default=None),
    jurisdiction: str | None = Form(default=None),
    document_type: str = Form(default="rules"),
    version: str = Form(default="v1"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> RuleUploadBatchResponse:
    batch, batch_files = await bulk_rule_upload_service.create_batch(
        db=db,
        user=current_user,
        files=files,
    )
    if batch_files:
        background_tasks.add_task(
            bulk_rule_upload_service.process_batch,
            batch_id=batch.id,
            files=batch_files,
            user_id=current_user.id,
            rule_set_id=rule_set_id,
            domain=domain,
            domains=domains,
            category=category,
            categories=categories,
            jurisdiction=jurisdiction,
            document_type=document_type,
            version=version,
        )
    return bulk_rule_upload_service.get_batch(db=db, batch_id=batch.id)


@router.get("/rule-batches/{batch_id}", response_model=RuleUploadBatchResponse)
def get_rule_upload_batch(
    batch_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> RuleUploadBatchResponse:
    return bulk_rule_upload_service.get_batch(db=db, batch_id=batch_id)


@router.post("/documents/upload", response_model=DocumentResponse)
async def upload_admin_document(
    title: str = Form(...),
    domain: str = Form(...),
    file: UploadFile | None = File(default=None),
    raw_text: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> UploadedDocument:
    started = time()
    upload_filename = file.filename if file is not None else f"{title}.txt"
    log_pipeline_stage(
        logger,
        "ADMIN_UPLOAD_START",
        audit_id=None,
        document_id=None,
        domain=domain,
        started_at=started,
        status="started",
        admin_user_id=current_user.id,
        upload_filename=upload_filename,
    )
    try:
        document = await document_service.upload_document(
            db=db,
            user=current_user,
            title=title,
            domain=domain,
            file=file,
            raw_text=raw_text,
        )
    except Exception as exc:
        log_pipeline_stage(
            logger,
            "ADMIN_UPLOAD_FAILED",
            audit_id=None,
            document_id=None,
            domain=domain,
            started_at=started,
            status="failed",
            admin_user_id=current_user.id,
            upload_filename=upload_filename,
            error=str(exc),
        )
        raise

    log_pipeline_stage(
        logger,
        "ADMIN_UPLOAD_SUCCESS",
        audit_id=None,
        document_id=document.id,
        domain=document.domain,
        started_at=started,
        status="completed",
        admin_user_id=current_user.id,
        upload_filename=document.filename,
    )
    return document


@router.delete("/document/{document_id}")
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    started = time()
    log_pipeline_stage(
        logger,
        "ADMIN_DELETE_START",
        audit_id=None,
        document_id=document_id,
        domain=None,
        started_at=started,
        status="started",
        admin_user_id=current_user.id,
    )
    uploaded = db.scalar(select(UploadedDocument).where(UploadedDocument.id == document_id))
    if uploaded is not None:
        return _delete_uploaded_document(
            db=db,
            current_user=current_user,
            document=uploaded,
            started_at=started,
        )

    rule = db.scalar(select(RuleDocument).where(RuleDocument.id == document_id))
    if rule is not None:
        try:
            s3_storage.delete_uri(rule.s3_uri)
            db.execute(delete(ComplianceRule).where(ComplianceRule.rule_document_id == rule.id))
            db.delete(rule)
            db.commit()
        except Exception as exc:
            db.rollback()
            log_pipeline_stage(
                logger,
                "ADMIN_DELETE_FAILED",
                audit_id=None,
                document_id=document_id,
                domain=rule.domain,
                started_at=started,
                status="failed",
                admin_user_id=current_user.id,
                upload_filename=rule.filename,
                error=str(exc),
            )
            raise
        audit_log_service.log(
            db=db,
            user=current_user,
            action="admin.document.deleted",
            entity_type="rule_document",
            entity_id=document_id,
        )
        log_pipeline_stage(
            logger,
            "ADMIN_DELETE_SUCCESS",
            audit_id=None,
            document_id=document_id,
            domain=rule.domain,
            started_at=started,
            status="completed",
            admin_user_id=current_user.id,
            deleted_audit_count=0,
            deleted_findings_count=0,
            upload_filename=rule.filename,
        )
        return {"status": "deleted", "id": document_id}

    log_pipeline_stage(
        logger,
        "ADMIN_DELETE_FAILED",
        audit_id=None,
        document_id=document_id,
        domain=None,
        started_at=started,
        status="not_found",
        admin_user_id=current_user.id,
        deleted_audit_count=0,
        deleted_findings_count=0,
    )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")


@router.get("/audit-reports")
def list_audit_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[dict[str, Any]]:
    reports = db.scalars(select(AuditReport).order_by(AuditReport.created_at.desc())).all()
    audits = {
        audit.id: audit
        for audit in db.scalars(select(AuditRun).where(AuditRun.id.in_([report.audit_id for report in reports]))).all()
    } if reports else {}
    return [_report_payload(report, audits.get(report.audit_id)) for report in reports]


@router.delete("/audits/{audit_id}")
def delete_audit(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    started = time()
    audit = db.scalar(select(AuditRun).where(AuditRun.id == audit_id))
    if audit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found.")

    audit_document_id = audit.document_id
    audit_user_id = audit.user_id
    audit_reports = list(db.scalars(select(AuditReport).where(AuditReport.audit_id == audit.id)))
    report_records = list(db.scalars(select(ReportRecord).where(ReportRecord.audit_id == audit.id)))
    finding_ids = list(db.scalars(select(Finding.id).where(Finding.audit_id == audit.id)))
    s3_uris: set[str] = set()
    for report in audit_reports:
        _add_s3_uri(s3_uris, report.report_json_s3_uri)
        _collect_s3_uris_from_value(s3_uris, report.report_payload)
    for report in report_records:
        _add_s3_uri(s3_uris, report.report_path)
        _add_s3_uri(s3_uris, report.report_json_s3_uri)
        _collect_s3_uris_from_value(s3_uris, report.report_payload)

    try:
        deleted_s3_objects_count = 0
        for uri in sorted(s3_uris):
            if s3_storage.delete_uri(uri):
                deleted_s3_objects_count += 1
        deleted_s3_objects_count += _delete_s3_prefix(
            bucket=settings.report_bucket,
            prefix=_s3_prefix(settings.s3_report_prefix, audit_user_id, audit.id),
        )

        evidence_count = _rowcount(
            db.execute(
                delete(EvidenceLink).where(
                    EvidenceLink.finding_id.in_(finding_ids) if finding_ids else false(),
                ),
            ),
        )
        findings_count = _rowcount(db.execute(delete(Finding).where(Finding.audit_id == audit.id)))
        audit_reports_count = _rowcount(db.execute(delete(AuditReport).where(AuditReport.audit_id == audit.id)))
        reports_count = _rowcount(db.execute(delete(ReportRecord).where(ReportRecord.audit_id == audit.id)))
        db.execute(update(BatchDocument).where(BatchDocument.audit_id == audit.id).values(audit_id=None))
        db.delete(audit)
        db.commit()
    except Exception as exc:
        db.rollback()
        log_pipeline_stage(
            logger,
            "ADMIN_AUDIT_DELETE_FAILED",
            audit_id=audit_id,
            document_id=audit_document_id,
            domain=None,
            started_at=started,
            status="failed",
            admin_user_id=current_user.id,
            error=str(exc),
        )
        raise

    audit_log_service.log(
        db=db,
        user=current_user,
        action="admin.audit.deleted",
        entity_type="audit_run",
        entity_id=audit_id,
        metadata={
            "deleted_findings_count": findings_count,
            "deleted_evidence_count": evidence_count,
            "deleted_audit_reports_count": audit_reports_count,
            "deleted_reports_count": reports_count,
            "deleted_s3_objects_count": deleted_s3_objects_count,
        },
    )
    log_pipeline_stage(
        logger,
        "ADMIN_AUDIT_DELETE_SUCCESS",
        audit_id=audit_id,
        document_id=audit_document_id,
        domain=None,
        started_at=started,
        status="completed",
        admin_user_id=current_user.id,
        deleted_findings_count=findings_count,
        deleted_evidence_count=evidence_count,
        deleted_audit_reports_count=audit_reports_count,
        deleted_reports_count=reports_count,
        deleted_s3_objects_count=deleted_s3_objects_count,
    )
    return {
        "status": "deleted",
        "id": audit_id,
        "deleted_findings_count": findings_count,
        "deleted_evidence_count": evidence_count,
        "deleted_audit_reports_count": audit_reports_count,
        "deleted_reports_count": reports_count,
    }


@router.get("/compliance-rules")
def list_compliance_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[dict[str, Any]]:
    rules = db.scalars(select(ComplianceRule).order_by(ComplianceRule.created_at.desc())).all()
    return [_compliance_rule_payload(rule) for rule in rules]


@router.post("/compliance-rules")
def create_compliance_rule(
    payload: ComplianceRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    rule = ComplianceRule(
        category=payload.category,
        title=payload.title,
        description=payload.description,
        rule_text=payload.rule_text,
        reference=payload.reference,
        version=payload.version,
        created_by=current_user.id,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    qdrant_store.upsert_chunks(
        collection_name=settings.qdrant_rule_collection,
        chunks=[
            {
                "chunk_id": f"manual-rule:{rule.id}",
                "document_id": rule.id,
                "source_type": "compliance_rule",
                "domain": payload.category.strip().lower().replace("_", "-"),
                "category": payload.category,
                "section": payload.title,
                "section_title": payload.title,
                "text": payload.rule_text,
                "citation_label": payload.reference or payload.title,
                "source": "manual_compliance_rule",
                "role_type": "ADMIN",
                "uploaded_by": current_user.id,
            },
        ],
        embeddings=embedding_service.embed_texts([payload.rule_text]),
    )
    audit_log_service.log(
        db=db,
        user=current_user,
        action="admin.compliance_rule.created",
        entity_type="compliance_rule",
        entity_id=rule.id,
        metadata={"category": rule.category},
    )
    return _compliance_rule_payload(rule)


@router.get("/rule-categories")
def list_rule_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[dict[str, str | None]]:
    existing = db.scalars(select(ComplianceDomain).order_by(ComplianceDomain.name.asc())).all()
    return [{"id": item.id, "name": item.name, "description": item.description} for item in existing]


@router.post("/rule-categories")
def create_rule_category(
    payload: RuleCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, str | None]:
    existing = db.scalar(select(ComplianceDomain).where(func.lower(ComplianceDomain.name) == payload.name.lower()))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category already exists.")
    category = ComplianceDomain(name=payload.name, description=payload.description)
    db.add(category)
    db.commit()
    db.refresh(category)
    audit_log_service.log(
        db=db,
        user=current_user,
        action="admin.rule_category.created",
        entity_type="compliance_domain",
        entity_id=category.id,
        metadata={"name": category.name},
    )
    return {"id": category.id, "name": category.name, "description": category.description}


@router.get("/analytics")
def analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    users = db.scalar(select(func.count()).select_from(User)) or 0
    uploads = db.scalar(select(func.count()).select_from(UploadedDocument)) or 0
    rule_docs = db.scalar(select(func.count()).select_from(RuleDocument)) or 0
    audits = db.scalar(select(func.count()).select_from(AuditRun)) or 0
    completed = db.scalar(select(func.count()).select_from(AuditRun).where(AuditRun.status == "completed")) or 0
    failed = db.scalar(select(func.count()).select_from(AuditRun).where(AuditRun.status == "failed")) or 0
    high_risk = db.scalar(select(func.count()).select_from(AuditRun).where(AuditRun.overall_risk == "HIGH")) or 0
    return {
        "users": users,
        "uploaded_documents": uploads,
        "rule_documents": rule_docs,
        "audits": audits,
        "completed_audits": completed,
        "failed_audits": failed,
        "high_risk_audits": high_risk,
        "storage": _s3_storage_summary(),
    }


@router.get("/logs")
def system_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[dict[str, Any]]:
    logs = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(200)).all()
    return [_log_payload(log) for log in logs]


@router.get("/storage")
def storage_monitoring(current_user: User = Depends(require_admin)) -> dict[str, Any]:
    return {
        "bucket": settings.s3_bucket,
        "retention_hours": settings.temp_document_retention_hours,
        "areas": _s3_storage_summary(),
    }


@router.get("/qdrant")
def qdrant_monitoring(current_user: User = Depends(require_admin)) -> dict[str, Any]:
    try:
        collections = qdrant_store.client.get_collections().collections
        items = []
        for collection in collections:
            detail = qdrant_store.client.get_collection(collection.name)
            items.append(
                {
                    "name": collection.name,
                    "points_count": getattr(detail, "points_count", None),
                    "vectors_count": getattr(detail, "vectors_count", None),
                    "is_rule_collection": collection.name == settings.qdrant_rule_collection,
                    "is_upload_collection": collection.name == settings.qdrant_upload_collection,
                },
            )
        return {
            "status": "connected",
            "rule_collection": settings.qdrant_rule_collection,
            "upload_collection": settings.qdrant_upload_collection,
            "collections": items,
        }
    except Exception as exc:
        return {
            "status": "unavailable",
            "rule_collection": settings.qdrant_rule_collection,
            "upload_collection": settings.qdrant_upload_collection,
            "error": str(exc),
            "collections": [],
        }


def _delete_uploaded_document(
    *,
    db: Session,
    current_user: User,
    document: UploadedDocument,
    started_at: float,
) -> dict[str, Any]:
    audit_runs = list(db.scalars(select(AuditRun).where(AuditRun.document_id == document.id)))
    audit_ids = [audit.id for audit in audit_runs]
    finding_ids = list(
        db.scalars(
            select(Finding.id).where(
                _any_condition(
                    Finding.audit_id.in_(audit_ids) if audit_ids else None,
                    Finding.document_id == document.id,
                ),
            ),
        ),
    )
    audit_result_ids = list(
        db.scalars(select(AuditResult.id).where(AuditResult.document_id == document.id)),
    )
    audit_reports = list(
        db.scalars(
            select(AuditReport).where(
                AuditReport.audit_id.in_(audit_ids) if audit_ids else false(),
            ),
        ),
    )
    report_records = list(
        db.scalars(
            select(ReportRecord).where(
                _any_condition(
                    ReportRecord.audit_id.in_(audit_ids) if audit_ids else None,
                    ReportRecord.audit_result_id.in_(audit_result_ids) if audit_result_ids else None,
                ),
            ),
        ),
    )
    report_record_ids = [report.id for report in report_records]
    s3_uris = _document_s3_uris(
        document=document,
        audit_reports=audit_reports,
        report_records=report_records,
    )

    try:
        evidence_count = _rowcount(
            db.execute(
                delete(EvidenceLink).where(
                    _any_condition(
                        EvidenceLink.finding_id.in_(finding_ids) if finding_ids else None,
                        EvidenceLink.document_id == document.id,
                    ),
                ),
            ),
        )
        findings_count = _rowcount(
            db.execute(
                delete(Finding).where(
                    _any_condition(
                        Finding.audit_id.in_(audit_ids) if audit_ids else None,
                        Finding.document_id == document.id,
                    ),
                ),
            ),
        )
        audit_reports_count = _rowcount(
            db.execute(
                delete(AuditReport).where(AuditReport.audit_id.in_(audit_ids) if audit_ids else false()),
            ),
        )
        if audit_result_ids:
            db.execute(
                update(ReportRecord)
                .where(ReportRecord.audit_result_id.in_(audit_result_ids))
                .values(audit_result_id=None),
            )
        audit_results_count = _rowcount(
            db.execute(
                delete(AuditResult).where(AuditResult.id.in_(audit_result_ids) if audit_result_ids else false()),
            ),
        )
        reports_count = _rowcount(
            db.execute(
                delete(ReportRecord).where(
                    _any_condition(
                        ReportRecord.id.in_(report_record_ids) if report_record_ids else None,
                        ReportRecord.audit_id.in_(audit_ids) if audit_ids else None,
                    ),
                ),
            ),
        )
        audit_runs_count = _rowcount(
            db.execute(delete(AuditRun).where(AuditRun.id.in_(audit_ids) if audit_ids else false())),
        )
        document_chunks_count = _rowcount(
            db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id)),
        )
        document_records_count = _rowcount(
            db.execute(delete(DocumentRecord).where(DocumentRecord.id == document.id)),
        )

        log_pipeline_stage(
            logger,
            "ADMIN_DELETE_DB",
            audit_id=None,
            document_id=document.id,
            domain=document.domain,
            started_at=started_at,
            status="dependencies_deleted",
            admin_user_id=current_user.id,
            deleted_audit_count=audit_runs_count,
            deleted_findings_count=findings_count,
            deleted_evidence_count=evidence_count,
            deleted_audit_reports_count=audit_reports_count,
            deleted_audit_results_count=audit_results_count,
            deleted_reports_count=reports_count,
            deleted_document_chunks_count=document_chunks_count,
            deleted_document_records_count=document_records_count,
            upload_filename=document.filename,
        )

        qdrant_points_count = _delete_qdrant_document_chunks(
            document_id=document.id,
            admin_user_id=current_user.id,
            domain=document.domain,
            started_at=started_at,
        )
        s3_objects_count = _delete_s3_document_artifacts(
            document=document,
            audit_runs=audit_runs,
            s3_uris=s3_uris,
            admin_user_id=current_user.id,
            started_at=started_at,
        )

        db.delete(document)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        log_pipeline_stage(
            logger,
            "ADMIN_DELETE_FAILED",
            audit_id=None,
            document_id=document.id,
            domain=document.domain,
            started_at=started_at,
            status="conflict",
            admin_user_id=current_user.id,
            deleted_audit_count=len(audit_ids),
            deleted_findings_count=len(finding_ids),
            upload_filename=document.filename,
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document cannot be deleted because dependent audit records still exist.",
        ) from exc
    except Exception as exc:
        db.rollback()
        log_pipeline_stage(
            logger,
            "ADMIN_DELETE_FAILED",
            audit_id=None,
            document_id=document.id,
            domain=document.domain,
            started_at=started_at,
            status="failed",
            admin_user_id=current_user.id,
            deleted_audit_count=len(audit_ids),
            deleted_findings_count=len(finding_ids),
            upload_filename=document.filename,
            error=str(exc),
        )
        logger.exception("Admin document delete failed for document %s", document.id)
        raise

    audit_log_service.log(
        db=db,
        user=current_user,
        action="admin.document.deleted",
        entity_type="uploaded_document",
        entity_id=document.id,
        metadata={
            "deleted_audit_count": audit_runs_count,
            "deleted_findings_count": findings_count,
            "deleted_qdrant_points_count": qdrant_points_count,
            "deleted_s3_objects_count": s3_objects_count,
        },
    )
    log_pipeline_stage(
        logger,
        "ADMIN_DELETE_SUCCESS",
        audit_id=None,
        document_id=document.id,
        domain=document.domain,
        started_at=started_at,
        status="completed",
        admin_user_id=current_user.id,
        deleted_audit_count=audit_runs_count,
        deleted_findings_count=findings_count,
        upload_filename=document.filename,
    )
    return {
        "status": "deleted",
        "id": document.id,
        "deleted_audit_count": audit_runs_count,
        "deleted_findings_count": findings_count,
        "deleted_qdrant_points_count": qdrant_points_count,
        "deleted_s3_objects_count": s3_objects_count,
    }


def _delete_qdrant_document_chunks(
    *,
    document_id: str,
    admin_user_id: str,
    domain: str | None,
    started_at: float,
) -> int:
    try:
        filters = {"document_id": document_id}
        existing_points = qdrant_store.scroll_payloads(
            collection_name=settings.qdrant_upload_collection,
            filters=filters,
        )
        qdrant_store.client.delete(
            collection_name=settings.qdrant_upload_collection,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id),
                    ),
                ],
            ),
            wait=True,
        )
    except Exception as exc:
        log_pipeline_stage(
            logger,
            "ADMIN_DELETE_QDRANT",
            audit_id=None,
            document_id=document_id,
            domain=domain,
            started_at=started_at,
            status="failed",
            admin_user_id=admin_user_id,
            collection=settings.qdrant_upload_collection,
            error=str(exc),
        )
        raise

    log_pipeline_stage(
        logger,
        "ADMIN_DELETE_QDRANT",
        audit_id=None,
        document_id=document_id,
        domain=domain,
        started_at=started_at,
        status="completed",
        admin_user_id=admin_user_id,
        collection=settings.qdrant_upload_collection,
        deleted_qdrant_points_count=len(existing_points),
    )
    return len(existing_points)


def _delete_s3_document_artifacts(
    *,
    document: UploadedDocument,
    audit_runs: list[AuditRun],
    s3_uris: set[str],
    admin_user_id: str,
    started_at: float,
) -> int:
    try:
        deleted_count = 0
        for uri in sorted(s3_uris):
            if s3_storage.delete_uri(uri):
                deleted_count += 1

        prefixes = {
            (settings.upload_bucket, _s3_prefix(settings.s3_temp_upload_prefix, document.user_id, document.id)),
            (settings.upload_bucket, _s3_prefix(settings.s3_rule_prefix, document.user_id, document.id)),
        }
        for audit in audit_runs:
            prefixes.add((settings.report_bucket, _s3_prefix(settings.s3_report_prefix, audit.user_id, audit.id)))

        for bucket, prefix in sorted(prefixes):
            deleted_count += _delete_s3_prefix(bucket=bucket, prefix=prefix)
    except Exception as exc:
        log_pipeline_stage(
            logger,
            "ADMIN_DELETE_S3",
            audit_id=None,
            document_id=document.id,
            domain=document.domain,
            started_at=started_at,
            status="failed",
            admin_user_id=admin_user_id,
            upload_filename=document.filename,
            error=str(exc),
        )
        raise

    log_pipeline_stage(
        logger,
        "ADMIN_DELETE_S3",
        audit_id=None,
        document_id=document.id,
        domain=document.domain,
        started_at=started_at,
        status="completed",
        admin_user_id=admin_user_id,
        deleted_s3_objects_count=deleted_count,
        upload_filename=document.filename,
    )
    return deleted_count


def _delete_s3_prefix(*, bucket: str, prefix: str) -> int:
    if not bucket or not prefix:
        return 0
    deleted_count = 0
    paginator = s3_storage.client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        keys = [{"Key": item["Key"]} for item in page.get("Contents", []) if item.get("Key")]
        if not keys:
            continue
        s3_storage.client.delete_objects(Bucket=bucket, Delete={"Objects": keys})
        deleted_count += len(keys)
    return deleted_count


def _document_s3_uris(
    *,
    document: UploadedDocument,
    audit_reports: list[AuditReport],
    report_records: list[ReportRecord],
) -> set[str]:
    uris = set()
    _add_s3_uri(uris, document.s3_uri)
    for report in audit_reports:
        _add_s3_uri(uris, report.report_json_s3_uri)
        _collect_s3_uris_from_value(uris, report.report_payload)
    for report in report_records:
        _add_s3_uri(uris, report.report_path)
        _add_s3_uri(uris, report.report_json_s3_uri)
        _collect_s3_uris_from_value(uris, report.report_payload)
    return uris


def _collect_s3_uris_from_value(uris: set[str], value: Any) -> None:
    if isinstance(value, str):
        _add_s3_uri(uris, value)
        return
    if isinstance(value, dict):
        for item in value.values():
            _collect_s3_uris_from_value(uris, item)
        return
    if isinstance(value, list):
        for item in value:
            _collect_s3_uris_from_value(uris, item)


def _add_s3_uri(uris: set[str], value: str | None) -> None:
    if value and value.startswith("s3://"):
        uris.add(value)


def _s3_prefix(*parts: str) -> str:
    cleaned = [str(part).strip("/") for part in parts if str(part).strip("/")]
    return "/".join(cleaned) + "/"


def _any_condition(*conditions):
    active = [condition for condition in conditions if condition is not None]
    return or_(*active) if active else false()


def _rowcount(result: Any) -> int:
    value = getattr(result, "rowcount", 0)
    return int(value or 0)


def _dt(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _user_payload(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "name": user.name,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": _dt(user.created_at),
    }


def _uploaded_document_payload(document: UploadedDocument) -> dict[str, Any]:
    return {
        "id": document.id,
        "user_id": document.user_id,
        "title": document.title,
        "domain": document.domain,
        "role_type": document.role_type,
        "source_type": document.source_type,
        "filename": document.filename,
        "file_name": document.file_name,
        "content_type": document.content_type,
        "s3_uri": document.s3_uri,
        "storage_path": document.s3_key,
        "status": document.status,
        "upload_status": document.upload_status,
        "processing_stage": document.processing_stage,
        "cleanup_status": document.cleanup_status,
        "file_type": document.file_type,
        "extracted_text": document.extracted_text,
        "qdrant_collection": document.qdrant_collection,
        "created_at": _dt(document.created_at),
        "expires_at": _dt(document.expires_at),
    }


def _rule_document_payload(document: RuleDocument) -> dict[str, Any]:
    return {
        "id": document.id,
        "user_id": document.user_id,
        "rule_set_id": document.rule_set_id,
        "domain": document.domain,
        "category": document.category,
        "jurisdiction": document.jurisdiction,
        "document_type": document.document_type,
        "version": document.version,
        "filename": document.filename,
        "content_type": document.content_type,
        "s3_uri": document.s3_uri,
        "storage_path": document.storage_path,
        "status": document.status,
        "indexed_at": _dt(document.indexed_at),
        "created_at": _dt(document.created_at),
    }


def _report_payload(report: AuditReport, audit: AuditRun | None) -> dict[str, Any]:
    return {
        "id": report.id,
        "audit_id": report.audit_id,
        "summary": report.summary,
        "report_payload": report.report_payload,
        "created_at": _dt(report.created_at),
        "audit_status": audit.status if audit else None,
        "overall_risk": audit.overall_risk if audit else None,
        "confidence_score": audit.confidence_score if audit else None,
    }


def _compliance_rule_payload(rule: ComplianceRule) -> dict[str, Any]:
    return {
        "id": rule.id,
        "rule_document_id": rule.rule_document_id,
        "category": rule.category,
        "title": rule.title,
        "description": rule.description,
        "rule_text": rule.rule_text,
        "reference": rule.reference,
        "version": rule.version,
        "created_by": rule.created_by,
        "created_at": _dt(rule.created_at),
        "updated_at": _dt(rule.updated_at),
    }


def _log_payload(log: AuditLog) -> dict[str, Any]:
    return {
        "id": log.id,
        "user_id": log.user_id,
        "action": log.action,
        "entity_type": log.entity_type,
        "entity_id": log.entity_id,
        "metadata": log.metadata_json,
        "message": log.message,
        "ip_address": log.ip_address,
        "created_at": _dt(log.created_at),
    }


def _s3_storage_summary() -> dict[str, dict[str, int]]:
    return s3_storage.prefix_summary(
        bucket=settings.s3_bucket,
        prefixes=[
            settings.s3_temp_upload_prefix,
            settings.s3_rule_prefix,
            settings.s3_report_prefix,
        ],
    )
