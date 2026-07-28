"""
Market scanners: gainers/losers, 52-week highs/lows, unusual volume, gap up/down,
and a per-sector performance heatmap.

Everything here is computed from data that is already in Postgres (daily_ohlcv +
stock_fundamentals) -- no external API calls, near-zero marginal cost. The heavy
lifting (ranking thousands of tickers over up to 252 trading days) is done with a
handful of set-based SQL queries using window functions, not a per-ticker Python
loop, so this stays fast even against a multi-million-row daily_ohlcv table.

IMPORTANT (per the data model): stock_fundamentals.day_change_percent /
current_price can lag behind the market close. Day-change and price levels here
are always derived from the last two available daily_ohlcv closes -- fundamentals
are only used for sector / market_cap / avg_volume / name.
"""
from __future__ import annotations

from datetime import date as date_type, datetime as datetime_type
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.utils.market_calendar import get_previous_trading_day

# The nightly warm job (22:30 ET, right after the 21:00 ET sync) and the route
# (which may be hit at any time, from any server timezone) share ONE stable cache
# key. Freshness is decided by the as_of_date embedded in the payload, compared
# against the US-Eastern trading calendar -- never by the key itself. A key that
# encodes "today" is a guaranteed miss for every reader on the other side of ET
# midnight from the writer.
_EASTERN = ZoneInfo("America/New_York")

# ============================================
# TUNABLE THRESHOLDS
# ============================================

MIN_CLOSE_PRICE = 2.0                  # Skip sub-$2 junk
MIN_AVG_VOLUME = 200_000                # Skip illiquid names
UNUSUAL_VOLUME_RATIO = 2.5              # last_volume / 20d avg volume
NEAR_52W_PCT_THRESHOLD = 1.0            # percent -- "within 1% of the 252d high/low"
GAP_PCT_THRESHOLD = 2.0                 # percent -- open vs prior close
TOP_N = 25
LOOKBACK_TRADING_DAYS = 252             # ~52 trading weeks
VOLUME_BASELINE_DAYS = 20               # bars in the avg-volume baseline (EXCLUDING the current bar)
MIN_VOLUME_BASELINE_BARS = 5            # fewer prior bars than this -> no baseline, no volume ratio

# ============================================
# CACHE
# ============================================

# One stable key -- the payload's own as_of_date is what tells a reader whether
# the cached scan is current (see `is_cached_payload_fresh`).
MARKET_SCANS_CACHE_KEY = "market:scans:latest"
MARKET_SCANS_CACHE_TTL = 172_800        # 2 days -- outlives a long weekend / a skipped warm job


# ============================================
# PURE HELPERS (unit-testable without a DB)
# ============================================

def _pct_change(new_value: Optional[float], base_value: Optional[float]) -> Optional[float]:
    """Percent change of new_value relative to base_value.

    Returns None if either value is missing or base_value is zero (can't divide).
    """
    if new_value is None or base_value is None or base_value == 0:
        return None
    return ((new_value - base_value) / base_value) * 100.0


def effective_avg_volume(
    fundamentals_avg_volume: Optional[float],
    computed_avg_volume_20d: Optional[float],
) -> Optional[float]:
    """Prefer the fundamentals avg_volume; fall back to the computed OHLCV baseline
    (the 20 bars *before* the current one -- see VOLUME_BASELINE_DAYS)."""
    if fundamentals_avg_volume:
        return fundamentals_avg_volume
    return computed_avg_volume_20d


def passes_junk_filter(last_close: Optional[float], avg_volume: Optional[float]) -> bool:
    """Skip sub-$2 stocks and illiquid names (<200k avg daily volume)."""
    if last_close is None or last_close < MIN_CLOSE_PRICE:
        return False
    if not avg_volume or avg_volume < MIN_AVG_VOLUME:
        return False
    return True


def is_near_52w_high(last_close: Optional[float], high_252: Optional[float]) -> bool:
    pct = _pct_change(last_close, high_252)
    return pct is not None and pct >= -NEAR_52W_PCT_THRESHOLD


def is_near_52w_low(last_close: Optional[float], low_252: Optional[float]) -> bool:
    pct = _pct_change(last_close, low_252)
    return pct is not None and pct <= NEAR_52W_PCT_THRESHOLD


def volume_ratio(last_volume: Optional[float], avg_volume_20d: Optional[float]) -> Optional[float]:
    """Today's volume over the prior-20-bar baseline.

    `avg_volume_20d` must EXCLUDE the current bar (the SQL does this), otherwise
    the spike dilutes its own baseline and the ratio understates the move.
    """
    if last_volume is None or not avg_volume_20d or avg_volume_20d <= 0:
        return None
    return last_volume / avg_volume_20d


def is_unusual_volume(last_volume: Optional[float], avg_volume_20d: Optional[float]) -> bool:
    ratio = volume_ratio(last_volume, avg_volume_20d)
    return ratio is not None and ratio >= UNUSUAL_VOLUME_RATIO


def is_gap_up(gap_pct: Optional[float]) -> bool:
    return gap_pct is not None and gap_pct >= GAP_PCT_THRESHOLD


def is_gap_down(gap_pct: Optional[float]) -> bool:
    return gap_pct is not None and gap_pct <= -GAP_PCT_THRESHOLD


def _round(value: Optional[float], ndigits: int = 2) -> Optional[float]:
    if value is None:
        return None
    try:
        return round(float(value), ndigits)
    except (TypeError, ValueError):
        return None


# ============================================
# SQL: A SINGLE ROUND TRIP PER SCAN
# ============================================
#
# One statement, four CTEs:
#   1. `ref_dates` -- the most recent `lookback_days` DISTINCT trading dates on or
#      before the requested date. This is a cheap index-only scan of the `date`
#      column (idx_ohlcv_date) and is what bounds everything below, so we never
#      scan the full 5-year daily_ohlcv history.
#   2. `bounds` -- collapses that into as_of_date (most recent), prior_date (the
#      one before it -- used for change%/gap math), and window_start (oldest date
#      in the lookback window -- used for the 252-day high/low).
#   3. `ranked` -- per-ticker row number ordered by date DESC, restricted to
#      [window_start, as_of_date].
#   4. `agg` -- collapses that into one row per ticker: last bar DATE + close/
#      open/volume (rn=1), prior close (rn=2), a 20-day avg volume, and the
#      252-day high/low.
# This turns "thousands of tickers x up to 252 days" into a single grouped scan
# instead of N per-ticker round trips, and resolves the reference dates in the
# same trip as the metrics instead of separate round trips.
#
# Two things the window functions do NOT give you for free, both handled below:
#
#   * STALENESS. `ranked` windows each ticker over ITS OWN bars, so rn=1 is
#     "that ticker's last bar", not "the market's last bar". A delisted/halted
#     name -- or one whose sync batch quietly failed -- keeps reporting a months-
#     old move as if it were today's, and since every tab ranks by extreme
#     change_pct those float straight to the top. The outer WHERE therefore
#     requires agg.last_date = bounds.as_of_date, which gates ALL scan types
#     (incl. 52w high/low) *and* the sector aggregation, since compute_scans
#     builds the sector accumulator from these same rows.
#
#   * VOLUME BASELINE. The average must EXCLUDE the current bar, otherwise the
#     spike is in its own baseline: a true k-times day computes as 20k/(19+k),
#     so a real 2.5x prints 2.33x (below the threshold -- silently dropped) and
#     a 10x day prints 6.90x. Baseline is rn 2..21 = the 20 bars *before* today.

_SCAN_SQL = text(
    """
    WITH ref_dates AS (
        SELECT DISTINCT date
        FROM daily_ohlcv
        WHERE date <= :cap_date
        ORDER BY date DESC
        LIMIT :lookback_days
    ),
    bounds AS (
        SELECT
            MAX(date) AS as_of_date,
            MIN(date) AS window_start,
            (SELECT date FROM ref_dates ORDER BY date DESC OFFSET 1 LIMIT 1) AS prior_date
        FROM ref_dates
    ),
    ranked AS (
        SELECT
            o.ticker_id, o.date, o.open, o.high, o.low, o.close, o.volume,
            ROW_NUMBER() OVER (PARTITION BY o.ticker_id ORDER BY o.date DESC) AS rn
        FROM daily_ohlcv o
        CROSS JOIN bounds b
        WHERE o.date <= b.as_of_date AND o.date >= b.window_start
    ),
    agg AS (
        SELECT
            ticker_id,
            MAX(CASE WHEN rn = 1 THEN ranked.date END) AS last_date,
            MAX(CASE WHEN rn = 1 THEN close END) AS last_close,
            MAX(CASE WHEN rn = 1 THEN open END) AS last_open,
            MAX(CASE WHEN rn = 1 THEN volume END) AS last_volume,
            MAX(CASE WHEN rn = 2 THEN close END) AS prior_close,
            CASE
                WHEN COUNT(
                    CASE WHEN rn BETWEEN 2 AND :volume_baseline_last_rn THEN volume END
                ) >= :min_baseline_bars
                THEN AVG(
                    CASE WHEN rn BETWEEN 2 AND :volume_baseline_last_rn THEN volume END
                )
            END AS avg_volume_20d,
            MAX(high) AS high_252,
            MIN(low) AS low_252
        FROM ranked
        GROUP BY ticker_id
    )
    SELECT
        t.symbol AS symbol,
        t.name AS name,
        f.sector AS sector,
        f.market_cap AS market_cap,
        f.avg_volume AS fundamentals_avg_volume,
        agg.last_close AS last_close,
        agg.last_open AS last_open,
        agg.last_volume AS last_volume,
        agg.prior_close AS prior_close,
        agg.avg_volume_20d AS avg_volume_20d,
        agg.high_252 AS high_252,
        agg.low_252 AS low_252,
        (SELECT as_of_date FROM bounds) AS as_of_date,
        (SELECT prior_date FROM bounds) AS prior_date
    FROM agg
    JOIN tickers t ON t.id = agg.ticker_id
    LEFT JOIN stock_fundamentals f ON f.ticker_id = agg.ticker_id
    WHERE agg.last_close IS NOT NULL
      AND agg.last_date = (SELECT as_of_date FROM bounds)
    """
)

# Sentinel used when no scan_date filter is requested -- keeps the SQL's date
# comparison simple (always `<= :cap_date`) instead of branching the query text.
_FAR_FUTURE_DATE = date_type(9999, 12, 31)


def _fetch_scan_data(
    db: Session, scan_date: Optional[date_type], lookback_days: int = LOOKBACK_TRADING_DAYS
) -> Tuple[Optional[date_type], Optional[date_type], List[Dict[str, Any]]]:
    """Single round-trip fetch of reference dates + per-ticker metrics.

    Returns (as_of_date, prior_date, metric_rows). If daily_ohlcv has no data at
    all (or none on/before scan_date), as_of_date is None.

    Only tickers whose own last bar lands on as_of_date come back -- see the
    staleness note above _SCAN_SQL.
    """
    cap_date = scan_date or _FAR_FUTURE_DATE
    result = db.execute(
        _SCAN_SQL,
        {
            "cap_date": cap_date,
            "lookback_days": lookback_days,
            # rn=1 is the current bar, so the 20-bar baseline is rn 2..21.
            "volume_baseline_last_rn": VOLUME_BASELINE_DAYS + 1,
            "min_baseline_bars": MIN_VOLUME_BASELINE_BARS,
        },
    )
    rows = [dict(row) for row in result.mappings().all()]

    if not rows:
        # Either there's no data at all, or every ticker failed the
        # `last_close IS NOT NULL` / freshness filter -- fall back to a cheap
        # direct lookup so the payload can still report an accurate as_of_date.
        as_of_date = db.execute(
            text("SELECT MAX(date) FROM daily_ohlcv WHERE date <= :cap_date"),
            {"cap_date": cap_date},
        ).scalar()
        return as_of_date, None, []

    return rows[0]["as_of_date"], rows[0]["prior_date"], rows


# ============================================
# ROW / SECTOR BUILDERS
# ============================================

def _make_row(m: Dict[str, Any], change_pct: Optional[float], metric: Optional[float]) -> Dict[str, Any]:
    return {
        "symbol": m["symbol"],
        "name": m["name"] or m["symbol"],
        "sector": m["sector"],
        "close": _round(m["last_close"]),
        "change_pct": _round(change_pct),
        "metric": _round(metric),
        "volume": int(m["last_volume"]) if m["last_volume"] is not None else None,
        "market_cap": int(m["market_cap"]) if m["market_cap"] is not None else None,
    }


def _top_n(rows: List[Tuple[float, Dict[str, Any]]], reverse: bool, n: int = TOP_N) -> List[Dict[str, Any]]:
    rows.sort(key=lambda pair: pair[0], reverse=reverse)
    return [row for _, row in rows[:n]]


def _new_sector_acc(sector: str) -> Dict[str, Any]:
    return {
        "sector": sector,
        "change_sum": 0.0,
        "stock_count": 0,
        "advancers": 0,
        "decliners": 0,
        "total_market_cap": 0,
    }


def _finalize_sectors(sector_acc: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    sectors: List[Dict[str, Any]] = []
    for acc in sector_acc.values():
        count = acc["stock_count"]
        avg_change = acc["change_sum"] / count if count else None
        sectors.append({
            "sector": acc["sector"],
            "avg_change_percent": _round(avg_change),
            "advancers": acc["advancers"],
            "decliners": acc["decliners"],
            "stock_count": count,
            "total_market_cap": acc["total_market_cap"],
        })
    sectors.sort(key=lambda s: s["avg_change_percent"] if s["avg_change_percent"] is not None else 0, reverse=True)
    return sectors


def market_scans_cache_key() -> str:
    """Redis key for the market scans payload -- one stable key, `market:scans:latest`.

    Deliberately NOT keyed by date. The warm job runs at 22:30 ET and any reader
    after ET midnight would compute the *next* day's key and miss every time, so
    the warm job would never serve morning traffic. Freshness is a property of
    the payload (`is_cached_payload_fresh`), not of the key.
    """
    return MARKET_SCANS_CACHE_KEY


@lru_cache(maxsize=8)
def _previous_trading_day(day: date_type) -> date_type:
    """Memoized get_previous_trading_day -- the pandas holiday calendar isn't free
    and this is on the hot path of every /market/scans request."""
    return get_previous_trading_day(day)


def expected_latest_trading_day(today_et: Optional[date_type] = None) -> date_type:
    """The most recent trading day whose close we should already have on hand.

    daily_ohlcv is synced at 21:00 ET, so at any point during ET day D the newest
    close we can *guarantee* is the one from the trading day before D. Anything at
    or after that is current; anything older means the cache predates a sync.
    """
    day = today_et or datetime_type.now(_EASTERN).date()
    # Pass the ET date explicitly -- market_calendar defaults to the *server's*
    # local date, which is exactly the timezone bug this function exists to avoid.
    return _previous_trading_day(day)


def is_cached_payload_fresh(
    payload: Optional[Dict[str, Any]], today_et: Optional[date_type] = None
) -> bool:
    """True if a cached payload is current enough to serve as-is."""
    if not payload:
        return False
    raw_as_of = payload.get("as_of_date")
    if not raw_as_of:
        return False
    try:
        as_of = date_type.fromisoformat(str(raw_as_of)[:10])
    except (TypeError, ValueError):
        return False
    return as_of >= expected_latest_trading_day(today_et)


def _empty_payload() -> Dict[str, Any]:
    return {
        "as_of_date": None,
        "prior_date": None,
        "gainers": [],
        "losers": [],
        "high_52w": [],
        "low_52w": [],
        "unusual_volume": [],
        "gap_up": [],
        "gap_down": [],
        "sectors": [],
    }


# ============================================
# MAIN ENTRY POINT
# ============================================

def compute_scans(db: Session, scan_date: Optional[date_type] = None) -> Dict[str, Any]:
    """
    Compute the full market-scanners payload.

    Args:
        db: SQLAlchemy session.
        scan_date: Optional date to scan as-of (defaults to the latest date present
            in daily_ohlcv). If given, the latest available trading date on or
            before scan_date is used.

    Returns:
        dict with as_of_date, prior_date, gainers, losers, high_52w, low_52w,
        unusual_volume, gap_up, gap_down, sectors.
    """
    as_of_date, prior_date, metrics = _fetch_scan_data(db, scan_date)
    if as_of_date is None:
        return _empty_payload()

    gainers: List[Tuple[float, Dict[str, Any]]] = []
    losers: List[Tuple[float, Dict[str, Any]]] = []
    high_52w: List[Tuple[float, Dict[str, Any]]] = []
    low_52w: List[Tuple[float, Dict[str, Any]]] = []
    unusual_volume: List[Tuple[float, Dict[str, Any]]] = []
    gap_up: List[Tuple[float, Dict[str, Any]]] = []
    gap_down: List[Tuple[float, Dict[str, Any]]] = []
    sector_acc: Dict[str, Dict[str, Any]] = {}

    for m in metrics:
        last_close = m["last_close"]
        avg_volume = effective_avg_volume(m["fundamentals_avg_volume"], m["avg_volume_20d"])
        if not passes_junk_filter(last_close, avg_volume):
            continue

        prior_close = m["prior_close"]
        change_pct = _pct_change(last_close, prior_close)

        if change_pct is not None:
            row = _make_row(m, change_pct, change_pct)
            gainers.append((change_pct, row))
            losers.append((change_pct, row))

        if is_near_52w_high(last_close, m["high_252"]):
            pct_from_high = _pct_change(last_close, m["high_252"])
            high_52w.append((pct_from_high, _make_row(m, change_pct, pct_from_high)))

        if is_near_52w_low(last_close, m["low_252"]):
            pct_from_low = _pct_change(last_close, m["low_252"])
            low_52w.append((pct_from_low, _make_row(m, change_pct, pct_from_low)))

        if is_unusual_volume(m["last_volume"], m["avg_volume_20d"]):
            ratio = volume_ratio(m["last_volume"], m["avg_volume_20d"])
            unusual_volume.append((ratio, _make_row(m, change_pct, ratio)))

        # Guard against zero/missing opens (halted or no-trade days show up as
        # open=0 in the feed) -- that would otherwise register as a bogus -100% gap.
        last_open = m["last_open"]
        gap_pct = _pct_change(last_open, prior_close) if last_open else None
        if is_gap_up(gap_pct):
            gap_up.append((gap_pct, _make_row(m, change_pct, gap_pct)))
        elif is_gap_down(gap_pct):
            gap_down.append((gap_pct, _make_row(m, change_pct, gap_pct)))

        # Sector aggregation rides on the same rows as the scan tabs, so the
        # SQL-level staleness filter covers the heatmap too -- a delisted name
        # can't drag its sector's average around with a months-old move.
        sector = m["sector"]
        if sector and change_pct is not None:
            acc = sector_acc.setdefault(sector, _new_sector_acc(sector))
            acc["change_sum"] += change_pct
            acc["stock_count"] += 1
            if change_pct > 0:
                acc["advancers"] += 1
            elif change_pct < 0:
                acc["decliners"] += 1
            if m["market_cap"]:
                acc["total_market_cap"] += int(m["market_cap"])

    return {
        "as_of_date": as_of_date.isoformat(),
        "prior_date": prior_date.isoformat() if prior_date else None,
        "gainers": _top_n(gainers, reverse=True),
        "losers": _top_n(losers, reverse=False),
        "high_52w": _top_n(high_52w, reverse=True),
        "low_52w": _top_n(low_52w, reverse=False),
        "unusual_volume": _top_n(unusual_volume, reverse=True),
        "gap_up": _top_n(gap_up, reverse=True),
        "gap_down": _top_n(gap_down, reverse=False),
        "sectors": _finalize_sectors(sector_acc),
    }
