"""add supporting indexes for pipeline lookups

Revision ID: 20260528_0005
Revises: 20260528_0004
Create Date: 2026-05-28
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import inspect


revision = "20260528_0005"
down_revision = "20260528_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names(schema="public"))
    if "audit_runs" in tables:
        _create_index_if_missing("audit_runs", "ix_audit_runs_created_at", ["created_at"])
    if "rule_documents" in tables:
        _create_index_if_missing("rule_documents", "ix_rule_documents_domain", ["domain"])
        _create_index_if_missing("rule_documents", "ix_rule_documents_category", ["category"])
        _create_index_if_missing("rule_documents", "ix_rule_documents_created_at", ["created_at"])
    if "compliance_rules" in tables:
        _create_index_if_missing("compliance_rules", "ix_compliance_rules_created_at", ["created_at"])


def downgrade() -> None:
    # Production data-preserving migration: no drops by design.
    pass


def _create_index_if_missing(table_name: str, index_name: str, columns: list[str]) -> None:
    existing = {index["name"] for index in inspect(op.get_bind()).get_indexes(table_name, schema="public")}
    if index_name not in existing:
        op.create_index(index_name, table_name, columns)
