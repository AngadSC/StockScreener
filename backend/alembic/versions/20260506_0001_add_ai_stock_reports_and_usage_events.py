"""add ai stock reports and usage events

Revision ID: 20260506_0001
Revises: 20250101_0000
Create Date: 2026-05-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260506_0001"
# Re-parented onto the bootstrap revision: this migration references users(id),
# so on an empty database the core tables must exist first. Production is
# stamped at this revision and Alembic only walks forward from a stamp, so the
# bootstrap never re-runs there.
down_revision: Union[str, None] = "20250101_0000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_stock_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(length=10), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("tier_used", sa.String(length=20), nullable=True),
        sa.Column("report_type", sa.String(length=50), nullable=False),
        sa.Column("swing_bias", sa.String(length=20), nullable=True),
        sa.Column("setup_type", sa.String(length=50), nullable=True),
        sa.Column("setup_quality_score", sa.REAL(), nullable=True),
        sa.Column("entry_timing_score", sa.REAL(), nullable=True),
        sa.Column("technical_score", sa.REAL(), nullable=True),
        sa.Column("fundamental_score", sa.REAL(), nullable=True),
        sa.Column("sentiment_score", sa.REAL(), nullable=True),
        sa.Column("valuation_score", sa.REAL(), nullable=True),
        sa.Column("risk_score", sa.REAL(), nullable=True),
        sa.Column("ai_report", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("input_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("sources", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_stock_reports_id", "ai_stock_reports", ["id"], unique=False)
    op.create_index("ix_ai_stock_reports_user_id", "ai_stock_reports", ["user_id"], unique=False)
    op.create_index("ix_ai_stock_reports_ticker", "ai_stock_reports", ["ticker"], unique=False)
    op.create_index("ix_ai_stock_reports_report_date", "ai_stock_reports", ["report_date"], unique=False)
    op.create_index("ix_ai_stock_reports_report_type", "ai_stock_reports", ["report_type"], unique=False)
    op.create_index(
        "idx_ai_stock_reports_user_ticker_date",
        "ai_stock_reports",
        ["user_id", "ticker", "report_date"],
        unique=False,
    )

    op.create_table(
        "ai_usage_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(length=10), nullable=True),
        sa.Column("report_type", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("model_used", sa.String(length=100), nullable=True),
        sa.Column("tokens_input", sa.Integer(), nullable=True),
        sa.Column("tokens_output", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_usage_events_id", "ai_usage_events", ["id"], unique=False)
    op.create_index("ix_ai_usage_events_user_id", "ai_usage_events", ["user_id"], unique=False)
    op.create_index("ix_ai_usage_events_ticker", "ai_usage_events", ["ticker"], unique=False)
    op.create_index("ix_ai_usage_events_report_type", "ai_usage_events", ["report_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ai_usage_events_report_type", table_name="ai_usage_events")
    op.drop_index("ix_ai_usage_events_ticker", table_name="ai_usage_events")
    op.drop_index("ix_ai_usage_events_user_id", table_name="ai_usage_events")
    op.drop_index("ix_ai_usage_events_id", table_name="ai_usage_events")
    op.drop_table("ai_usage_events")

    op.drop_index("idx_ai_stock_reports_user_ticker_date", table_name="ai_stock_reports")
    op.drop_index("ix_ai_stock_reports_report_type", table_name="ai_stock_reports")
    op.drop_index("ix_ai_stock_reports_report_date", table_name="ai_stock_reports")
    op.drop_index("ix_ai_stock_reports_ticker", table_name="ai_stock_reports")
    op.drop_index("ix_ai_stock_reports_user_id", table_name="ai_stock_reports")
    op.drop_index("ix_ai_stock_reports_id", table_name="ai_stock_reports")
    op.drop_table("ai_stock_reports")
