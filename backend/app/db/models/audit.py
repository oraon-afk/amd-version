from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.session import Base


def new_uuid() -> str:
    return str(uuid4())


class AuditRun(Base):
    __tablename__ = "audit_runs"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("uploaded_documents.id"),
        index=True,
        nullable=False,
    )
    rule_set_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="uploaded", index=True, nullable=False)
    overall_risk: Mapped[str | None] = mapped_column(String(20), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    # Feature 1: HITL – review deadline for pending_review state
    review_deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_uuid)
    audit_id: Mapped[str] = mapped_column(ForeignKey("audit_runs.id"), index=True, nullable=False)
    document_id: Mapped[str | None] = mapped_column(ForeignKey("uploaded_documents.id"), index=True, nullable=True)
    violated_rule: Mapped[str] = mapped_column(Text, nullable=False)
    finding_type: Mapped[str] = mapped_column(String(50), default="missing_clause", nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="MEDIUM", nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), default="MEDIUM", nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    evidence_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    citation_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    # Feature 1: HITL review columns
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    review_status: Mapped[str] = mapped_column(String(20), default="not_required", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_finding_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class EvidenceLink(Base):
    __tablename__ = "evidence_links"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_uuid)
    finding_id: Mapped[str] = mapped_column(ForeignKey("findings.id"), index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    qdrant_point_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    document_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)
    page_number: Mapped[int | None] = mapped_column(nullable=True)
    section_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    citation_text: Mapped[str] = mapped_column(Text, nullable=False)
    citation_label: Mapped[str | None] = mapped_column(String(512), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class AuditReport(Base):
    __tablename__ = "audit_reports"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_uuid)
    audit_id: Mapped[str] = mapped_column(ForeignKey("audit_runs.id"), index=True, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    report_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    report_json_s3_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ComplianceScoreDiagnostic(Base):
    __tablename__ = "compliance_score_diagnostics"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_uuid)
    audit_id: Mapped[str] = mapped_column(ForeignKey("audit_runs.id"), index=True, nullable=False)
    report_id: Mapped[str | None] = mapped_column(ForeignKey("audit_reports.id"), index=True, nullable=True)
    rules_evaluated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rules_matched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rules_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    match_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    diagnostics_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    # Feature 2: Full diagnostic trail columns
    retry_attempts: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    final_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_llm_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    context_chunks_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    heuristic_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    blended_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)


class AuditResult(Base):
    __tablename__ = "audit_results"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_uuid)
    document_id: Mapped[str | None] = mapped_column(
        ForeignKey("documents.id"),
        index=True,
        nullable=True,
    )
    overall_risk: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow, nullable=True)


class ReportRecord(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_uuid)
    audit_result_id: Mapped[str | None] = mapped_column(
        ForeignKey("audit_results.id"),
        index=True,
        nullable=True,
    )
    report_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    audit_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    report_json_s3_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
