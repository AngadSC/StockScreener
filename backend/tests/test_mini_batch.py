"""
Test 4: Mini batch job (live end-to-end probe)

Simulates the real bulk population job at small scale: one year of daily data
for 10 stocks through YFinanceProvider, then a read-only check that the
database has the tables the job would write into.

This hits Yahoo for real and connects to whatever DATABASE_URL is configured
(read-only: SELECT 1 and a pg_tables lookup, nothing is written), so it is
skipped unless explicitly enabled. Two equivalent ways to opt in:

    RUN_LIVE_MARKET_DATA_TESTS=1 pytest tests/test_mini_batch.py -s
    python tests/test_mini_batch.py          # same, with output shown

The env var replaces the interactive "Continue? (yes/no)" prompt this file used
to have -- that prompt made the module unimportable under pytest, which took
collection of the whole suite down with it.
"""

import os
import sys
from datetime import datetime, timedelta

import pytest

LIVE_ENV_VAR = "RUN_LIVE_MARKET_DATA_TESTS"

pytestmark = pytest.mark.skipif(
    os.getenv(LIVE_ENV_VAR) != "1",
    reason=f"hits the live Yahoo API and a real database; set {LIVE_ENV_VAR}=1 to run",
)

TEST_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
    "TSLA", "META", "BRK-B", "UNH", "JNJ",
]
HISTORY_DAYS = 365
REQUIRED_TABLES = {"tickers", "daily_ohlcv"}


# App imports live inside fixtures rather than at module scope: this module is
# skipped by default, and collecting it should not require a populated .env or
# a working provider import.

@pytest.fixture(scope="module")
def provider():
    from app.providers.yfinance_provider import YFinanceProvider

    return YFinanceProvider()


@pytest.fixture(scope="module")
def database_url():
    from app.config import settings

    return settings.DATABASE_URL


@pytest.fixture(scope="module")
def batch_prices(provider):
    """One year of daily bars for 10 stocks, fetched once for the module."""
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=HISTORY_DAYS)

    df = provider.get_batch_historical_prices(
        tickers=TEST_TICKERS,
        start_date=start_date,
        end_date=end_date,
        is_bulk_load=True,  # longer jitter, same as the real population job
    )

    assert df is not None and not df.empty, "provider returned no data for the mini batch"
    return df


def test_batch_historical_prices(batch_prices):
    """4.1 A year of data for 10 stocks comes back in the expected shape."""
    df = batch_prices

    print(f"\n   Shape: {df.shape}")
    print(f"   Columns: {list(df.columns)}")
    print(f"   Date range: {df['date'].min()} to {df['date'].max()}")

    records_per_ticker = df.groupby("ticker").size()
    print("   Records per ticker:")
    for ticker, count in records_per_ticker.items():
        print(f"     {ticker}: {count}")
    print(df.head(10))

    assert {"date", "ticker"} <= set(df.columns)

    returned = set(df["ticker"].unique())
    assert returned <= set(TEST_TICKERS), f"unexpected tickers in result: {returned - set(TEST_TICKERS)}"
    assert returned == set(TEST_TICKERS), f"missing tickers: {sorted(set(TEST_TICKERS) - returned)}"


def test_required_tables_exist(database_url):
    """4.2 The database the job writes into actually has its tables.

    Read-only. Skips (rather than fails) when no database is reachable, since
    the fetch above is the part that matters and a dev box may have none.
    """
    from sqlalchemy import create_engine, text

    engine = create_engine(database_url)

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - any connection failure means "no database here"
        pytest.skip(f"no database reachable at DATABASE_URL: {exc}")

    with engine.connect() as conn:
        result = conn.execute(
            text(
                """
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename IN ('tickers', 'daily_ohlcv')
                """
            )
        )
        tables = {row[0] for row in result}

    print(f"\n   Found: {sorted(tables)}")
    missing = REQUIRED_TABLES - tables
    assert not missing, f"required tables missing (run migrations first): {sorted(missing)}"


if __name__ == "__main__":
    # Manual usage: `python tests/test_mini_batch.py` runs the live checks with
    # output shown, the way this file was originally used as a script.
    os.environ[LIVE_ENV_VAR] = "1"
    sys.exit(pytest.main([__file__, "-v", "-s"]))
