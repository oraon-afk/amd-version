"""document ingestion and compliance pipeline schema

Revision ID: 20260527_0001
Revises:
Create Date: 2026-05-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


revision = "20260527_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names(schema="public"))

    bind.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))

    if "compliance_domains" not in tables:
        op.create_table(
            "compliance_domains",
            sa.Column("id", sa.Uuid(as_uuid=False), server_default=sa.text("gen_random_uuid()"), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name", name="uq_compliance_domains_name"),
        )
        op.create_index("ix_compliance_domains_name", "compliance_domains", ["name"])

    if "document_chunks" not in tables:
        op.create_table(
            "document_chunks",
            sa.Column("id", sa.Uuid(as_uuid=False), server_default=sa.text("gen_random_uuid()"), nullable=False),
            sa.Column("document_id", sa.Uuid(as_uuid=False), nullable=False),
            sa.Column("chunk_index", sa.Integer(), nullable=False),
            sa.Column("chunk_text", sa.Text(), nullable=False),
            sa.Column("embedding_model", sa.String(length=255), nullable=False),
            sa.Column("vector_id", sa.String(length=128), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["document_id"], ["uploaded_documents.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
        op.create_index("ix_document_chunks_created_at", "document_chunks", ["created_at"])

    _add_uploaded_document_columns(bind)
    _add_finding_columns(bind)
    _create_indexes(bind)


def downgrade() -> None:
    # Production data-preserving migration: no drops by design.
    pass


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in inspect(op.get_bind()).get_columns(table_name, schema="public")}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if column.name not in _columns(table_name):
        op.add_column(table_name, column)


def _add_uploaded_document_columns(bind) -> None:
    _add_column_if_missing("uploaded_documents", sa.Column("title", sa.String(length=255), nullable=True))
    _add_column_if_missing("uploaded_documents", sa.Column("domain", sa.String(length=100), nullable=True))
    _add_column_if_missing("uploaded_documents", sa.Column("source_type", sa.String(length=50), nullable=True))
    _add_column_if_missing("uploaded_documents", sa.Column("s3_key", sa.String(length=1024), nullable=True))
    _add_column_if_missing("uploaded_documents", sa.Column("qdrant_collection", sa.String(length=100), nullable=True))
    _add_column_if_missing("uploaded_documents", sa.Column("upload_status", sa.String(length=50), nullable=True))
    _add_column_if_missing("uploaded_documents", sa.Column("file_name", sa.String(length=512), nullable=True))
    _add_column_if_missing("uploaded_documents", sa.Column("extracted_text", sa.Text(), nullable=True))

    bind.execute(
        text(
            """
            UPDATE uploaded_documents
            SET
                title = COALESCE(NULLIF(title, ''), NULLIF(filename, ''), 'Untitled document'),
                domain = COALESCE(NULLIF(domain, ''), 'general'),
                source_type = COALESCE(NULLIF(source_type, ''), 'file'),
                qdrant_collection = COALESCE(NULLIF(qdrant_collection, ''), 'audit_document_chunks'),
                upload_status = COALESCE(NULLIF(upload_status, ''), NULLIF(status, ''), 'uploaded'),
                file_name = COALESCE(NULLIF(file_name, ''), NULLIF(filename, ''))
            """
        )
    )

    _set_not_null_if_nullable("uploaded_documents", "title")
    _set_not_null_if_nullable("uploaded_documents", "domain")
    _set_not_null_if_nullable("uploaded_documents", "source_type")
    _set_not_null_if_nullable("uploaded_documents", "qdrant_collection")
    _set_not_null_if_nullable("uploaded_documents", "upload_status")


def _add_finding_columns(bind) -> None:
    _add_column_if_missing("findings", sa.Column("document_id", sa.Uuid(as_uuid=False), nullable=True))
    _add_column_if_missing("findings", sa.Column("evidence_text", sa.Text(), nullable=True))
    _add_column_if_missing("findings", sa.Column("citation_source", sa.Text(), nullable=True))

    bind.execute(
        text(
            """
            UPDATE findings AS f
            SET document_id = ar.document_id
            FROM audit_runs AS ar
            WHERE f.audit_id = ar.id
              AND f.document_id IS NULL
            """
        )
    )

    foreign_keys = {fk["name"] for fk in inspect(bind).get_foreign_keys("findings", schema="public")}
    if "fk_findings_document_id_uploaded_documents" not in foreign_keys:
        op.create_foreign_key(
            "fk_findings_document_id_uploaded_documents",
            "findings",
            "uploaded_documents",
            ["document_id"],
            ["id"],
            ondelete="SET NULL",
        )


def _set_not_null_if_nullable(table_name: str, column_name: str) -> None:
    column = next(
        column for column in inspect(op.get_bind()).get_columns(table_name, schema="public")
        if column["name"] == column_name
    )
    if column.get("nullable", True):
        op.alter_column(table_name, column_name, existing_type=column["type"], nullable=False)


def _create_indexes(bind) -> None:
    indexes = {
        table: {index["name"] for index in inspect(bind).get_indexes(table, schema="public")}
        for table in ("uploaded_documents", "document_chunks", "findings", "compliance_domains")
        if table in set(inspect(bind).get_table_names(schema="public"))
    }

    _create_index_if_missing(indexes, "uploaded_documents", "ix_uploaded_documents_user_id", ["user_id"])
    _create_index_if_missing(indexes, "uploaded_documents", "ix_uploaded_documents_domain", ["domain"])
    _create_index_if_missing(indexes, "uploaded_documents", "ix_uploaded_documents_created_at", ["created_at"])
    _create_index_if_missing(indexes, "uploaded_documents", "ix_uploaded_documents_upload_status", ["upload_status"])
    _create_index_if_missing(indexes, "document_chunks", "ix_document_chunks_document_id", ["document_id"])
    _create_index_if_missing(indexes, "document_chunks", "ix_document_chunks_created_at", ["created_at"])
    _create_index_if_missing(indexes, "findings", "ix_findings_document_id", ["document_id"])
    _create_index_if_missing(indexes, "findings", "ix_findings_created_at", ["created_at"])


def _create_index_if_missing(indexes: dict[str, set[str]], table_name: str, index_name: str, columns: list[str]) -> None:
    if index_name not in indexes.get(table_name, set()):
        op.create_index(index_name, table_name, columns)
