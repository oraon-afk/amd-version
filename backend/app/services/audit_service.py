from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.db.models.audit import AuditReport, AuditRun, ComplianceScoreDiagnostic, EvidenceLink, Finding
from backend.app.db.models.document import UploadedDocument
from backend.app.db.models.user import User
from backend.app.db.session import SessionLocal, recover_from_database_error
from backend.app.schemas.audit import CreateAuditRequest
from backend.app.services.audit_log_service import audit_log_service
from backend.app.workers.audit_workflow import audit_workflow


class AuditService:
    def create_audit(
        self,
        *,
        db: Session,
        user: User,
        payload: CreateAuditRequest,
    ) -> AuditRun:
        document = self._get_accessible_document(db=db, user=user, document_id=payload.document_id)
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

        audit = AuditRun(
            user_id=user.id,
            document_id=document.id,
            rule_set_id=payload.rule_set_id,
            status="uploaded",
        )
        try:
            db.add(audit)
            db.commit()
            db.refresh(audit)
        except SQLAlchemyError as exc:
            db.rollback()
            recover_from_database_error(exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database failed to create audit.",
            ) from exc
        audit_log_service.log(
            db=db,
            user=user,
            action="audit.created",
            entity_type="audit_run",
            entity_id=audit.id,
            metadata={"document_id": document.id, "rule_set_id": payload.rule_set_id},
        )
        return audit

    def create_and_run_audit(
        self,
        *,
        db: Session,
        user: User,
        payload: CreateAuditRequest,
    ) -> AuditRun:
        audit = self.create_audit(db=db, user=user, payload=payload)
        return audit_workflow.run(db=db, audit_id=audit.id)

    def run_audit_background(self, audit_id: str) -> None:
        with SessionLocal() as db:
            audit_workflow.run(db=db, audit_id=audit_id)

    def list_audits(self, *, db: Session, user: User) -> list[AuditRun]:
        statement = select(AuditRun).order_by(AuditRun.created_at.desc())
        if not self._is_admin(user):
            statement = statement.where(AuditRun.user_id == user.id)
        return list(db.scalars(statement))

    def get_audit(self, *, db: Session, user: User, audit_id: str) -> AuditRun:
        statement = select(AuditRun).where(AuditRun.id == audit_id)
        if not self._is_admin(user):
            statement = statement.where(AuditRun.user_id == user.id)
        audit = db.scalar(statement)
        if audit is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found.")
        return audit

    def get_findings(self, *, db: Session, user: User, audit_id: str) -> list[Finding]:
        self.get_audit(db=db, user=user, audit_id=audit_id)
        return list(db.scalars(select(Finding).where(Finding.audit_id == audit_id)))

    def get_evidence(self, *, db: Session, user: User, audit_id: str) -> list[EvidenceLink]:
        findings = self.get_findings(db=db, user=user, audit_id=audit_id)
        finding_ids = [finding.id for finding in findings]
        if not finding_ids:
            return []
        return list(db.scalars(select(EvidenceLink).where(EvidenceLink.finding_id.in_(finding_ids))))

    def get_report(self, *, db: Session, user: User, audit_id: str) -> AuditReport:
        self.get_audit(db=db, user=user, audit_id=audit_id)
        report = db.scalar(
            select(AuditReport)
            .where(AuditReport.audit_id == audit_id)
            .order_by(AuditReport.created_at.desc()),
        )
        if report is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
        return report

    def get_score_diagnostics(
        self,
        *,
        db: Session,
        user: User,
        audit_id: str,
    ) -> ComplianceScoreDiagnostic:
        self.get_audit(db=db, user=user, audit_id=audit_id)
        diagnostics = db.scalar(
            select(ComplianceScoreDiagnostic)
            .where(ComplianceScoreDiagnostic.audit_id == audit_id)
            .order_by(ComplianceScoreDiagnostic.created_at.desc()),
        )
        if diagnostics is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Score diagnostics not found.")
        return diagnostics

    def get_report_by_id_or_audit_id(self, *, db: Session, user: User, id_or_audit_id: str) -> AuditReport:
        report = db.scalar(select(AuditReport).where(AuditReport.id == id_or_audit_id))
        if report is not None:
            self.get_audit(db=db, user=user, audit_id=report.audit_id)
            return report
        return self.get_report(db=db, user=user, audit_id=id_or_audit_id)

    @staticmethod
    def _is_admin(user: User) -> bool:
        return (user.role or "").upper() == "ADMIN"

    def _get_accessible_document(self, *, db: Session, user: User, document_id: str) -> UploadedDocument | None:
        statement = select(UploadedDocument).where(UploadedDocument.id == document_id)
        if not self._is_admin(user):
            statement = statement.where(UploadedDocument.user_id == user.id)
        return db.scalar(statement)


audit_service = AuditService()
