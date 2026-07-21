"""add earnings events and macro observations

Revision ID: 20260721_0001
Revises: 20260506_0001
Create Date: 2026-07-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260721_0001"
down_revision: Union[str, None] = "20260506_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "earnings_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticker_id", sa.SmallInteger(), nullable=False),
        sa.Column("earnings_date", sa.Date(), nullable=False),
        sa.Column("time_hint", sa.String(length=16), nullable=True, server_default="unknown"),
        sa.Column("eps_estimate", sa.REAL(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["ticker_id"], ["tickers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_earnings_events_id", "earnings_events", ["id"], unique=False)
    op.create_index("ix_earnings_events_ticker_id", "earnings_events", ["ticker_id"], unique=False)
    op.create_index("ix_earnings_events_earnings_date", "earnings_events", ["earnings_date"], unique=False)
    op.create_index(
        "idx_earnings_events_ticker_date",
        "earnings_events",
        ["ticker_id", "earnings_date"],
        unique=True,
    )

    op.create_table(
        "macro_observations",
        sa.Column("series_id", sa.String(length=20), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("value", sa.REAL(), nullable=True),
        sa.PrimaryKeyConstraint("series_id", "date"),
    )


def downgrade() -> None:
    op.drop_table("macro_observations")

    op.drop_index("idx_earnings_events_ticker_date", table_name="earnings_events")
    op.drop_index("ix_earnings_events_earnings_date", table_name="earnings_events")
    op.drop_index("ix_earnings_events_ticker_id", table_name="earnings_events")
    op.drop_index("ix_earnings_events_id", table_name="earnings_events")
    op.drop_table("earnings_events")
