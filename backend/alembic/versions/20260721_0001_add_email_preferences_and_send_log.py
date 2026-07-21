"""add email preferences and email send log

Revision ID: 20260721_0001
Revises: 20260506_0001
Create Date: 2026-07-21

Adds the email infrastructure foundation tables:
  - email_preferences: per-user category opt-in flags + unsubscribe token
  - email_send_log: per-attempt audit / idempotency log

NOTE: Parallel feature branches may create sibling heads off the same
down_revision (20260506_0001). Integration will merge them with a merge
revision; that is expected.
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
        "email_preferences",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("daily_brief", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("watchlist_digest", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("weekly_recap", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("product_updates", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("unsubscribe_token", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index(
        "ix_email_preferences_unsubscribe_token",
        "email_preferences",
        ["unsubscribe_token"],
        unique=True,
    )

    op.create_table(
        "email_send_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("sent_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("provider_message_id", sa.String(length=64), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_send_log_id", "email_send_log", ["id"], unique=False)
    op.create_index("ix_email_send_log_user_id", "email_send_log", ["user_id"], unique=False)
    op.create_index(
        "idx_email_send_log_user_category_date",
        "email_send_log",
        ["user_id", "category", "sent_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_email_send_log_user_category_date", table_name="email_send_log")
    op.drop_index("ix_email_send_log_user_id", table_name="email_send_log")
    op.drop_index("ix_email_send_log_id", table_name="email_send_log")
    op.drop_table("email_send_log")

    op.drop_index("ix_email_preferences_unsubscribe_token", table_name="email_preferences")
    op.drop_table("email_preferences")
