"""role aware storage and pipeline stage columns

Revision ID: 20260528_0003
Revises: 20260527_0002
Create Date: 2026-05-28
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


revision = "20260528_0003"
down_revision = "20260527_0002"
branch_labels = None
depends_on = None


DEFAULT_DOMAINS = [
    ("insurance", "Insurance policy and claims compliance"),
    ("banking", "Banking, lending, KYC, and controls"),
    ("hr-policy", "Employee and HR policy compliance"),
    ("finance", "Finance, procurement, and reporting controls"),
    ("healthcare", "Healthcare privacy, safety, and operations"),
    ("legal", "Legal agreements and obligations"),
]


def upgrade() -> None:
    bind = op.get_bind()
    _add_user_columns(bind)
    _add_document_columns(bind)
    _seed_domains(bind)
    _create_compatibility_views(bind)


def downgrade() -> None:
    # Production data-preserving migration: no drops by design.
    pass


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in inspect(op.get_bind()).get_columns(table_name, schema="public")}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if column.name not in _columns(table_name):
        op.add_column(table_name, column)


def _set_not_null(table_name: str, column_name: str) -> None:
    column = next(
        column for column in inspect(op.get_bind()).get_columns(table_name, schema="public")
        if column["name"] == column_name
    )
    if column.get("nullable", True):
        op.alter_column(table_name, column_name, existing_type=column["type"], nullable=False)


def _add_user_columns(bind) -> None:
    _add_column_if_missing("users", sa.Column("role", sa.String(length=20), nullable=True))
    _add_column_if_missing("users", sa.Column("is_active", sa.Boolean(), nullable=True))
    bind.execute(text("UPDATE users SET role = COALESCE(NULLIF(role, ''), 'USER')"))
    bind.execute(text("UPDATE users SET is_active = COALESCE(is_active, true)"))
    _set_not_null("users", "role")
    _set_not_null("users", "is_active")
    _create_index_if_missing("users", "ix_users_role", ["role"])


def _add_document_columns(bind) -> None:
    _add_column_if_missing("uploaded_documents", sa.Column("role_type", sa.String(length=20), nullable=True))
    _add_column_if_missing("uploaded_documents", sa.Column("processing_stage", sa.String(length=80), nullable=True))
    _add_column_if_missing("uploaded_documents", sa.Column("cleanup_status", sa.String(length=80), nullable=True))
    _add_column_if_missing("uploaded_documents", sa.Column("file_type", sa.String(length=120), nullable=True))

    bind.execute(
        text(
            """
            UPDATE uploaded_documents AS d
            SET
                role_type = COALESCE(NULLIF(d.role_type, ''), NULLIF(u.role, ''), 'USER'),
                processing_stage = COALESCE(NULLIF(d.processing_stage, ''), NULLIF(d.upload_status, ''), NULLIF(d.status, ''), 'uploaded'),
                cleanup_status = COALESCE(
                    NULLIF(d.cleanup_status, ''),
                    CASE WHEN COALESCE(NULLIF(u.role, ''), 'USER') = 'ADMIN' THEN 'permanent' ELSE 'scheduled' END
                ),
                file_type = COALESCE(NULLIF(d.file_type, ''), NULLIF(d.content_type, ''))
            FROM users AS u
            WHERE d.user_id = u.id
            """
        )
    )
    bind.execute(
        text(
            """
            UPDATE uploaded_documents
            SET
                role_type = COALESCE(NULLIF(role_type, ''), 'USER'),
                processing_stage = COALESCE(NULLIF(processing_stage, ''), 'uploaded'),
                cleanup_status = COALESCE(NULLIF(cleanup_status, ''), 'scheduled'),
                file_type = COALESCE(NULLIF(file_type, ''), NULLIF(content_type, ''))
            """
        )
    )
    _set_not_null("uploaded_documents", "role_type")
    _set_not_null("uploaded_documents", "processing_stage")
    _set_not_null("uploaded_documents", "cleanup_status")
    _create_index_if_missing("uploaded_documents", "ix_uploaded_documents_role_type", ["role_type"])
    _create_index_if_missing("uploaded_documents", "ix_uploaded_documents_processing_stage", ["processing_stage"])
    _create_index_if_missing("uploaded_documents", "ix_uploaded_documents_cleanup_status", ["cleanup_status"])


def _seed_domains(bind) -> None:
    for name, description in DEFAULT_DOMAINS:
        bind.execute(
            text(
                """
                INSERT INTO compliance_domains (id, name, description)
                VALUES (gen_random_uuid(), :name, :description)
                ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description
                """
            ),
            {"name": name, "description": description},
        )


def _create_compatibility_views(bind) -> None:
    inspector = inspect(bind)
    tables = set(inspector.get_table_names(schema="public"))
    views = set(inspector.get_view_names(schema="public"))
    if "documents" not in tables:
        bind.execute(
            text(
                """
                CREATE OR REPLACE VIEW documents AS
                SELECT
                    id,
                    user_id,
                    title,
                    domain,
                    role_type,
                    source_type,
                    file_name,
                    file_type,
                    s3_key,
                    qdrant_collection,
                    extracted_text,
                    upload_status,
                    processing_stage,
                    created_at
                FROM uploaded_documents
                """
            )
        )
    if "reports" not in tables:
        bind.execute(
            text(
                """
                CREATE OR REPLACE VIEW reports AS
                SELECT
                    id,
                    audit_id,
                    summary,
                    report_payload,
                    report_json_s3_uri,
                    created_at
                FROM audit_reports
                """
            )
        )


def _create_index_if_missing(table_name: str, index_name: str, columns: list[str]) -> None:
    existing = {index["name"] for index in inspect(op.get_bind()).get_indexes(table_name, schema="public")}
    if index_name not in existing:
        op.create_index(index_name, table_name, columns)
