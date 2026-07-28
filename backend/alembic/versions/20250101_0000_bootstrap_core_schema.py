"""bootstrap core schema

Revision ID: 20250101_0000
Revises:
Create Date: 2025-01-01

Bootstrap revision. Creates the *core* tables that predate Alembic in this
project -- they were originally applied by hand from
``app/database/migrations/001_optimized_schema.sql`` and never captured in a
revision. Without this, ``alembic upgrade head`` on an empty database fails
immediately: 20260506_0001 declares ``REFERENCES users(id)`` and nothing had
created ``users``.

Tables created here (everything in ``app.database.models`` that is NOT owned by
a later revision):

    users, tickers, daily_ohlcv, stock_fundamentals, dividends, stock_splits,
    failed_tickers, population_progress, watchlists

Owned by later revisions, therefore deliberately absent here:
ai_stock_reports / ai_usage_events (20260506_0001), email_preferences /
email_send_log (20260721_0001), insider_transactions (20260721_0002),
earnings_events / macro_observations (20260721_0003).

Two things to know about this file:

1. ``models.py`` is the source of truth, NOT 001_optimized_schema.sql, which is
   stale. The DDL below is a verbatim transcription of what
   ``Base.metadata.create_all()`` emits on PostgreSQL (timestamptz rather than
   naive timestamp, ``ix_*`` index names, ``users.tier`` plus the four Stripe
   billing columns, ``population_progress.batch_number`` as SERIAL). Keeping it
   byte-compatible with create_all is what makes the two documented bootstrap
   paths converge on an identical schema.

2. Every statement is idempotent (IF NOT EXISTS). Long-lived databases were
   built by hand and may already have some or all of these tables; running this
   revision against them must be a no-op rather than an error. Note that
   ``CREATE TABLE IF NOT EXISTS`` will not reconcile an existing table whose
   columns differ -- later revisions handle column-level drift (see
   20260726_0004 for the Stripe columns).

The production database is stamped at 20260506_0001, i.e. already past this
revision, so this never executes there.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20250101_0000"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Each entry is a single DDL statement, executed in dependency order
# (tickers/users first, then everything that references them).
STATEMENTS: Sequence[str] = (
    # ------------------------------------------------------------------
    # users
    # ------------------------------------------------------------------
    """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL NOT NULL,
        email VARCHAR(255) NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        tier VARCHAR(20),
        is_active BOOLEAN,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
        stripe_customer_id VARCHAR(64),
        stripe_subscription_id VARCHAR(64),
        subscription_status VARCHAR(32),
        subscription_current_period_end TIMESTAMP WITH TIME ZONE,
        PRIMARY KEY (id)
    )
    """,
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)",
    "CREATE INDEX IF NOT EXISTS ix_users_id ON users (id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_stripe_customer_id ON users (stripe_customer_id)",
    "CREATE INDEX IF NOT EXISTS ix_users_stripe_subscription_id ON users (stripe_subscription_id)",
    # ------------------------------------------------------------------
    # tickers
    # ------------------------------------------------------------------
    """
    CREATE TABLE IF NOT EXISTS tickers (
        id SMALLSERIAL NOT NULL,
        symbol VARCHAR(10) NOT NULL,
        name VARCHAR(255),
        exchange VARCHAR(20),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
        PRIMARY KEY (id)
    )
    """,
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_tickers_symbol ON tickers (symbol)",
    # ------------------------------------------------------------------
    # daily_ohlcv
    # ------------------------------------------------------------------
    """
    CREATE TABLE IF NOT EXISTS daily_ohlcv (
        ticker_id SMALLINT NOT NULL,
        date DATE NOT NULL,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume BIGINT,
        PRIMARY KEY (ticker_id, date),
        FOREIGN KEY(ticker_id) REFERENCES tickers (id) ON DELETE CASCADE
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_ohlcv_date ON daily_ohlcv (date)",
    "CREATE INDEX IF NOT EXISTS idx_ohlcv_ticker ON daily_ohlcv (ticker_id)",
    # ------------------------------------------------------------------
    # stock_fundamentals
    # ------------------------------------------------------------------
    """
    CREATE TABLE IF NOT EXISTS stock_fundamentals (
        ticker_id SMALLINT NOT NULL,
        pe_ratio REAL,
        forward_pe REAL,
        peg_ratio REAL,
        price_to_book REAL,
        price_to_sales REAL,
        ev_to_ebitda REAL,
        profit_margin REAL,
        operating_margin REAL,
        roe REAL,
        roa REAL,
        debt_to_equity REAL,
        current_ratio REAL,
        quick_ratio REAL,
        revenue_growth REAL,
        earnings_growth REAL,
        dividend_yield REAL,
        dividend_rate REAL,
        payout_ratio REAL,
        market_cap BIGINT,
        volume BIGINT,
        avg_volume BIGINT,
        beta REAL,
        current_price REAL,
        day_change_percent REAL,
        fifty_two_week_high REAL,
        fifty_two_week_low REAL,
        sector VARCHAR(100),
        industry VARCHAR(100),
        additional_data JSONB,
        last_updated TIMESTAMP WITH TIME ZONE DEFAULT now(),
        PRIMARY KEY (ticker_id),
        FOREIGN KEY(ticker_id) REFERENCES tickers (id) ON DELETE CASCADE
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_stock_fundamentals_debt_to_equity ON stock_fundamentals (debt_to_equity)",
    "CREATE INDEX IF NOT EXISTS ix_stock_fundamentals_dividend_yield ON stock_fundamentals (dividend_yield)",
    "CREATE INDEX IF NOT EXISTS ix_stock_fundamentals_market_cap ON stock_fundamentals (market_cap)",
    "CREATE INDEX IF NOT EXISTS ix_stock_fundamentals_pe_ratio ON stock_fundamentals (pe_ratio)",
    "CREATE INDEX IF NOT EXISTS ix_stock_fundamentals_roe ON stock_fundamentals (roe)",
    "CREATE INDEX IF NOT EXISTS ix_stock_fundamentals_sector ON stock_fundamentals (sector)",
    # ------------------------------------------------------------------
    # dividends
    # ------------------------------------------------------------------
    """
    CREATE TABLE IF NOT EXISTS dividends (
        ticker_id SMALLINT NOT NULL,
        date DATE NOT NULL,
        amount REAL NOT NULL,
        PRIMARY KEY (ticker_id, date),
        FOREIGN KEY(ticker_id) REFERENCES tickers (id) ON DELETE CASCADE
    )
    """,
    # ------------------------------------------------------------------
    # stock_splits
    # ------------------------------------------------------------------
    """
    CREATE TABLE IF NOT EXISTS stock_splits (
        ticker_id SMALLINT NOT NULL,
        date DATE NOT NULL,
        ratio REAL NOT NULL,
        PRIMARY KEY (ticker_id, date),
        FOREIGN KEY(ticker_id) REFERENCES tickers (id) ON DELETE CASCADE
    )
    """,
    # ------------------------------------------------------------------
    # failed_tickers
    # ------------------------------------------------------------------
    """
    CREATE TABLE IF NOT EXISTS failed_tickers (
        id SERIAL NOT NULL,
        ticker VARCHAR(10) NOT NULL,
        batch_number INTEGER,
        error_message TEXT,
        retry_count INTEGER,
        last_attempt TIMESTAMP WITH TIME ZONE DEFAULT now(),
        status VARCHAR(20),
        PRIMARY KEY (id)
    )
    """,
    # ------------------------------------------------------------------
    # population_progress
    # ------------------------------------------------------------------
    """
    CREATE TABLE IF NOT EXISTS population_progress (
        batch_number SERIAL NOT NULL,
        ticker_list VARCHAR[],
        start_time TIMESTAMP WITH TIME ZONE,
        end_time TIMESTAMP WITH TIME ZONE,
        status VARCHAR(20),
        error_message TEXT,
        records_inserted INTEGER,
        PRIMARY KEY (batch_number)
    )
    """,
    # ------------------------------------------------------------------
    # watchlists
    # ------------------------------------------------------------------
    """
    CREATE TABLE IF NOT EXISTS watchlists (
        id SERIAL NOT NULL,
        user_id INTEGER NOT NULL,
        ticker_id SMALLINT NOT NULL,
        added_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
        PRIMARY KEY (id),
        FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY(ticker_id) REFERENCES tickers (id) ON DELETE CASCADE
    )
    """,
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_user_ticker ON watchlists (user_id, ticker_id)",
    "CREATE INDEX IF NOT EXISTS ix_watchlists_id ON watchlists (id)",
    "CREATE INDEX IF NOT EXISTS ix_watchlists_user_id ON watchlists (user_id)",
)


def upgrade() -> None:
    for statement in STATEMENTS:
        op.execute(statement.strip())


def downgrade() -> None:
    # Intentionally a no-op.
    #
    # Downgrading past the bootstrap would mean dropping users, watchlists and
    # every price/fundamental row in the database. There is no situation where
    # an automated downgrade should do that. Tear a database down by dropping
    # the database itself, deliberately, not by walking Alembic backwards.
    pass
