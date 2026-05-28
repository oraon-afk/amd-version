"""ensure audit_results exists for legacy reports foreign key

Revision ID: 20260528_0006
Revises: 20260528_0005
Create Date: 2026-05-28
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260528_0006"
down_revision = "20260528_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names(schema="public"))

    if "audit_results" not in tables:
        constraints = [
            sa.PrimaryKeyConstraint("id"),
        ]
        if "documents" in tables:
            constraints.append(
                sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
            )
        op.create_table(
            "audit_results",
            sa.Column("id", sa.Uuid(as_uuid=False), server_default=sa.text("gen_random_uuid()"), nullable=False),
            sa.Column("document_id", sa.Uuid(as_uuid=False), nullable=True),
            sa.Column("overall_risk", sa.Text(), nullable=True),
            sa.Column("confidence_score", sa.Float(), nullable=True),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
            *constraints,
        )
        tables.add("audit_results")
    else:
        _add_audit_result_columns()

    if "reports" in tables:
        _add_report_columns()
        _create_index_if_missing("reports", "ix_reports_audit_result_id", ["audit_result_id"])


def downgrade() -> None:
    # Production data-preserving migration: no drops by design.
    pass


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in inspect(op.get_bind()).get_columns(table_name, schema="public")}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if column.name not in _columns(table_name):
        op.add_column(table_name, column)


def _add_audit_result_columns() -> None:
    for column in [
        sa.Column("document_id", sa.Uuid(as_uuid=False), nullable=True),
        sa.Column("overall_risk", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    ]:
        _add_column_if_missing("audit_results", column)


def _add_report_columns() -> None:
    for column in [
        sa.Column("audit_result_id", sa.Uuid(as_uuid=False), nullable=True),
        sa.Column("audit_id", sa.Uuid(as_uuid=False), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("report_payload", sa.JSON(), nullable=True),
        sa.Column("report_json_s3_uri", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    ]:
        _add_column_if_missing("reports", column)


def _create_index_if_missing(table_name: str, index_name: str, columns: list[str]) -> None:
    existing = {index["name"] for index in inspect(op.get_bind()).get_indexes(table_name, schema="public")}
    if index_name not in existing:
        op.create_index(index_name, table_name, columns)
