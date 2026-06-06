from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from backend.app.auth.auth_dependencies import get_current_user
from backend.app.db.models.user import User
from backend.app.db.session import get_db
from backend.app.schemas.audit import (
    AuditResponse,
    ComplianceScoreDiagnosticResponse,
    CreateAuditRequest,
    EvidenceResponse,
    FindingResponse,
    ReportResponse,
)
from backend.app.services.audit_service import audit_service

router = APIRouter(prefix="/audits", tags=["audits"])
compat_router = APIRouter(prefix="/audit", tags=["audit"])


@router.post("", response_model=AuditResponse)
def create_audit(
    payload: CreateAuditRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AuditResponse:
    audit = audit_service.create_audit(db=db, user=current_user, payload=payload)
    background_tasks.add_task(audit_service.run_audit_background, audit.id)
    return audit


@router.get("", response_model=list[AuditResponse])
def list_audits(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AuditResponse]:
    return audit_service.list_audits(db=db, user=current_user)


@router.get("/{audit_id}", response_model=AuditResponse)
def get_audit(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AuditResponse:
    return audit_service.get_audit(db=db, user=current_user, audit_id=audit_id)


@router.get("/{audit_id}/findings", response_model=list[FindingResponse])
def get_findings(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[FindingResponse]:
    return audit_service.get_findings(db=db, user=current_user, audit_id=audit_id)


@router.get("/{audit_id}/evidence", response_model=list[EvidenceResponse])
def get_evidence(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[EvidenceResponse]:
    return audit_service.get_evidence(db=db, user=current_user, audit_id=audit_id)


@router.get("/{audit_id}/report", response_model=ReportResponse)
def get_report(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportResponse:
    return audit_service.get_report(db=db, user=current_user, audit_id=audit_id)


@router.get("/{audit_id}/diagnostics", response_model=ComplianceScoreDiagnosticResponse)
def get_score_diagnostics(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ComplianceScoreDiagnosticResponse:
    return audit_service.get_score_diagnostics(db=db, user=current_user, audit_id=audit_id)


@compat_router.post("/run", response_model=AuditResponse)
def run_audit(
    payload: CreateAuditRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AuditResponse:
    audit = audit_service.create_audit(db=db, user=current_user, payload=payload)
    background_tasks.add_task(audit_service.run_audit_background, audit.id)
    return audit


@compat_router.get("/report/{id_or_audit_id}", response_model=ReportResponse)
def get_audit_report_alias(
    id_or_audit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportResponse:
    return audit_service.get_report_by_id_or_audit_id(
        db=db,
        user=current_user,
        id_or_audit_id=id_or_audit_id,
    )
