"""add bulk upload batch tracking tables

Revision ID: 20260531_0007
Revises: 20260528_0006
Create Date: 2026-05-31
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260531_0007"
down_revision = "20260528_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tables = _tables()

    if "upload_batches" not in tables:
        op.create_table(
            "upload_batches",
            sa.Column("id", sa.Uuid(as_uuid=False), nullable=False),
            sa.Column("user_id", sa.Uuid(as_uuid=False), nullable=False),
            sa.Column("module", sa.String(length=50), nullable=False, server_default="compliance_check"),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="queued"),
            sa.Column("total_documents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("completed_documents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("failed_documents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("running_document", sa.String(length=512), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _create_index_if_missing("upload_batches", "ix_upload_batches_user_id", ["user_id"])
        _create_index_if_missing("upload_batches", "ix_upload_batches_status", ["status"])

    if "batch_documents" not in tables:
        op.create_table(
            "batch_documents",
            sa.Column("id", sa.Uuid(as_uuid=False), nullable=False),
            sa.Column("batch_id", sa.Uuid(as_uuid=False), nullable=False),
            sa.Column("document_id", sa.Uuid(as_uuid=False), nullable=True),
            sa.Column("audit_id", sa.Uuid(as_uuid=False), nullable=True),
            sa.Column("filename", sa.String(length=512), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("domain", sa.String(length=100), nullable=True),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="queued"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("processing_time_seconds", sa.Float(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["audit_id"], ["audit_runs.id"]),
            sa.ForeignKeyConstraint(["batch_id"], ["upload_batches.id"]),
            sa.ForeignKeyConstraint(["document_id"], ["uploaded_documents.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _create_index_if_missing("batch_documents", "ix_batch_documents_batch_id", ["batch_id"])
        _create_index_if_missing("batch_documents", "ix_batch_documents_document_id", ["document_id"])
        _create_index_if_missing("batch_documents", "ix_batch_documents_audit_id", ["audit_id"])
        _create_index_if_missing("batch_documents", "ix_batch_documents_status", ["status"])
    else:
        _add_column_if_missing("batch_documents", sa.Column("domain", sa.String(length=100), nullable=True))

    if "rule_upload_batches" not in tables:
        op.create_table(
            "rule_upload_batches",
            sa.Column("id", sa.Uuid(as_uuid=False), nullable=False),
            sa.Column("user_id", sa.Uuid(as_uuid=False), nullable=False),
            sa.Column("module", sa.String(length=50), nullable=False, server_default="rule_management"),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="queued"),
            sa.Column("total_documents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("completed_documents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("failed_documents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("running_document", sa.String(length=512), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _create_index_if_missing("rule_upload_batches", "ix_rule_upload_batches_user_id", ["user_id"])
        _create_index_if_missing("rule_upload_batches", "ix_rule_upload_batches_status", ["status"])

    if "rule_upload_batch_items" not in tables:
        op.create_table(
            "rule_upload_batch_items",
            sa.Column("id", sa.Uuid(as_uuid=False), nullable=False),
            sa.Column("batch_id", sa.Uuid(as_uuid=False), nullable=False),
            sa.Column("rule_document_id", sa.Uuid(as_uuid=False), nullable=True),
            sa.Column("filename", sa.String(length=512), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="queued"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("processing_time_seconds", sa.Float(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["batch_id"], ["rule_upload_batches.id"]),
            sa.ForeignKeyConstraint(["rule_document_id"], ["rule_documents.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _create_index_if_missing("rule_upload_batch_items", "ix_rule_upload_batch_items_batch_id", ["batch_id"])
        _create_index_if_missing("rule_upload_batch_items", "ix_rule_upload_batch_items_rule_document_id", ["rule_document_id"])
        _create_index_if_missing("rule_upload_batch_items", "ix_rule_upload_batch_items_status", ["status"])


def downgrade() -> None:
    # Data-preserving migration: do not drop operational batch history.
    pass


def _tables() -> set[str]:
    inspector = inspect(op.get_bind())
    try:
        names = inspector.get_table_names(schema="public")
    except Exception:
        names = inspector.get_table_names()
    return set(names)


def _create_index_if_missing(table_name: str, index_name: str, columns: list[str]) -> None:
    inspector = inspect(op.get_bind())
    try:
        existing = {index["name"] for index in inspector.get_indexes(table_name, schema="public")}
    except Exception:
        existing = {index["name"] for index in inspector.get_indexes(table_name)}
    if index_name not in existing:
        op.create_index(index_name, table_name, columns)


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    inspector = inspect(op.get_bind())
    try:
        existing = {item["name"] for item in inspector.get_columns(table_name, schema="public")}
    except Exception:
        existing = {item["name"] for item in inspector.get_columns(table_name)}
    if column.name not in existing:
        op.add_column(table_name, column)
