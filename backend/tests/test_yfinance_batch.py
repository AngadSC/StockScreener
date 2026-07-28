"""
Test 2: Batch ticker download (live yfinance probe)

Exercises the multi-ticker download path the bulk population job leans on:
multi-ticker format, multi-index -> long-format conversion, date-range windows
(delta sync), and a production-size 100-ticker batch.

These talk to Yahoo for real, so they are skipped unless explicitly enabled --
a plain `pytest tests` run must not depend on the network or spend ~20s on a
single batch. Two equivalent ways to opt in:

    RUN_LIVE_MARKET_DATA_TESTS=1 pytest tests/test_yfinance_batch.py -s
    python tests/test_yfinance_batch.py          # same, with output shown

(The second form is how this file has always been used as a manual
compatibility check; it still works, it just runs through pytest now.)
"""

import os
import sys
import time
from datetime import datetime, timedelta

import pandas as pd
import pytest
import yfinance as yf
from curl_cffi import requests

LIVE_ENV_VAR = "RUN_LIVE_MARKET_DATA_TESTS"

pytestmark = pytest.mark.skipif(
    os.getenv(LIVE_ENV_VAR) != "1",
    reason=f"hits the live Yahoo API; set {LIVE_ENV_VAR}=1 to run",
)

SMALL_BATCH = ["AAPL", "MSFT", "GOOGL"]
DATE_RANGE_BATCH = ["TSLA", "NVDA", "AMD"]

LONG_FORMAT_COLUMNS = [
    "date", "ticker", "Open", "High", "Low", "Close",
    "Volume", "Dividends", "Stock Splits",
]

# Fraction of a batch we expect to come back with data. Yahoo drops the odd
# symbol under load; below this the batch path is genuinely broken.
COVERAGE_THRESHOLD = 0.9

# S&P 500 subset, sized to match what the population job actually sends.
PRODUCTION_BATCH = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'UNH', 'JNJ',
    'V', 'WMT', 'XOM', 'LLY', 'JPM', 'PG', 'MA', 'AVGO', 'HD', 'CVX',
    'MRK', 'ABBV', 'COST', 'PEP', 'ADBE', 'KO', 'TMO', 'MCD', 'CSCO', 'ACN',
    'CRM', 'ABT', 'NFLX', 'LIN', 'NKE', 'DHR', 'DIS', 'AMD', 'VZ', 'TXN',
    'CMCSA', 'PM', 'ORCL', 'NEE', 'INTC', 'WFC', 'COP', 'UPS', 'RTX', 'BMY',
    'IBM', 'HON', 'UNP', 'QCOM', 'BA', 'ELV', 'AMGN', 'LOW', 'SPGI', 'GE',
    'INTU', 'SBUX', 'CAT', 'DE', 'GS', 'MS', 'AXP', 'BLK', 'MDT', 'SCHW',
    'ADI', 'GILD', 'CVS', 'AMT', 'TJX', 'BKNG', 'LRCX', 'ADP', 'PLD', 'MMC',
    'C', 'SYK', 'REGN', 'VRTX', 'NOW', 'ISRG', 'MO', 'CB', 'ZTS', 'MDLZ',
    'CI', 'DUK', 'SO', 'PGR', 'BDX', 'EQIX', 'EOG', 'APH', 'ITW', 'CL',
]


@pytest.fixture(scope="module")
def session():
    """Stealth session. Browser impersonation is what keeps Yahoo from 429ing."""
    return requests.Session(impersonate="chrome110")


def _download(tickers, session, **kwargs):
    """yf.download with the settings the production code always passes.

    threads=False is not optional: concurrent requests are what gets the
    scraper blocked.
    """
    return yf.download(
        tickers=tickers,
        session=session,
        threads=False,
        auto_adjust=True,
        actions=True,
        progress=False,
        **kwargs,
    )


def _to_long_format(data):
    """Flatten yfinance's multi-index columns into the row-per-(date, ticker)
    shape the database insert expects."""
    assert isinstance(data.columns, pd.MultiIndex), (
        f"expected multi-index columns for a multi-ticker download, got {data.columns}"
    )

    df = data.stack(level=1, future_stack=True).reset_index()
    assert len(df.columns) == len(LONG_FORMAT_COLUMNS), (
        f"expected {len(LONG_FORMAT_COLUMNS)} columns after stacking, "
        f"got {len(df.columns)}: {list(df.columns)}"
    )
    df.columns = LONG_FORMAT_COLUMNS
    return df


@pytest.fixture(scope="module")
def small_batch_data(session):
    """One 3-ticker download, shared by the tests below."""
    data = _download(SMALL_BATCH, session, period="5d")
    assert not data.empty, "yfinance returned an empty frame for a 3-ticker batch"
    return data


def test_small_batch_download(small_batch_data):
    """2.1 A small multi-ticker batch comes back with data."""
    print(f"\n   Shape: {small_batch_data.shape}")
    print(f"   Index type: {type(small_batch_data.index)}")
    print(f"   Columns: {small_batch_data.columns}")
    print(small_batch_data.head(3))

    assert not small_batch_data.empty
    assert len(small_batch_data) > 0


def test_multiindex_to_long_format(small_batch_data):
    """2.2 Multi-index -> long format, the conversion database inserts rely on."""
    df = _to_long_format(small_batch_data)

    print(f"\n   Shape: {df.shape}")
    print(df.head(5))

    unique_tickers = set(df["ticker"].unique())
    print(f"   Unique tickers: {sorted(unique_tickers)}")
    assert unique_tickers == set(SMALL_BATCH), (
        f"expected {sorted(SMALL_BATCH)}, got {sorted(unique_tickers)}"
    )

    nan_count = df[["Open", "High", "Low", "Close"]].isna().sum().sum()
    print(f"   NaN values in OHLC: {nan_count}")


def test_batch_with_date_range(session):
    """2.3 Explicit start/end window -- the delta sync scenario."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    data = _download(
        DATE_RANGE_BATCH,
        session,
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
    )

    print(f"\n   Shape: {data.shape}")
    assert not data.empty, "date-range batch returned no data"


def test_production_size_batch(session):
    """2.4 100 tickers at once, the size the population job actually uses."""
    start_time = time.time()
    data = _download(PRODUCTION_BATCH, session, period="5d")
    elapsed = time.time() - start_time

    print(f"\n   Time: {elapsed:.1f}s")
    print(f"   Shape: {data.shape}")
    assert not data.empty, "production-size batch returned no data"

    df = _to_long_format(data)
    covered = df["ticker"].nunique()
    print(f"   Got data for {covered}/{len(PRODUCTION_BATCH)} tickers")

    assert covered >= len(PRODUCTION_BATCH) * COVERAGE_THRESHOLD, (
        f"only {covered}/{len(PRODUCTION_BATCH)} tickers returned data "
        f"(threshold {COVERAGE_THRESHOLD:.0%})"
    )


if __name__ == "__main__":
    # Manual usage: `python tests/test_yfinance_batch.py` runs the live checks
    # with output shown, the way this file was originally used as a script.
    os.environ[LIVE_ENV_VAR] = "1"
    sys.exit(pytest.main([__file__, "-v", "-s"]))
