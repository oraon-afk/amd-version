from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.session import Base


def new_uuid() -> str:
    return str(uuid4())


class RuleDocument(Base):
    __tablename__ = "rule_documents"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    rule_set_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    domain: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    jurisdiction: Mapped[str | None] = mapped_column(String(100), nullable=True)
    document_type: Mapped[str] = mapped_column(String(80), default="rules", nullable=False)
    version: Mapped[str] = mapped_column(String(50), default="v1", nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    s3_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    storage_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="indexed", index=True, nullable=False)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ComplianceRule(Base):
    __tablename__ = "compliance_rules"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_uuid)
    rule_document_id: Mapped[str | None] = mapped_column(ForeignKey("rule_documents.id"), index=True, nullable=True)
    category: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    rule_text: Mapped[str] = mapped_column(Text, nullable=False)
    reference: Mapped[str | None] = mapped_column(String(512), nullable=True)
    version: Mapped[str] = mapped_column(String(50), default="v1", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", index=True, nullable=False)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    # Feature 4: Configurable Rule Engine – versioning + custom attributes
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    parent_rule_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)
    custom_attributes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    effectivity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
