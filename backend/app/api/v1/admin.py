from __future__ import annotations

from datetime import date, datetime
import logging
import math
from time import time
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from qdrant_client.models import FieldCondition, Filter, MatchValue, PointIdsList
from sqlalchemy import delete, false, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.auth.auth_dependencies import require_admin
from backend.app.core.config import settings
from backend.app.core.logging import get_logger, log_once, log_pipeline_stage
from backend.app.db.models.audit import (
    AuditReport,
    AuditResult,
    AuditRun,
    ComplianceScoreDiagnostic,
    EvidenceLink,
    Finding,
    ReportRecord,
)
from backend.app.db.models.digital_twin import ComplianceTwinPolicyProfile
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
    custom_attributes: dict | None = None
    effectivity_date: date | None = None
    expiry_date: date | None = None


class GenerateRuleFromTextRequest(BaseModel):
    description: str = Field(min_length=5)


class ComplianceRuleUpdate(BaseModel):
    category: str | None = Field(default=None, min_length=2, max_length=100)
    title: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None
    rule_text: str | None = Field(default=None, min_length=5)
    reference: str | None = None
    version: str | None = None
    status: str | None = None
    custom_attributes: dict | None = None
    effectivity_date: date | None = None
    expiry_date: date | None = None


class RuleTestRequest(BaseModel):
    sample_document_text: str


class GapAnalysisRequest(BaseModel):
    framework: str = Field(min_length=3, max_length=20)


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
async def delete_document(
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
    
    from backend.app.services.cache_service import cache_service
    await cache_service.delete_pattern("cache:documents:*")

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
    report_ids = [report.id for report in audit_reports]
    audit_result_ids = [
        report.audit_result_id
        for report in report_records
        if report.audit_result_id
    ]
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
        twin_profiles_count = _rowcount(
            db.execute(
                delete(ComplianceTwinPolicyProfile).where(
                    _any_condition(
                        ComplianceTwinPolicyProfile.latest_audit_id == audit.id,
                        ComplianceTwinPolicyProfile.latest_report_id.in_(report_ids) if report_ids else None,
                    ),
                ),
            ),
        )
        diagnostics_count = _rowcount(
            db.execute(
                delete(ComplianceScoreDiagnostic).where(
                    _any_condition(
                        ComplianceScoreDiagnostic.audit_id == audit.id,
                        ComplianceScoreDiagnostic.report_id.in_(report_ids) if report_ids else None,
                    ),
                ),
            ),
        )
        reports_count = _rowcount(db.execute(delete(ReportRecord).where(ReportRecord.audit_id == audit.id)))
        audit_results_count = _rowcount(
            db.execute(
                delete(AuditResult).where(AuditResult.id.in_(audit_result_ids) if audit_result_ids else false()),
            ),
        )
        audit_reports_count = _rowcount(db.execute(delete(AuditReport).where(AuditReport.audit_id == audit.id)))
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
            "deleted_audit_results_count": audit_results_count,
            "deleted_score_diagnostics_count": diagnostics_count,
            "deleted_twin_profiles_count": twin_profiles_count,
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
        deleted_audit_results_count=audit_results_count,
        deleted_score_diagnostics_count=diagnostics_count,
        deleted_twin_profiles_count=twin_profiles_count,
        deleted_s3_objects_count=deleted_s3_objects_count,
    )
    return {
        "status": "deleted",
        "id": audit_id,
        "deleted_findings_count": findings_count,
        "deleted_evidence_count": evidence_count,
        "deleted_audit_reports_count": audit_reports_count,
        "deleted_reports_count": reports_count,
        "deleted_audit_results_count": audit_results_count,
        "deleted_score_diagnostics_count": diagnostics_count,
        "deleted_twin_profiles_count": twin_profiles_count,
    }


@router.get("/compliance-rules")
async def list_compliance_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[dict[str, Any]]:
    from backend.app.services.cache_service import cache_service
    cache_key = "cache:rules:all"
    cached = await cache_service.get(cache_key)
    if cached is not None:
        return cached

    rules = db.scalars(select(ComplianceRule).order_by(ComplianceRule.created_at.desc())).all()
    payload = [_compliance_rule_payload(rule) for rule in rules]
    await cache_service.set(cache_key, payload, ttl=300)
    return payload


@router.post("/gap-analysis")
async def gap_analysis(
    payload: GapAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[dict[str, Any]]:
    """Perform a semantic gap analysis for a standard compliance framework."""
    try:
        from backend.app.services.gap_analysis_service import gap_analysis_service
        return await gap_analysis_service.analyze_gap(
            db=db,
            framework=payload.framework,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/compliance-rules/generate-from-text")
def generate_rule_from_text(
    payload: GenerateRuleFromTextRequest,
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    """Generate a structured compliance rule draft from plain English."""
    try:
        from backend.app.services.rule_generator_service import rule_generator_service
        return rule_generator_service.generate_rule(description=payload.description)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to generate structured rule: {exc}",
        )


@router.post("/compliance-rules")
async def create_compliance_rule(
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
        version_number=1,
        custom_attributes=payload.custom_attributes,
        effectivity_date=payload.effectivity_date,
        expiry_date=payload.expiry_date,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    _upsert_manual_rule_vector(rule=rule, current_user=current_user)
    audit_log_service.log(
        db=db,
        user=current_user,
        action="admin.compliance_rule.created",
        entity_type="compliance_rule",
        entity_id=rule.id,
        metadata={"category": rule.category},
    )
    from backend.app.services.cache_service import cache_service
    await cache_service.delete("cache:rules:all")
    return _compliance_rule_payload(rule)


@router.patch("/compliance-rules/{rule_id}")
async def update_compliance_rule(
    rule_id: str,
    payload: ComplianceRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    rule = db.get(ComplianceRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compliance rule not found.")
    updates = payload.model_dump(exclude_unset=True)
    allowed_statuses = {"active", "archived"}
    if "status" in updates and updates["status"] not in allowed_statuses:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rule status must be active or archived.")

    # Versioning logic:
    # If the rule is updated, we archive the old row and create a new row with version_number + 1.
    # But if the only change is status="archived" on an already active rule, we just archive the row.
    only_status_archive = len(updates) == 1 and "status" in updates and updates["status"] == "archived"

    from backend.app.services.cache_service import cache_service

    if only_status_archive:
        rule.status = "archived"
        db.commit()
        db.refresh(rule)
        _upsert_manual_rule_vector(
            rule=rule,
            current_user=current_user,
            source_type="archived_compliance_rule",
        )
        audit_log_service.log(
            db=db,
            user=current_user,
            action="admin.compliance_rule.archived",
            entity_type="compliance_rule",
            entity_id=rule.id,
            metadata={"status": rule.status},
        )
        await cache_service.delete("cache:rules:all")
        return _compliance_rule_payload(rule)

    # Archive the current rule
    rule.status = "archived"
    db.commit()
    db.refresh(rule)
    _upsert_manual_rule_vector(
        rule=rule,
        current_user=current_user,
        source_type="archived_compliance_rule",
    )

    # Create new rule version
    new_rule = ComplianceRule(
        category=updates.get("category", rule.category),
        title=updates.get("title", rule.title),
        description=updates.get("description", rule.description),
        rule_text=updates.get("rule_text", rule.rule_text),
        reference=updates.get("reference", rule.reference),
        version=updates.get("version", rule.version),
        status=updates.get("status", "active"),
        created_by=current_user.id,
        version_number=rule.version_number + 1,
        parent_rule_id=rule.id,
        custom_attributes=updates.get("custom_attributes", rule.custom_attributes),
        effectivity_date=updates.get("effectivity_date", rule.effectivity_date),
        expiry_date=updates.get("expiry_date", rule.expiry_date),
    )
    db.add(new_rule)
    db.commit()
    db.refresh(new_rule)
    _upsert_manual_rule_vector(rule=new_rule, current_user=current_user)

    audit_log_service.log(
        db=db,
        user=current_user,
        action="admin.compliance_rule.updated",
        entity_type="compliance_rule",
        entity_id=new_rule.id,
        metadata={"status": new_rule.status, "version_number": new_rule.version_number, "parent_id": rule.id},
    )
    await cache_service.delete("cache:rules:all")
    return _compliance_rule_payload(new_rule)


@router.post("/compliance-rules/{rule_id}/test")
def test_compliance_rule(
    rule_id: str,
    payload: RuleTestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    """Test a compliance rule against sample text using the live evaluation pipeline."""
    try:
        from backend.app.services.rule_test_service import rule_test_service
        return rule_test_service.test_rule(
            db=db,
            user=current_user,
            rule_id=rule_id,
            sample_document_text=payload.sample_document_text,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/compliance-rules/{rule_id}/archive")
async def archive_compliance_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    return await update_compliance_rule(
        rule_id=rule_id,
        payload=ComplianceRuleUpdate(status="archived"),
        db=db,
        current_user=current_user,
    )


@router.delete("/compliance-rules/{rule_id}")
async def delete_compliance_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    rule = db.get(ComplianceRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compliance rule not found.")
    _delete_manual_rule_vector(rule_id=rule.id)
    db.delete(rule)
    db.commit()
    audit_log_service.log(
        db=db,
        user=current_user,
        action="admin.compliance_rule.deleted",
        entity_type="compliance_rule",
        entity_id=rule_id,
    )
    from backend.app.services.cache_service import cache_service
    await cache_service.delete("cache:rules:all")
    return {"status": "deleted", "id": rule_id}


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
async def analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    from backend.app.services.cache_service import cache_service
    cache_key = "cache:admin:analytics"
    cached = await cache_service.get(cache_key)
    if cached is not None:
        return cached

    users = db.scalar(select(func.count()).select_from(User)) or 0
    uploads = db.scalar(select(func.count()).select_from(UploadedDocument)) or 0
    rule_docs = db.scalar(select(func.count()).select_from(RuleDocument)) or 0
    audits = db.scalar(select(func.count()).select_from(AuditRun)) or 0
    completed = db.scalar(select(func.count()).select_from(AuditRun).where(AuditRun.status == "completed")) or 0
    failed = db.scalar(select(func.count()).select_from(AuditRun).where(AuditRun.status == "failed")) or 0
    high_risk = db.scalar(select(func.count()).select_from(AuditRun).where(AuditRun.overall_risk == "HIGH")) or 0
    storage, storage_warnings = _safe_s3_storage_summary()
    payload = {
        "users": users,
        "uploaded_documents": uploads,
        "rule_documents": rule_docs,
        "audits": audits,
        "completed_audits": completed,
        "failed_audits": failed,
        "high_risk_audits": high_risk,
        "storage": storage,
        "warnings": storage_warnings,
    }
    await cache_service.set(cache_key, payload, ttl=30)
    return payload


@router.get("/logs")
def system_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[dict[str, Any]]:
    logs = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(200)).all()
    return [_log_payload(log) for log in logs]


@router.get("/storage")
def storage_monitoring(current_user: User = Depends(require_admin)) -> dict[str, Any]:
    areas, warnings = _safe_s3_storage_summary()
    buckets = _configured_storage_buckets()
    enabled = any(buckets.values())
    return {
        "enabled": enabled,
        "status": "connected" if enabled and not warnings else "storage_not_configured" if not enabled else "degraded",
        "root": settings.storage_root,
        "bucket": settings.s3_bucket or None,
        "buckets": buckets,
        "retention_hours": settings.temp_document_retention_hours,
        "areas": areas,
        "warnings": warnings,
    }


@router.get("/qdrant")
def qdrant_monitoring(current_user: User = Depends(require_admin)) -> dict[str, Any]:
    try:
        rule_collection = settings.qdrant_rule_collection.strip()
        upload_collection = settings.qdrant_upload_collection.strip()
        collections = qdrant_store.client.get_collections().collections
        items = []
        seen_collections: set[str] = set()
        for collection in collections:
            collection_name = collection.name.strip()
            if not collection_name or collection_name in seen_collections:
                continue
            seen_collections.add(collection_name)
            detail = qdrant_store.client.get_collection(collection_name)
            items.append(
                {
                    "name": collection_name,
                    "points_count": getattr(detail, "points_count", None),
                    "vectors_count": getattr(detail, "vectors_count", None),
                    "is_rule_collection": collection_name == rule_collection,
                    "is_upload_collection": collection_name == upload_collection,
                },
            )
        return {
            "status": "connected",
            "rule_collection": rule_collection,
            "upload_collection": upload_collection,
            "collections": items,
        }
    except Exception as exc:
        return {
            "status": "unavailable",
            "rule_collection": settings.qdrant_rule_collection.strip(),
            "upload_collection": settings.qdrant_upload_collection.strip(),
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
    report_ids = [report.id for report in audit_reports]
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
        twin_profiles_count = _rowcount(
            db.execute(
                delete(ComplianceTwinPolicyProfile).where(
                    _any_condition(
                        ComplianceTwinPolicyProfile.document_id == document.id,
                        ComplianceTwinPolicyProfile.latest_audit_id.in_(audit_ids) if audit_ids else None,
                        ComplianceTwinPolicyProfile.latest_report_id.in_(report_ids) if report_ids else None,
                    ),
                ),
            ),
        )
        diagnostics_count = _rowcount(
            db.execute(
                delete(ComplianceScoreDiagnostic).where(
                    _any_condition(
                        ComplianceScoreDiagnostic.audit_id.in_(audit_ids) if audit_ids else None,
                        ComplianceScoreDiagnostic.report_id.in_(report_ids) if report_ids else None,
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
        batch_documents_count = _rowcount(
            db.execute(
                update(BatchDocument)
                .where(
                    _any_condition(
                        BatchDocument.document_id == document.id,
                        BatchDocument.audit_id.in_(audit_ids) if audit_ids else None,
                    ),
                )
                .values(document_id=None, audit_id=None),
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
            deleted_score_diagnostics_count=diagnostics_count,
            deleted_twin_profiles_count=twin_profiles_count,
            cleared_batch_documents_count=batch_documents_count,
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
            collection_name=settings.qdrant_upload_collection.strip(),
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
        logger.warning("Admin document Qdrant cleanup skipped for document %s: %s", document_id, exc)
        return 0

    log_pipeline_stage(
        logger,
        "ADMIN_DELETE_QDRANT",
        audit_id=None,
        document_id=document_id,
        domain=domain,
        started_at=started_at,
        status="completed",
        admin_user_id=admin_user_id,
        collection=settings.qdrant_upload_collection.strip(),
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
    deleted_count = 0
    try:
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
        logger.warning("Admin document S3 cleanup skipped for document %s: %s", document.id, exc)
        return deleted_count

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
    try:
        bucket = bucket.strip()
        prefix = prefix.strip("/")
        if prefix:
            prefix = f"{prefix}/"
        paginator = s3_storage.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            keys = [{"Key": item["Key"]} for item in page.get("Contents", []) if item.get("Key")]
            if not keys:
                continue
            s3_storage.client.delete_objects(Bucket=bucket, Delete={"Objects": keys})
            deleted_count += len(keys)
    except Exception as exc:
        logger.warning("S3 prefix cleanup skipped bucket=%s prefix=%s error=%s", bucket, prefix, exc)
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
    payload = report.report_payload if isinstance(report.report_payload, dict) else {}
    return {
        "id": report.id,
        "audit_id": report.audit_id,
        "summary": report.summary,
        "compliance_score": _read_payload_number(
            payload,
            "compliance_score",
            "complianceScore",
            "audit_score",
            "auditScore",
            "overall_score",
            "overallScore",
            "final_score",
            "finalScore",
            "score",
            normalize_percent=True,
        ),
        "findings_count": _findings_count_from_payload(payload),
        "risk_level": audit.overall_risk if audit else _risk_level_from_payload(payload),
        "report_payload": payload,
        "created_at": _dt(report.created_at),
        "audit_status": audit.status if audit else None,
        "overall_risk": audit.overall_risk if audit else None,
        "confidence_score": audit.confidence_score if audit else None,
    }


def _read_payload_number(payload: dict[str, Any], *keys: str, normalize_percent: bool = False) -> float | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            number = float(value)
            return number / 100 if normalize_percent and number > 1 else number
        if isinstance(value, str):
            stripped = value.strip()
            try:
                number = float(stripped.removesuffix("%"))
            except ValueError:
                continue
            if math.isfinite(number):
                return number / 100 if normalize_percent and (stripped.endswith("%") or number > 1) else number
    return None


def _findings_count_from_payload(payload: dict[str, Any]) -> int:
    explicit = _read_payload_number(payload, "finding_count", "findings_count", "total_violations", "failed_rules")
    findings = payload.get("findings")
    list_count = len(findings) if isinstance(findings, list) else 0
    if explicit is None:
        return list_count
    return max(int(explicit), list_count)


def _risk_level_from_payload(payload: dict[str, Any]) -> str | None:
    explicit = payload.get("risk_level") or payload.get("riskLevel")
    if explicit:
        return str(explicit).upper()
    risk_counts = payload.get("risk_counts")
    if not isinstance(risk_counts, dict):
        return None
    if _read_payload_number(risk_counts, "CRITICAL", "critical"):
        return "CRITICAL"
    if _read_payload_number(risk_counts, "HIGH", "high"):
        return "HIGH"
    if _read_payload_number(risk_counts, "MEDIUM", "medium"):
        return "MEDIUM"
    if _read_payload_number(risk_counts, "LOW", "low"):
        return "LOW"
    return None


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
        "status": rule.status,
        "created_by": rule.created_by,
        "created_at": _dt(rule.created_at),
        "updated_at": _dt(rule.updated_at),
        "version_number": rule.version_number,
        "parent_rule_id": rule.parent_rule_id,
        "custom_attributes": rule.custom_attributes,
        "effectivity_date": rule.effectivity_date.isoformat() if rule.effectivity_date else None,
        "expiry_date": rule.expiry_date.isoformat() if rule.expiry_date else None,
    }


def _upsert_manual_rule_vector(
    *,
    rule: ComplianceRule,
    current_user: User,
    source_type: str = "compliance_rule",
) -> None:
    qdrant_store.upsert_chunks(
        collection_name=settings.qdrant_rule_collection,
        chunks=[
            {
                "chunk_id": f"manual-rule:{rule.id}",
                "document_id": rule.id,
                "source_type": source_type,
                "domain": rule.category.strip().lower().replace("_", "-"),
                "category": rule.category,
                "section": rule.title,
                "section_title": rule.title,
                "text": rule.rule_text,
                "citation_label": rule.reference or rule.title,
                "source": "manual_compliance_rule",
                "role_type": "ADMIN",
                "uploaded_by": current_user.id,
                "rule_status": rule.status,
                "version": rule.version,
            },
        ],
        embeddings=embedding_service.embed_texts([rule.rule_text]),
    )


def _delete_manual_rule_vector(*, rule_id: str) -> None:
    point_id = str(uuid5(NAMESPACE_URL, f"manual-rule:{rule_id}"))
    try:
        qdrant_store.client.delete(
            collection_name=settings.qdrant_rule_collection.strip(),
            points_selector=PointIdsList(points=[point_id]),
            wait=True,
        )
    except Exception:
        logger.warning("Manual compliance rule vector delete failed for rule %s", rule_id, exc_info=True)


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


def _configured_storage_buckets() -> dict[str, str | None]:
    return {
        "rules": settings.rule_bucket or None,
        "temporary_uploads": settings.upload_bucket or None,
        "reports": settings.report_bucket or None,
    }


def _storage_prefix_targets() -> list[tuple[str, str | None]]:
    return [
        (settings.s3_temp_upload_prefix, settings.upload_bucket),
        (settings.s3_rule_prefix, settings.rule_bucket),
        (settings.s3_report_prefix, settings.report_bucket),
    ]


def _s3_storage_summary() -> dict[str, dict[str, int]]:
    summary: dict[str, dict[str, int]] = {}
    for prefix, bucket in _storage_prefix_targets():
        if not prefix or not prefix.strip("/") or not bucket:
            continue
        summary.update(s3_storage.prefix_summary(bucket=bucket, prefixes=[prefix]))
    return summary


def _safe_s3_storage_summary() -> tuple[dict[str, dict[str, int]], list[str]]:
    warnings: list[str] = []
    missing = [label for label, bucket in _configured_storage_buckets().items() if not bucket]
    if missing:
        warnings.append(f"S3 buckets are not fully configured: {', '.join(missing)}.")
        log_once(
            logger,
            logging.WARNING,
            "admin_storage_summary_partial_bucket_configuration",
            "ADMIN_STORAGE_SUMMARY_PARTIAL_BUCKET_CONFIGURATION missing=%s",
            ",".join(missing),
        )
    if len(missing) == len(_configured_storage_buckets()):
        return _empty_storage_summary(), warnings
    try:
        return _s3_storage_summary(), warnings
    except Exception as exc:
        log_once(
            logger,
            logging.WARNING,
            "admin_storage_summary_failed",
            "ADMIN_STORAGE_SUMMARY_FAILED error=%s",
            exc,
        )
        warnings.append("S3 storage summary is unavailable.")
        return _empty_storage_summary(), warnings


def _empty_storage_summary() -> dict[str, dict[str, int]]:
    return {
        prefix.strip("/"): {"files": 0, "bytes": 0}
        for prefix, _bucket in _storage_prefix_targets()
        if prefix and prefix.strip("/")
    }


@router.get("/deployment/config")
def get_deployment_config(
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    """Get the current deployment configuration with redacted secrets."""
    return {
        "mode": settings.deployment_mode,
        "components": {
            "vector_db": {
                "type": "qdrant_local" if settings.local_qdrant_url else "qdrant_cloud",
                "url": settings.local_qdrant_url or settings.qdrant_url,
            },
            "storage": {
                "type": "minio" if settings.minio_endpoint else "aws_s3",
                "endpoint": settings.minio_endpoint or "AWS S3 Cloud",
            },
            "embedding": {
                "type": "local" if settings.local_embedding_model else "cloud",
                "model": settings.local_embedding_model or settings.embedding_model,
            },
            "llm": {
                "type": settings.primary_llm_provider,
                "model": settings.primary_llm_model,
            }
        }
    }


@router.post("/deployment/reload")
def reload_deployment_config(
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    """Reload deployment clients and config."""
    # Reset cached singleton clients
    from backend.app.rag.indexing.qdrant_store import qdrant_store
    from backend.app.storage.s3_client import s3_storage
    
    qdrant_store._client = None
    s3_storage._client = None
    
    return {
        "status": "reloading",
        "components_reloaded": ["qdrant_client", "s3_storage_client"]
    }


@router.post("/caching/toggle")
def toggle_caching(
    enabled: bool,
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    """Toggle the caching status dynamically."""
    settings.enable_caching = enabled
    from backend.app.services.cache_service import cache_service
    cache_service._redis = None
    return {"status": "success", "enable_caching": settings.enable_caching}
