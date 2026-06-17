"""
Feature 1: Human-in-the-Loop (HITL) Review Service.

Handles accept / reject / modify actions on high-risk findings
before an audit report is published.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.logging import get_logger
from backend.app.db.models.audit import AuditReport, AuditRun, Finding
from backend.app.db.models.user import User
from backend.app.db.transactions import commit_or_rollback
from backend.app.services.audit_log_service import audit_log_service

logger = get_logger(__name__)

# Valid actions for HITL review
REVIEW_ACTIONS = {"accept", "reject", "modify"}

# Fields that may be modified via the modify action
MODIFIABLE_FINDING_FIELDS = {"risk_level", "severity", "explanation", "recommendation", "violated_rule"}


class FindingReviewService:
    """Service that implements the HITL review workflow for critical findings."""

    # ─────────────────────────── public API ──────────────────────────────────

    def review_finding(
        self,
        *,
        db: Session,
        user: User,
        finding_id: str,
        action: str,
        comment: str | None,
        modified_fields: dict[str, Any] | None,
    ) -> Finding:
        """
        Apply a review action (accept | reject | modify) to a finding.

        - accept:  Mark as reviewed with no content changes.
        - reject:  Soft-delete the finding (is_active=False).
        - modify:  Apply field overrides, snapshot original state.

        Returns the updated Finding object.
        """
        if action not in REVIEW_ACTIONS:
            raise ValueError(f"Invalid review action '{action}'. Must be one of {REVIEW_ACTIONS}.")

        finding = db.scalar(select(Finding).where(Finding.id == finding_id))
        if finding is None:
            raise ValueError(f"Finding not found: {finding_id}")

        # Enforce ownership: user must own the audit unless admin or reviewer
        audit = db.scalar(select(AuditRun).where(AuditRun.id == finding.audit_id))
        if audit is None:
            raise ValueError("Audit not found for finding.")
        if user.role.upper() not in {"ADMIN", "REVIEWER"} and audit.user_id != user.id:
            raise PermissionError("You do not have permission to review this finding.")

        if not finding.needs_review:
            raise ValueError("This finding does not require human review.")

        if finding.review_status in {"accepted", "rejected", "modified"}:
            raise ValueError(f"Finding has already been reviewed (status: {finding.review_status}).")

        # Snapshot original state before any changes
        original_snapshot: dict[str, Any] = {
            "risk_level": finding.risk_level,
            "severity": finding.severity,
            "explanation": finding.explanation,
            "recommendation": finding.recommendation,
            "violated_rule": finding.violated_rule,
        }

        if action == "accept":
            finding.review_status = "accepted"

        elif action == "reject":
            finding.is_active = False
            finding.review_status = "rejected"

        elif action == "modify":
            if not modified_fields:
                raise ValueError("'modified_fields' is required for action='modify'.")
            invalid_fields = set(modified_fields.keys()) - MODIFIABLE_FINDING_FIELDS
            if invalid_fields:
                raise ValueError(f"Cannot modify fields: {invalid_fields}. Allowed: {MODIFIABLE_FINDING_FIELDS}")

            finding.original_finding_snapshot = original_snapshot
            for field, value in modified_fields.items():
                setattr(finding, field, value)
            finding.review_status = "modified"

        finding.reviewed_by = user.id
        finding.reviewed_at = datetime.utcnow()
        finding.review_comment = comment or ""

        commit_or_rollback(db)

        audit_log_service.log(
            db=db,
            action=f"finding.review.{action}",
            user=user,
            entity_type="finding",
            entity_id=finding_id,
            metadata={
                "audit_id": finding.audit_id,
                "action": action,
                "comment": comment,
            },
        )

        logger.info("Finding %s reviewed: action=%s by user=%s", finding_id, action, user.id)

        # After each review, check if audit can auto-advance
        self._maybe_advance_audit(db=db, audit=audit, user=user)

        return finding

    def publish_report(
        self,
        *,
        db: Session,
        user: User,
        audit_id: str,
    ) -> dict[str, Any]:
        """
        Publish a report after all required HITL reviews are complete.

        Enforces that every HIGH-risk finding has been reviewed.
        Soft-removes rejected findings from the report payload, applies
        modified explanations, then marks the audit as 'completed'.
        """
        audit = db.scalar(select(AuditRun).where(AuditRun.id == audit_id))
        if audit is None:
            raise ValueError(f"Audit not found: {audit_id}")

        if user.role.upper() == "REVIEWER" or (user.role.upper() != "ADMIN" and audit.user_id != user.id):
            raise PermissionError("You do not have permission to publish this report.")

        if audit.status not in {"pending_review", "completed"}:
            raise ValueError(f"Cannot publish: audit is in state '{audit.status}'.")

        # Verify all required reviews are done
        pending = db.scalars(
            select(Finding).where(
                Finding.audit_id == audit_id,
                Finding.needs_review == True,  # noqa: E712
                Finding.review_status == "pending",
            )
        ).all()

        if pending:
            raise ValueError(
                f"Cannot publish: {len(pending)} finding(s) still require review. "
                "Accept, reject, or modify all HIGH-risk findings first."
            )

        # Fetch the latest report
        report = db.scalar(
            select(AuditReport).where(AuditReport.audit_id == audit_id).order_by(AuditReport.created_at.desc())
        )
        if report is None:
            raise ValueError(f"No report found for audit {audit_id}.")

        # Rebuild report payload: exclude rejected findings, apply modifications
        self._rebuild_report_payload(db=db, audit_id=audit_id, report=report)

        # Mark audit as completed
        audit.status = "completed"
        if audit.completed_at is None:
            audit.completed_at = datetime.utcnow()
        commit_or_rollback(db)

        audit_log_service.log(
            db=db,
            action="report.published",
            user=user,
            entity_type="audit_report",
            entity_id=report.id,
            metadata={"audit_id": audit_id},
        )

        logger.info("Report published for audit %s by user %s", audit_id, user.id)

        return {
            "report_id": report.id,
            "audit_id": audit_id,
            "status": "published",
            "published_at": datetime.utcnow(),
            "download_urls": {
                "json": f"/reports/{audit_id}/download/json",
                "pdf": f"/reports/{audit_id}/download/pdf",
            },
        }

    def get_review_history(
        self,
        *,
        db: Session,
        user: User,
        audit_id: str,
    ) -> list[Finding]:
        """Return all findings that have been through review (reviewed_at is set)."""
        audit = db.scalar(select(AuditRun).where(AuditRun.id == audit_id))
        if audit is None:
            raise ValueError(f"Audit not found: {audit_id}")
        if user.role.upper() not in {"ADMIN", "REVIEWER"} and audit.user_id != user.id:
            raise PermissionError("Access denied.")

        return list(
            db.scalars(
                select(Finding).where(
                    Finding.audit_id == audit_id,
                    Finding.reviewed_at.isnot(None),
                )
            ).all()
        )

    # ──────────────────────────── internals ──────────────────────────────────

    def _maybe_advance_audit(self, *, db: Session, audit: AuditRun, user: User) -> None:
        """If no pending reviews remain, the audit status automatically updates to completed."""
        if audit.status != "pending_review":
            return
        remaining = db.scalar(
            select(Finding).where(
                Finding.audit_id == audit.id,
                Finding.needs_review == True,  # noqa: E712
                Finding.review_status == "pending",
            )
        )
        if remaining is None:
            # Fetch the latest report to rebuild payload
            report = db.scalar(
                select(AuditReport).where(AuditReport.audit_id == audit.id).order_by(AuditReport.created_at.desc())
            )
            if report is not None:
                self._rebuild_report_payload(db=db, audit_id=audit.id, report=report)

            # Mark audit as completed
            audit.status = "completed"
            if audit.completed_at is None:
                audit.completed_at = datetime.utcnow()
            
            commit_or_rollback(db)

            audit_log_service.log(
                db=db,
                action="report.published.auto",
                user=user,
                entity_type="audit_run",
                entity_id=audit.id,
                metadata={"audit_id": audit.id},
            )

            logger.info("All required reviews complete for audit %s — automatically updated status to completed.", audit.id)

    def _rebuild_report_payload(
        self,
        *,
        db: Session,
        audit_id: str,
        report: AuditReport,
    ) -> None:
        """Patch the report payload to reflect HITL decisions."""
        payload = dict(report.report_payload)
        all_findings = list(
            db.scalars(select(Finding).where(Finding.audit_id == audit_id)).all()
        )

        # Rebuild findings list: exclude rejected, apply modified explanations
        active_findings = [f for f in all_findings if f.is_active]
        if "findings" in payload and isinstance(payload["findings"], list):
            id_map = {f.id: f for f in active_findings}
            rebuilt = []
            for item in payload["findings"]:
                if not isinstance(item, dict):
                    continue
                finding_id = item.get("id") or item.get("finding_id")
                if finding_id and finding_id in id_map:
                    f = id_map[finding_id]
                    item = dict(item)
                    item["explanation"] = f.explanation
                    item["risk_level"] = f.risk_level
                    item["severity"] = f.severity
                    item["recommendation"] = f.recommendation
                    item["review_status"] = f.review_status
                    rebuilt.append(item)
                elif finding_id is None:
                    rebuilt.append(item)
                # else: finding_id present but rejected → excluded
            payload["findings"] = rebuilt
            payload["finding_count"] = len(rebuilt)
            payload["hitl_reviewed"] = True

        report.report_payload = payload
        db.add(report)
        db.flush()


finding_review_service = FindingReviewService()
