"""Offline check of YFinanceProvider's batch reshaping against the frame shape
yfinance (1.x) returns from yf.download: MultiIndex columns (Price, Ticker),
index named "Date". No network -- yf.download is stubbed.
"""

import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://u:p@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

from datetime import date  # noqa: E402

import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from app.config import settings  # noqa: E402
from app.providers import yfinance_provider  # noqa: E402


def _download_frame(tickers):
    idx = pd.DatetimeIndex(["2025-01-02", "2025-01-03"], name="Date")
    fields = ["Close", "Dividends", "High", "Low", "Open", "Stock Splits", "Volume"]
    cols = pd.MultiIndex.from_product([fields, tickers], names=["Price", "Ticker"])
    df = pd.DataFrame(1.0, index=idx, columns=cols)
    df[("Volume", tickers[0])] = [100.0, float("nan")]
    df[("Close", tickers[-1])] = [2.0, float("nan")]  # dropped: no close
    return df


def test_batch_download_reshapes_to_long_format(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    seen = {}

    def fake_download(**kwargs):
        seen.update(kwargs)
        return _download_frame(kwargs["tickers"])

    monkeypatch.setattr(yfinance_provider.yf, "download", fake_download)
    provider = yfinance_provider.YFinanceProvider()
    out = provider.get_batch_historical_prices(["AAPL", "MSFT"], date(2025, 1, 1), date(2025, 1, 4))

    assert seen["session"] is not None and seen["auto_adjust"] is True
    assert list(out.columns) == ["date", "ticker", "Open", "High", "Low", "Close", "Volume"]
    assert len(out) == 3
    assert out["Volume"].dtype == "int64"
    assert set(out["ticker"]) == {"AAPL", "MSFT"}


@pytest.mark.parametrize("flat", [False, True])
def test_single_ticker_download(monkeypatch, flat):
    # yfinance keeps MultiIndex columns for a single ticker by default; this used
    # to return None. flat=True covers multi_level_index=False.
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)

    def fake_download(**kw):
        df = _download_frame(kw["tickers"])
        return df.droplevel("Ticker", axis=1) if flat else df

    monkeypatch.setattr(yfinance_provider.yf, "download", fake_download)
    out = yfinance_provider.YFinanceProvider().get_batch_historical_prices(
        ["AAPL"], date(2025, 1, 1), date(2025, 1, 4)
    )
    assert out is not None and len(out) == 1  # second row has NaN close
    assert list(out.columns) == ["date", "ticker", "Open", "High", "Low", "Close", "Volume"]
    assert out.iloc[0]["ticker"] == "AAPL"
