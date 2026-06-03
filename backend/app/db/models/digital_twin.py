from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.session import Base


def new_uuid() -> str:
    return str(uuid4())


class ComplianceDigitalTwin(Base):
    __tablename__ = "compliance_digital_twins"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_uuid)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), default="Organization Compliance Twin", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", index=True, nullable=False)
    maturity_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    coverage_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    missing_policies: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    risk_heatmap: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    policy_inventory: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class ComplianceTwinPolicyProfile(Base):
    __tablename__ = "compliance_twin_policy_profiles"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_uuid)
    twin_id: Mapped[str] = mapped_column(ForeignKey("compliance_digital_twins.id"), index=True, nullable=False)
    document_id: Mapped[str] = mapped_column(ForeignKey("uploaded_documents.id"), index=True, nullable=False)
    latest_audit_id: Mapped[str | None] = mapped_column(ForeignKey("audit_runs.id"), index=True, nullable=True)
    latest_report_id: Mapped[str | None] = mapped_column(ForeignKey("audit_reports.id"), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    compliance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(30), nullable=True)
    findings_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    coverage_status: Mapped[str] = mapped_column(String(50), default="covered", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class ComplianceTwinSnapshot(Base):
    __tablename__ = "compliance_twin_snapshots"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_uuid)
    twin_id: Mapped[str] = mapped_column(ForeignKey("compliance_digital_twins.id"), index=True, nullable=False)
    maturity_score: Mapped[float] = mapped_column(Float, nullable=False)
    coverage_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    total_policies: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    missing_policy_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    high_risk_policy_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    snapshot_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
