"""add users stripe billing columns

Revision ID: 20260726_0004
Revises: 20260721_0003
Create Date: 2026-07-26

Brings ``app/database/migrations/002_stripe_billing.sql`` under Alembic control.

Those four columns were only ever applied by hand, so they existed in the
production database but in no revision. Any database rebuilt purely from
Alembic would come up without them and fail every authenticated request the
moment ``User`` was loaded.

This revision is a belt-and-braces safety net and is expected to be a no-op
almost everywhere:

  * production already has the columns and both indexes (hand-applied), and
  * a database built from the 20250101_0000 bootstrap already has the columns,
    because models.py declares them.

The one case it actually does work is a database created from the stale
001_optimized_schema.sql and stamped forward without 002 ever being run.

Everything below is therefore written to be safely re-runnable.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260726_0004"
down_revision: Union[str, None] = "20260721_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ADD_COLUMNS = """
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS subscription_status VARCHAR(32),
    ADD COLUMN IF NOT EXISTS subscription_current_period_end TIMESTAMP WITH TIME ZONE
"""

# The partial indexes from 002_stripe_billing.sql, but only created when the
# column is not already indexed. Plain CREATE INDEX IF NOT EXISTS keys off the
# index *name*, which would happily add a second, redundant index alongside the
# ix_users_stripe_* indexes the bootstrap revision creates from models.py. The
# guard below keys off the column instead, so every path ends up with exactly
# one index per column.
CREATE_INDEXES = """
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_index i
        JOIN pg_class t ON t.oid = i.indrelid
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(i.indkey)
        WHERE t.relname = 'users' AND a.attname = 'stripe_customer_id'
    ) THEN
        CREATE UNIQUE INDEX idx_users_stripe_customer_id
            ON users(stripe_customer_id)
            WHERE stripe_customer_id IS NOT NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_index i
        JOIN pg_class t ON t.oid = i.indrelid
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(i.indkey)
        WHERE t.relname = 'users' AND a.attname = 'stripe_subscription_id'
    ) THEN
        CREATE INDEX idx_users_stripe_subscription_id
            ON users(stripe_subscription_id)
            WHERE stripe_subscription_id IS NOT NULL;
    END IF;
END
$$;
"""


def upgrade() -> None:
    op.execute(ADD_COLUMNS.strip())
    op.execute(CREATE_INDEXES.strip())


def downgrade() -> None:
    # Intentionally a no-op.
    #
    # Dropping these columns would discard the Stripe customer / subscription
    # linkage for every paying user, which is not recoverable from our side.
    pass
