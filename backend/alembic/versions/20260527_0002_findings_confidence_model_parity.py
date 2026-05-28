"""add findings confidence model parity column

Revision ID: 20260527_0002
Revises: 20260527_0001
Create Date: 2026-05-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


revision = "20260527_0002"
down_revision = "20260527_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("findings", schema="public")}
    if "confidence" not in columns:
        op.add_column("findings", sa.Column("confidence", sa.Float(), nullable=True))
        bind.execute(text("UPDATE findings SET confidence = COALESCE(confidence_score, 0.0) WHERE confidence IS NULL"))
        op.alter_column("findings", "confidence", existing_type=sa.Float(), nullable=False)


def downgrade() -> None:
    # Production data-preserving migration: no drops by design.
    pass
