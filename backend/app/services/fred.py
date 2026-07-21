"""
FRED (Federal Reserve Economic Data) macro service.

Pulls a small fixed set of macro series from the FRED observations API and
exposes pure, independently-testable transforms:

- parse_fred_value: handles FRED's '.' missing-value sentinel
- compute_yoy_series: turns a monthly index series (e.g. CPI) into YoY % change

Network I/O (fetch_series_observations) is isolated so tests never need it.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.config import settings

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

# (series_id, human label, whether this series needs a YoY transform)
FRED_SERIES: List[Dict[str, Any]] = [
    {"id": "DGS10", "label": "10-Year Treasury Yield", "unit": "%", "yoy": False},
    {"id": "DGS2", "label": "2-Year Treasury Yield", "unit": "%", "yoy": False},
    {"id": "T10Y2Y", "label": "10Y-2Y Treasury Spread", "unit": "pp", "yoy": False},
    {"id": "FEDFUNDS", "label": "Effective Federal Funds Rate", "unit": "%", "yoy": False},
    {"id": "UNRATE", "label": "Unemployment Rate", "unit": "%", "yoy": False},
    {"id": "CPIAUCSL", "label": "CPI (YoY)", "unit": "%", "yoy": True},
    {"id": "MORTGAGE30US", "label": "30-Year Mortgage Rate", "unit": "%", "yoy": False},
    {"id": "VIXCLS", "label": "VIX", "unit": "idx", "yoy": False},
]

# How much history to keep in the DB / return in the dashboard.
RETENTION_DAYS = 730
# Extra lookback fetched (but not stored beyond RETENTION_DAYS) so CPI YoY
# math has a same-month-last-year comparison point available.
YOY_LOOKBACK_BUFFER_DAYS = 400


def parse_fred_value(raw: Optional[str]) -> Optional[float]:
    """FRED represents missing observations as the literal string '.'."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    raw = raw.strip()
    if raw == "" or raw == ".":
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def compute_yoy_series(
    observations: List[Tuple[date, Optional[float]]]
) -> List[Tuple[date, float]]:
    """
    Convert a raw monthly index series (e.g. CPIAUCSL) into year-over-year
    percent change, matched by (year - 1, month) rather than a fixed day
    offset so it's robust to FRED's month-end/month-start date conventions.
    """
    by_month: Dict[Tuple[int, int], float] = {}
    for d, v in observations:
        if v is not None:
            by_month[(d.year, d.month)] = v

    result: List[Tuple[date, float]] = []
    for d, v in observations:
        if v is None:
            continue
        prior = by_month.get((d.year - 1, d.month))
        if prior is None or prior == 0:
            continue
        yoy = (v - prior) / prior * 100.0
        result.append((d, yoy))

    return result


def fetch_series_observations(
    series_id: str,
    start_date: date,
    end_date: date,
    api_key: Optional[str] = None,
) -> List[Tuple[date, Optional[float]]]:
    """Fetch raw (date, value) pairs for one FRED series. Network call."""
    key = api_key or settings.FRED_API_KEY
    if not key:
        return []

    params = {
        "series_id": series_id,
        "api_key": key,
        "file_type": "json",
        "observation_start": start_date.isoformat(),
        "observation_end": end_date.isoformat(),
    }

    try:
        response = httpx.get(FRED_BASE_URL, params=params, timeout=15.0)
        response.raise_for_status()
        payload = response.json()
    except Exception as e:
        print(f"[fred] error fetching {series_id}: {e}")
        return []

    observations = []
    for row in payload.get("observations", []):
        raw_date = row.get("date")
        if not raw_date:
            continue
        try:
            d = datetime.strptime(raw_date, "%Y-%m-%d").date()
        except ValueError:
            continue
        observations.append((d, parse_fred_value(row.get("value"))))

    return observations


def build_series_for_storage(
    series_def: Dict[str, Any],
    end_date: Optional[date] = None,
    api_key: Optional[str] = None,
) -> List[Tuple[date, float]]:
    """
    Fetch + (optionally) transform one series, trimmed to RETENTION_DAYS.
    Applies the CPI YoY transform when series_def['yoy'] is True.
    """
    end_date = end_date or date.today()
    fetch_start = end_date - timedelta(days=RETENTION_DAYS + YOY_LOOKBACK_BUFFER_DAYS)

    raw_obs = fetch_series_observations(series_def["id"], fetch_start, end_date, api_key=api_key)
    if not raw_obs:
        return []

    if series_def.get("yoy"):
        transformed = compute_yoy_series(raw_obs)
    else:
        transformed = [(d, v) for d, v in raw_obs if v is not None]

    cutoff = end_date - timedelta(days=RETENTION_DAYS)
    return [(d, v) for d, v in transformed if d >= cutoff]
