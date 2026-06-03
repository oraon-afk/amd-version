"""add digital twin, durable queue metadata, diagnostics, and rule lifecycle

Revision ID: 20260601_0008
Revises: 20260531_0007
Create Date: 2026-06-01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260601_0008"
down_revision = "20260531_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tables = _tables()

    if "compliance_digital_twins" not in tables:
        op.create_table(
            "compliance_digital_twins",
            sa.Column("id", sa.Uuid(as_uuid=False), nullable=False),
            sa.Column("user_id", sa.Uuid(as_uuid=False), nullable=True),
            sa.Column("name", sa.String(length=255), nullable=False, server_default="Organization Compliance Twin"),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
            sa.Column("maturity_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("coverage_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("risk_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("missing_policies", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("risk_heatmap", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("policy_inventory", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("summary", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("generated_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _create_index_if_missing("compliance_digital_twins", "ix_compliance_digital_twins_user_id", ["user_id"])
        _create_index_if_missing("compliance_digital_twins", "ix_compliance_digital_twins_status", ["status"])

    if "compliance_twin_policy_profiles" not in tables:
        op.create_table(
            "compliance_twin_policy_profiles",
            sa.Column("id", sa.Uuid(as_uuid=False), nullable=False),
            sa.Column("twin_id", sa.Uuid(as_uuid=False), nullable=False),
            sa.Column("document_id", sa.Uuid(as_uuid=False), nullable=False),
            sa.Column("latest_audit_id", sa.Uuid(as_uuid=False), nullable=True),
            sa.Column("latest_report_id", sa.Uuid(as_uuid=False), nullable=True),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("domain", sa.String(length=100), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False),
            sa.Column("compliance_score", sa.Float(), nullable=True),
            sa.Column("risk_level", sa.String(length=30), nullable=True),
            sa.Column("findings_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("coverage_status", sa.String(length=50), nullable=False, server_default="covered"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["document_id"], ["uploaded_documents.id"]),
            sa.ForeignKeyConstraint(["latest_audit_id"], ["audit_runs.id"]),
            sa.ForeignKeyConstraint(["latest_report_id"], ["audit_reports.id"]),
            sa.ForeignKeyConstraint(["twin_id"], ["compliance_digital_twins.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _create_index_if_missing("compliance_twin_policy_profiles", "ix_compliance_twin_policy_profiles_twin_id", ["twin_id"])
        _create_index_if_missing("compliance_twin_policy_profiles", "ix_compliance_twin_policy_profiles_document_id", ["document_id"])
        _create_index_if_missing("compliance_twin_policy_profiles", "ix_compliance_twin_policy_profiles_domain", ["domain"])
        _create_index_if_missing("compliance_twin_policy_profiles", "ix_compliance_twin_policy_profiles_latest_audit_id", ["latest_audit_id"])
        _create_index_if_missing("compliance_twin_policy_profiles", "ix_compliance_twin_policy_profiles_latest_report_id", ["latest_report_id"])

    if "compliance_twin_snapshots" not in tables:
        op.create_table(
            "compliance_twin_snapshots",
            sa.Column("id", sa.Uuid(as_uuid=False), nullable=False),
            sa.Column("twin_id", sa.Uuid(as_uuid=False), nullable=False),
            sa.Column("maturity_score", sa.Float(), nullable=False),
            sa.Column("coverage_score", sa.Float(), nullable=False),
            sa.Column("risk_score", sa.Float(), nullable=False),
            sa.Column("total_policies", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("missing_policy_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("high_risk_policy_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("summary_text", sa.Text(), nullable=False),
            sa.Column("snapshot_payload", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["twin_id"], ["compliance_digital_twins.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _create_index_if_missing("compliance_twin_snapshots", "ix_compliance_twin_snapshots_twin_id", ["twin_id"])

    if "compliance_score_diagnostics" not in tables:
        op.create_table(
            "compliance_score_diagnostics",
            sa.Column("id", sa.Uuid(as_uuid=False), nullable=False),
            sa.Column("audit_id", sa.Uuid(as_uuid=False), nullable=False),
            sa.Column("report_id", sa.Uuid(as_uuid=False), nullable=True),
            sa.Column("rules_evaluated", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("rules_matched", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("rules_failed", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("match_confidence", sa.Float(), nullable=True),
            sa.Column("score_reasoning", sa.Text(), nullable=False),
            sa.Column("diagnostics_payload", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["audit_id"], ["audit_runs.id"]),
            sa.ForeignKeyConstraint(["report_id"], ["audit_reports.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _create_index_if_missing("compliance_score_diagnostics", "ix_compliance_score_diagnostics_audit_id", ["audit_id"])
        _create_index_if_missing("compliance_score_diagnostics", "ix_compliance_score_diagnostics_report_id", ["report_id"])

    _add_column_if_missing("upload_batches", sa.Column("processed_documents", sa.Integer(), nullable=False, server_default="0"))
    _add_column_if_missing("upload_batches", sa.Column("summary_report", sa.JSON(), nullable=True))
    _add_column_if_missing("batch_documents", sa.Column("content_type", sa.String(length=120), nullable=False, server_default="application/octet-stream"))
    _add_column_if_missing("batch_documents", sa.Column("staging_path", sa.String(length=1024), nullable=True))
    _add_column_if_missing("batch_documents", sa.Column("file_size_bytes", sa.Integer(), nullable=False, server_default="0"))
    _add_column_if_missing("batch_documents", sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
    _add_column_if_missing("batch_documents", sa.Column("max_retries", sa.Integer(), nullable=False, server_default="2"))
    _add_column_if_missing("batch_documents", sa.Column("last_error_at", sa.DateTime(), nullable=True))
    _add_column_if_missing("rule_upload_batches", sa.Column("processed_documents", sa.Integer(), nullable=False, server_default="0"))
    _add_column_if_missing("rule_upload_batches", sa.Column("summary_report", sa.JSON(), nullable=True))
    _add_column_if_missing("rule_upload_batch_items", sa.Column("content_type", sa.String(length=120), nullable=False, server_default="application/octet-stream"))
    _add_column_if_missing("rule_upload_batch_items", sa.Column("staging_path", sa.String(length=1024), nullable=True))
    _add_column_if_missing("rule_upload_batch_items", sa.Column("file_size_bytes", sa.Integer(), nullable=False, server_default="0"))
    _add_column_if_missing("rule_upload_batch_items", sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
    _add_column_if_missing("rule_upload_batch_items", sa.Column("max_retries", sa.Integer(), nullable=False, server_default="2"))
    _add_column_if_missing("rule_upload_batch_items", sa.Column("last_error_at", sa.DateTime(), nullable=True))
    _add_column_if_missing("compliance_rules", sa.Column("status", sa.String(length=50), nullable=False, server_default="active"))


def downgrade() -> None:
    # Data-preserving migration: keep history, queue state, diagnostics, and Twin snapshots.
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
