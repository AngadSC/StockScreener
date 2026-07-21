"""
Earnings calendar service.

Fetches upcoming earnings dates from yahooquery in batches (reusing the same
batching/jitter conventions as app.providers.yahooquery_provider) and exposes
small, independently-testable helper functions:

- _merge_scope_symbols: pure merge/dedupe of two symbol lists (no DB/network)
- get_earnings_scope_tickers: builds the DB-backed scope query
- parse_calendar_event: pure parser for a single yahooquery calendar_events payload
- fetch_calendar_events_batch: the network call (batched + jittered)
"""
from __future__ import annotations

import random
import time
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import StockFundamental, Ticker, Watchlist

# Cost-control: only fetch earnings for tickers that matter.
DEFAULT_TOP_MARKET_CAP_LIMIT = 500


def _merge_scope_symbols(watchlisted_symbols: List[str], top_market_cap_symbols: List[str]) -> List[str]:
    """Union + de-dupe two symbol lists into a sorted list. Pure function (no I/O)."""
    return sorted({s for s in watchlisted_symbols if s} | {s for s in top_market_cap_symbols if s})


def get_earnings_scope_tickers(db: Session, top_n: int = DEFAULT_TOP_MARKET_CAP_LIMIT) -> List[str]:
    """
    Union of (all tickers on any user watchlist) + (top `top_n` by market cap).

    This bounds the nightly yahooquery call volume instead of fetching the
    entire ticker universe every night.
    """
    watchlisted_symbols = [
        s for (s,) in db.query(Ticker.symbol)
        .join(Watchlist, Watchlist.ticker_id == Ticker.id)
        .distinct()
        .all()
    ]

    top_market_cap_symbols = [
        s for (s,) in db.query(Ticker.symbol)
        .join(StockFundamental, StockFundamental.ticker_id == Ticker.id)
        .filter(StockFundamental.market_cap.isnot(None))
        .order_by(StockFundamental.market_cap.desc())
        .limit(top_n)
        .all()
    ]

    return _merge_scope_symbols(watchlisted_symbols, top_market_cap_symbols)


def _coerce_event_date(raw: Any) -> Optional[datetime]:
    """yahooquery returns earningsDate entries as datetime, date, or ISO strings depending on version."""
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, date):
        return datetime(raw.year, raw.month, raw.day)
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _infer_time_hint(dt: datetime) -> str:
    """
    Best-effort BMO/AMC classification.

    Yahoo's calendarEvents payload usually only carries a date (midnight,
    no time-of-day), so this can only classify events that DO carry an
    hour component. Known gap: most events will resolve to 'unknown'.
    """
    if dt.hour == 0 and dt.minute == 0:
        return "unknown"
    if dt.hour < 12:
        return "bmo"
    if dt.hour >= 16:
        return "amc"
    return "unknown"


def parse_calendar_event(raw: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Parse one ticker's yahooquery `calendar_events` payload into our storage shape.

    Expected shape (yahooquery):
        {
            "earnings": {
                "earningsDate": [datetime, ...],   # sometimes a 1-2 item range
                "earningsAverage": float,
                ...
            },
            "exDividendDate": ...,
        }

    Returns None if there's no usable earnings date.
    """
    if not raw or isinstance(raw, str):
        return None

    earnings = raw.get("earnings") if isinstance(raw, dict) else None
    if not earnings or not isinstance(earnings, dict):
        return None

    raw_dates = earnings.get("earningsDate")
    if not raw_dates:
        return None
    if not isinstance(raw_dates, (list, tuple)):
        raw_dates = [raw_dates]

    parsed_dates = [d for d in (_coerce_event_date(v) for v in raw_dates) if d is not None]
    if not parsed_dates:
        return None

    # When Yahoo gives an uncertain range, use the earliest date as our estimate.
    earliest = min(parsed_dates)

    return {
        "earnings_date": earliest.date(),
        "time_hint": _infer_time_hint(earliest),
        "eps_estimate": earnings.get("earningsAverage"),
    }


def _apply_jitter() -> None:
    if not settings.RATE_LIMIT_ENABLED:
        return
    time.sleep(random.uniform(settings.YAHOOQUERY_JITTER_MIN, settings.YAHOOQUERY_JITTER_MAX))


def fetch_calendar_events_batch(symbols: List[str]) -> Dict[str, Any]:
    """
    Fetch calendar_events for a batch of symbols via yahooquery in ONE API call.
    Applies jitter after the call, matching YahooQueryProvider's batching style.
    """
    if not symbols:
        return {}

    from yahooquery import Ticker as YQTicker  # local import to keep provider dep optional at module load

    try:
        ticker_obj = YQTicker(symbols)
        events = ticker_obj.calendar_events
        if not isinstance(events, dict):
            return {}
        return events
    except Exception as e:
        print(f"[earnings] yahooquery batch error: {e}")
        return {}
    finally:
        _apply_jitter()


def chunk_symbols(symbols: List[str], batch_size: Optional[int] = None) -> List[List[str]]:
    size = batch_size or settings.YAHOOQUERY_BATCH_SIZE
    return [symbols[i:i + size] for i in range(0, len(symbols), size)]
