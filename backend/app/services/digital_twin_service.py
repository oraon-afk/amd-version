from __future__ import annotations

from datetime import datetime
import math
from time import time
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.logging import get_logger, log_pipeline_stage
from backend.app.db.models.audit import AuditReport, AuditRun
from backend.app.db.models.digital_twin import (
    ComplianceDigitalTwin,
    ComplianceTwinPolicyProfile,
    ComplianceTwinSnapshot,
)
from backend.app.db.models.document import UploadedDocument
from backend.app.db.models.user import User
from backend.app.services.audit_log_service import audit_log_service

logger = get_logger(__name__)


class ComplianceDigitalTwinService:
    def get_or_rebuild(self, *, db: Session, user: User, rebuild: bool = False) -> dict[str, Any]:
        twin = self._get_twin(db=db, user=user)
        if rebuild or twin is None:
            twin = self.rebuild(db=db, user=user)
        return self._payload(db=db, twin=twin)

    def history(self, *, db: Session, user: User) -> list[ComplianceTwinSnapshot]:
        twin = self._get_twin(db=db, user=user)
        if twin is None:
            return []
        return list(
            db.scalars(
                select(ComplianceTwinSnapshot)
                .where(ComplianceTwinSnapshot.twin_id == twin.id)
                .order_by(ComplianceTwinSnapshot.created_at.desc())
                .limit(24),
            ),
        )

    def rebuild(self, *, db: Session, user: User) -> ComplianceDigitalTwin:
        started = time()
        log_pipeline_stage(
            logger,
            "DIGITAL_TWIN_REFRESH",
            audit_id=None,
            document_id=None,
            domain=None,
            started_at=started,
            status="started",
            user_id=user.id,
            role=user.role,
        )
        documents = self._documents(db=db, user=user)
        audits_by_document = self._latest_audits_by_document(db=db, documents=documents)
        reports_by_audit = self._reports_by_audit(db=db, audit_ids=[audit.id for audit in audits_by_document.values()])
        expected_domains = self._expected_domains(db=db)
        profiles = [
            self._policy_profile(document=document, audit=audits_by_document.get(document.id), reports_by_audit=reports_by_audit)
            for document in documents
        ]
        missing = self._missing_policies(expected_domains=expected_domains, profiles=profiles)
        heatmap = self._risk_heatmap(expected_domains=expected_domains, profiles=profiles)
        coverage_score = self._coverage_score(expected_domains=expected_domains, profiles=profiles)
        maturity_score = self._maturity_score(profiles=profiles, coverage_score=coverage_score)
        risk_score = self._risk_score(heatmap=heatmap)
        summary = self._summary(
            profiles=profiles,
            missing=missing,
            heatmap=heatmap,
            maturity_score=maturity_score,
            coverage_score=coverage_score,
            risk_score=risk_score,
        )
        twin = self._get_twin(db=db, user=user)
        if twin is None:
            twin = ComplianceDigitalTwin(user_id=None if self._is_admin(user) else user.id)
            db.add(twin)
            db.flush()

        twin.name = "Organization Compliance Twin"
        twin.status = "active"
        twin.maturity_score = maturity_score
        twin.coverage_score = coverage_score
        twin.risk_score = risk_score
        twin.missing_policies = missing
        twin.risk_heatmap = heatmap
        twin.policy_inventory = profiles
        twin.summary = summary
        twin.generated_at = datetime.utcnow()

        db.execute(delete(ComplianceTwinPolicyProfile).where(ComplianceTwinPolicyProfile.twin_id == twin.id))
        for profile in profiles:
            db.add(
                ComplianceTwinPolicyProfile(
                    twin_id=twin.id,
                    document_id=profile["document_id"],
                    latest_audit_id=profile.get("latest_audit_id"),
                    latest_report_id=profile.get("latest_report_id"),
                    title=profile["title"],
                    domain=profile["domain"],
                    status=profile["status"],
                    compliance_score=profile.get("compliance_score"),
                    risk_level=profile.get("risk_level"),
                    findings_count=int(profile.get("findings_count") or 0),
                    coverage_status=profile["coverage_status"],
                ),
            )

        db.add(
            ComplianceTwinSnapshot(
                twin_id=twin.id,
                maturity_score=maturity_score,
                coverage_score=coverage_score,
                risk_score=risk_score,
                total_policies=len(profiles),
                missing_policy_count=len(missing),
                high_risk_policy_count=sum(1 for item in profiles if item.get("risk_level") in {"HIGH", "CRITICAL"}),
                summary_text=str(summary["summary_text"]),
                snapshot_payload=summary,
            ),
        )
        db.commit()
        db.refresh(twin)
        audit_log_service.log(
            db=db,
            user=user,
            action="digital_twin.rebuilt",
            entity_type="compliance_digital_twin",
            entity_id=twin.id,
            metadata={
                "total_policies": len(profiles),
                "missing_policy_count": len(missing),
                "maturity_score": maturity_score,
                "coverage_score": coverage_score,
            },
        )
        log_pipeline_stage(
            logger,
            "DIGITAL_TWIN_REFRESH",
            audit_id=None,
            document_id=None,
            domain=None,
            started_at=started,
            status="completed",
            user_id=user.id,
            role=user.role,
            total_policies=len(profiles),
            missing_policy_count=len(missing),
            maturity_score=maturity_score,
            coverage_score=coverage_score,
            risk_score=risk_score,
        )
        return twin

    def _get_twin(self, *, db: Session, user: User) -> ComplianceDigitalTwin | None:
        statement = select(ComplianceDigitalTwin)
        if self._is_admin(user):
            statement = statement.where(ComplianceDigitalTwin.user_id.is_(None))
        else:
            statement = statement.where(ComplianceDigitalTwin.user_id == user.id)
        return db.scalar(statement.order_by(ComplianceDigitalTwin.updated_at.desc()))

    def _documents(self, *, db: Session, user: User) -> list[UploadedDocument]:
        statement = (
            select(UploadedDocument)
            .where(UploadedDocument.role_type != "ADMIN")
            .order_by(UploadedDocument.created_at.desc())
        )
        if not self._is_admin(user):
            statement = statement.where(UploadedDocument.user_id == user.id)
        return list(db.scalars(statement))

    @staticmethod
    def _latest_audits_by_document(*, db: Session, documents: list[UploadedDocument]) -> dict[str, AuditRun]:
        if not documents:
            return {}
        document_ids = [document.id for document in documents]
        audits = list(
            db.scalars(
                select(AuditRun)
                .where(AuditRun.document_id.in_(document_ids))
                .order_by(AuditRun.created_at.desc()),
            ),
        )
        latest: dict[str, AuditRun] = {}
        for audit in audits:
            latest.setdefault(audit.document_id, audit)
        return latest

    @staticmethod
    def _reports_by_audit(*, db: Session, audit_ids: list[str]) -> dict[str, AuditReport]:
        if not audit_ids:
            return {}
        reports = list(
            db.scalars(
                select(AuditReport)
                .where(AuditReport.audit_id.in_(audit_ids))
                .order_by(AuditReport.created_at.desc()),
            ),
        )
        latest: dict[str, AuditReport] = {}
        for report in reports:
            latest.setdefault(report.audit_id, report)
        return latest

    @staticmethod
    def _policy_profile(
        *,
        document: UploadedDocument,
        audit: AuditRun | None,
        reports_by_audit: dict[str, AuditReport],
    ) -> dict[str, Any]:
        report = reports_by_audit.get(audit.id) if audit else None
        payload = report.report_payload if report is not None and isinstance(report.report_payload, dict) else {}
        compliance_score = _read_number(
            payload,
            "compliance_score",
            "complianceScore",
            "overall_score",
            "overallScore",
            "score",
        )
        findings_count = int(
            _read_number(payload, "finding_count", "findings_count", "total_violations", "failed_rules") or 0,
        )
        risk_level = None
        if audit:
            risk_level = str(audit.overall_risk or payload.get("risk_level") or "").upper() or None
        coverage_status = "covered" if audit and audit.status == "completed" else "uploaded"
        if audit and audit.status == "failed":
            coverage_status = "audit_failed"
        domain = _normalize_domain(document.domain) or "uncategorized"
        return {
            "document_id": document.id,
            "latest_audit_id": audit.id if audit else None,
            "latest_report_id": report.id if report else None,
            "title": document.title or document.filename or document.file_name or "Untitled policy",
            "domain": domain,
            "status": audit.status if audit else document.status or document.upload_status or "uploaded",
            "compliance_score": compliance_score,
            "risk_level": risk_level,
            "findings_count": findings_count,
            "coverage_status": coverage_status,
            "uploaded_at": document.created_at.isoformat() if document.created_at else None,
        }

    def _expected_domains(self, *, db: Session) -> list[str]:
        configured = [_normalize_domain(item) for item in settings.rule_category_list if _normalize_domain(item)]
        if configured:
            return sorted(set(configured))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No compliance domains are configured for Digital Twin coverage.",
        )

    @staticmethod
    def _missing_policies(*, expected_domains: list[str], profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        covered = {_normalize_domain(profile.get("domain")) for profile in profiles}
        return [
            {
                "domain": domain,
                "priority": "high" if domain in {"security", "legal", "finance", "gdpr"} else "medium",
                "reason": "No uploaded policy document is mapped to this compliance domain.",
            }
            for domain in expected_domains
            if domain not in covered
        ]

    @staticmethod
    def _risk_heatmap(*, expected_domains: list[str], profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows = []
        for domain in expected_domains:
            domain_profiles = [profile for profile in profiles if _normalize_domain(profile.get("domain")) == domain]
            scores = [profile["compliance_score"] for profile in domain_profiles if profile.get("compliance_score") is not None]
            average_score = round(sum(scores) / len(scores), 4) if scores else None
            failed = sum(int(profile.get("findings_count") or 0) for profile in domain_profiles)
            high_risk = sum(1 for profile in domain_profiles if profile.get("risk_level") in {"HIGH", "CRITICAL"})
            if not domain_profiles:
                risk_level = "MISSING"
            elif high_risk:
                risk_level = "HIGH"
            elif average_score is not None and average_score < 0.65:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"
            rows.append(
                {
                    "domain": domain,
                    "policy_count": len(domain_profiles),
                    "average_score": average_score,
                    "findings_count": failed,
                    "risk_level": risk_level,
                },
            )
        return rows

    @staticmethod
    def _coverage_score(*, expected_domains: list[str], profiles: list[dict[str, Any]]) -> float:
        if not expected_domains:
            return 0.0
        covered = {_normalize_domain(profile.get("domain")) for profile in profiles}
        return round(len(covered & set(expected_domains)) / len(expected_domains), 4)

    @staticmethod
    def _maturity_score(*, profiles: list[dict[str, Any]], coverage_score: float) -> float:
        scores = [profile["compliance_score"] for profile in profiles if profile.get("compliance_score") is not None]
        audit_completion = sum(1 for profile in profiles if profile["coverage_status"] == "covered") / max(len(profiles), 1)
        score_average = sum(scores) / len(scores) if scores else 0.0
        return round((coverage_score * 0.45) + (score_average * 0.4) + (audit_completion * 0.15), 4)

    @staticmethod
    def _risk_score(*, heatmap: list[dict[str, Any]]) -> float:
        weights = {"MISSING": 1.0, "HIGH": 0.85, "MEDIUM": 0.55, "LOW": 0.2}
        if not heatmap:
            return 0.0
        return round(sum(weights.get(str(row.get("risk_level")), 0.4) for row in heatmap) / len(heatmap), 4)

    @staticmethod
    def _summary(
        *,
        profiles: list[dict[str, Any]],
        missing: list[dict[str, Any]],
        heatmap: list[dict[str, Any]],
        maturity_score: float,
        coverage_score: float,
        risk_score: float,
    ) -> dict[str, Any]:
        high_risk_domains = [row["domain"] for row in heatmap if row["risk_level"] in {"HIGH", "MISSING"}]
        return {
            "summary_text": (
                f"Compliance Twin covers {len(profiles)} uploaded policy document(s), "
                f"{round(coverage_score * 100)}% domain coverage, and "
                f"{round(maturity_score * 100)}% maturity."
            ),
            "total_policies": len(profiles),
            "missing_policy_count": len(missing),
            "high_risk_domains": high_risk_domains,
            "maturity_band": _band(maturity_score),
            "coverage_band": _band(coverage_score),
            "risk_band": _risk_band(risk_score),
        }

    @staticmethod
    def _payload(*, db: Session, twin: ComplianceDigitalTwin) -> dict[str, Any]:
        policies = list(
            db.scalars(
                select(ComplianceTwinPolicyProfile)
                .where(ComplianceTwinPolicyProfile.twin_id == twin.id)
                .order_by(ComplianceTwinPolicyProfile.domain.asc(), ComplianceTwinPolicyProfile.updated_at.desc()),
            ),
        )
        history = list(
            db.scalars(
                select(ComplianceTwinSnapshot)
                .where(ComplianceTwinSnapshot.twin_id == twin.id)
                .order_by(ComplianceTwinSnapshot.created_at.desc())
                .limit(12),
            ),
        )
        return {
            "id": twin.id,
            "user_id": twin.user_id,
            "name": twin.name,
            "status": twin.status,
            "maturity_score": twin.maturity_score,
            "coverage_score": twin.coverage_score,
            "risk_score": twin.risk_score,
            "missing_policies": twin.missing_policies or [],
            "risk_heatmap": twin.risk_heatmap or [],
            "policy_inventory": twin.policy_inventory or [],
            "summary": twin.summary or {},
            "generated_at": twin.generated_at,
            "created_at": twin.created_at,
            "updated_at": twin.updated_at,
            "policies": policies,
            "history": history,
        }

    @staticmethod
    def _is_admin(user: User) -> bool:
        return (user.role or "").upper() == "ADMIN"


def _read_number(payload: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            number = float(value)
            return number / 100 if number > 1 else number
        if isinstance(value, str):
            try:
                number = float(value.strip().removesuffix("%"))
            except ValueError:
                continue
            if math.isfinite(number):
                return number / 100 if value.strip().endswith("%") or number > 1 else number
    return None


def _normalize_domain(value: object) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", "-").split())


def _band(score: float) -> str:
    if score >= 0.85:
        return "optimized"
    if score >= 0.65:
        return "managed"
    if score >= 0.4:
        return "developing"
    return "initial"


def _risk_band(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


digital_twin_service = ComplianceDigitalTwinService()
