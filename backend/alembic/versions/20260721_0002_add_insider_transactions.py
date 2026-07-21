"""add insider transactions (SEC EDGAR Form 4)

Revision ID: 20260721_0002
Revises: 20260506_0001
Create Date: 2026-07-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260721_0002"
down_revision: Union[str, None] = "20260506_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "insider_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticker_id", sa.SmallInteger(), nullable=False),
        sa.Column("accession_no", sa.String(length=25), nullable=False),
        sa.Column("txn_index", sa.SmallInteger(), nullable=False),
        sa.Column("filed_date", sa.Date(), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=True),
        sa.Column("owner_name", sa.String(length=255), nullable=True),
        sa.Column("owner_title", sa.String(length=255), nullable=True),
        sa.Column("is_officer", sa.Boolean(), nullable=True),
        sa.Column("is_director", sa.Boolean(), nullable=True),
        sa.Column("transaction_code", sa.String(length=2), nullable=True),
        sa.Column("shares", sa.REAL(), nullable=True),
        sa.Column("price", sa.REAL(), nullable=True),
        sa.Column("value", sa.REAL(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["ticker_id"], ["tickers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_insider_transactions_ticker_id",
        "insider_transactions",
        ["ticker_id"],
        unique=False,
    )
    op.create_index(
        "ix_insider_transactions_accession_no",
        "insider_transactions",
        ["accession_no"],
        unique=False,
    )
    op.create_index(
        "ix_insider_transactions_filed_date",
        "insider_transactions",
        ["filed_date"],
        unique=False,
    )
    op.create_index(
        "uq_insider_accession_txn",
        "insider_transactions",
        ["accession_no", "txn_index"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_insider_accession_txn", table_name="insider_transactions")
    op.drop_index(
        "ix_insider_transactions_filed_date", table_name="insider_transactions"
    )
    op.drop_index(
        "ix_insider_transactions_accession_no", table_name="insider_transactions"
    )
    op.drop_index(
        "ix_insider_transactions_ticker_id", table_name="insider_transactions"
    )
    op.drop_table("insider_transactions")
