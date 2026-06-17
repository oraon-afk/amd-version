from datetime import datetime
from uuid import uuid4
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.db.session import Base

def new_uuid() -> str:
    return str(uuid4())

class FindingExplanationCache(Base):
    __tablename__ = "finding_explanations_cache"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_uuid)
    finding_id: Mapped[str] = mapped_column(
        ForeignKey("findings.id", ondelete="CASCADE"),
        index=True,
        unique=True,
        nullable=False,
    )
    explanation_text: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_list: Mapped[dict] = mapped_column(JSON, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class RemediationPlan(Base):
    __tablename__ = "remediation_plans"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_uuid)
    finding_id: Mapped[str] = mapped_column(
        ForeignKey("findings.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    steps: Mapped[dict] = mapped_column(JSON, nullable=False)
    estimated_effort_hours: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    priority: Mapped[str] = mapped_column(String(10), default="MEDIUM", nullable=False)
    suggested_owner_role: Mapped[str] = mapped_column(String(50), default="IT Staff", nullable=False)
    approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class FrameworkRequirement(Base):
    __tablename__ = "framework_requirements"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_uuid)
    framework: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    control_id: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class CustomReport(Base):
    __tablename__ = "custom_reports"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_uuid)
    audit_id: Mapped[str] = mapped_column(
        ForeignKey("audit_runs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    template: Mapped[str] = mapped_column(String(30), nullable=False)
    sections: Mapped[dict] = mapped_column(JSON, nullable=False)
    generated_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
