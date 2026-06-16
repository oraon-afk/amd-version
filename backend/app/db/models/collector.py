"""
Feature 3: Agentic Evidence Collection – SQLAlchemy models.

Tables:
  - evidence_collectors : User-defined collectors (HTTP / SQL / script)
  - external_evidence   : Evidence fetched by collectors, linked to audits/findings
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.session import Base


def new_uuid() -> str:
    return str(uuid4())


class EvidenceCollector(Base):
    __tablename__ = "evidence_collectors"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    # type: 'http' | 'sql' | 'script'
    collector_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # JSON config: url, method, headers, response_mapping, db_url, query, script_path
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Cron expression e.g. "0 */6 * * *"
    schedule: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_domain: Mapped[str | None] = mapped_column(String(100), nullable=True)
    document_id: Mapped[str | None] = mapped_column(ForeignKey("uploaded_documents.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_run_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ExternalEvidence(Base):
    __tablename__ = "external_evidence"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_uuid)
    collector_id: Mapped[str | None] = mapped_column(ForeignKey("evidence_collectors.id"), index=True, nullable=True)
    audit_id: Mapped[str | None] = mapped_column(ForeignKey("audit_runs.id"), index=True, nullable=True)
    finding_id: Mapped[str | None] = mapped_column(ForeignKey("findings.id"), index=True, nullable=True)
    evidence_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    citation_label: Mapped[str | None] = mapped_column(String(512), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    # Raw API/DB response payload (truncated to 10KB)
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), default="external_collector", nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
