"""add compatibility fields to legacy documents and reports tables

Revision ID: 20260528_0004
Revises: 20260528_0003
Create Date: 2026-05-28
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


revision = "20260528_0004"
down_revision = "20260528_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names(schema="public"))
    if "documents" in tables:
        _add_documents_columns(bind)
    if "reports" in tables:
        _add_reports_columns(bind)


def downgrade() -> None:
    # Production data-preserving migration: no drops by design.
    pass


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in inspect(op.get_bind()).get_columns(table_name, schema="public")}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if column.name not in _columns(table_name):
        op.add_column(table_name, column)


def _add_documents_columns(bind) -> None:
    for column in [
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("domain", sa.String(length=100), nullable=True),
        sa.Column("role_type", sa.String(length=20), nullable=True),
        sa.Column("source_type", sa.String(length=50), nullable=True),
        sa.Column("file_name", sa.String(length=512), nullable=True),
        sa.Column("file_type", sa.String(length=120), nullable=True),
        sa.Column("s3_key", sa.String(length=1024), nullable=True),
        sa.Column("qdrant_collection", sa.String(length=100), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("upload_status", sa.String(length=50), nullable=True),
        sa.Column("processing_stage", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    ]:
        _add_column_if_missing("documents", column)
    bind.execute(
        text(
            """
            UPDATE documents
            SET
                title = COALESCE(NULLIF(title, ''), filename),
                domain = COALESCE(NULLIF(domain, ''), 'general'),
                role_type = COALESCE(NULLIF(role_type, ''), 'USER'),
                source_type = COALESCE(NULLIF(source_type, ''), document_type, 'file'),
                file_name = COALESCE(NULLIF(file_name, ''), filename),
                file_type = COALESCE(NULLIF(file_type, ''), document_type),
                s3_key = COALESCE(NULLIF(s3_key, ''), s3_path),
                qdrant_collection = COALESCE(NULLIF(qdrant_collection, ''), 'audit_document_chunks'),
                upload_status = COALESCE(NULLIF(upload_status, ''), status, 'uploaded'),
                processing_stage = COALESCE(NULLIF(processing_stage, ''), status, 'uploaded'),
                created_at = COALESCE(created_at, upload_time)
            """
        )
    )
    _create_index_if_missing("documents", "ix_documents_user_id", ["user_id"])
    _create_index_if_missing("documents", "ix_documents_domain", ["domain"])
    _create_index_if_missing("documents", "ix_documents_created_at", ["created_at"])


def _add_reports_columns(bind) -> None:
    for column in [
        sa.Column("audit_id", sa.Uuid(as_uuid=False), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("report_payload", sa.JSON(), nullable=True),
        sa.Column("report_json_s3_uri", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    ]:
        _add_column_if_missing("reports", column)
    bind.execute(
        text(
            """
            UPDATE reports
            SET
                audit_id = COALESCE(audit_id, audit_result_id),
                report_json_s3_uri = COALESCE(report_json_s3_uri, report_path),
                created_at = COALESCE(created_at, generated_at)
            """
        )
    )
    _create_index_if_missing("reports", "ix_reports_audit_id", ["audit_id"])
    _create_index_if_missing("reports", "ix_reports_created_at", ["created_at"])


def _create_index_if_missing(table_name: str, index_name: str, columns: list[str]) -> None:
    existing = {index["name"] for index in inspect(op.get_bind()).get_indexes(table_name, schema="public")}
    if index_name not in existing:
        op.create_index(index_name, table_name, columns)
