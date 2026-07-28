"""
Public (free) insider-activity endpoints backed by SEC EDGAR Form 4 data.

Router prefix is ``/market`` (shared with market_scans.py, owned by another
agent -- FastAPI allows multiple routers under one prefix). Mounted under
``settings.API_V1_PREFIX`` in ``app/main.py``.
"""

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.config import settings
from app.database.connection import get_db
from app.database.models import InsiderTransaction, StockFundamental, Ticker
from app.services.cache import cache_service
from app.utils.market_calendar import today_et

router = APIRouter(prefix="/market", tags=["insiders"])

# map the public "type" filter to Form 4 transaction codes
_TYPE_CODES = {
    "buys": ("P",),
    "sells": ("S",),
    "all": ("P", "S"),
}


def _resolve_company_name(
    ticker_name: Optional[str], additional: Optional[dict]
) -> Optional[str]:
    """
    Company display name with a StockFundamental.additional_data fallback.

    ``tickers.name`` is NULL for the large majority of rows (including megacaps
    like MSFT/NVDA/TSLA), so relying on it alone rendered "N/A" for most of the
    insider feed. Mirrors services/screener.py::_resolve_company_name.
    """
    if ticker_name:
        return ticker_name

    if not isinstance(additional, dict):
        return None

    # YahooQuery structure: additional_data.price.{shortName,longName}
    for section in ("price", "summary"):
        block = additional.get(section)
        if isinstance(block, dict):
            name = block.get("shortName") or block.get("longName") or block.get("name")
            if name:
                return name

    # YFinance structure: additional_data.{shortName,longName,displayName}
    for key in ("shortName", "longName", "displayName", "name"):
        name = additional.get(key)
        if name:
            return name

    return None


def _serialize(txn: InsiderTransaction, symbol: str, company: Optional[str]) -> dict:
    return {
        "accession_no": txn.accession_no,
        "filed_date": txn.filed_date.isoformat() if txn.filed_date else None,
        "transaction_date": (
            txn.transaction_date.isoformat() if txn.transaction_date else None
        ),
        "symbol": symbol,
        "company": company,
        "owner_name": txn.owner_name,
        "owner_title": txn.owner_title,
        "is_officer": bool(txn.is_officer),
        "is_director": bool(txn.is_director),
        "transaction_code": txn.transaction_code,
        "type": "buy" if txn.transaction_code == "P" else "sell",
        "shares": txn.shares,
        "price": txn.price,
        "value": txn.value,
    }


@router.get("/insider-activity")
def get_insider_activity(
    type: str = Query("buys", description="buys | sells | all"),
    min_value: float = Query(50000, ge=0, description="Minimum transaction value ($)"),
    days: int = Query(14, ge=1, le=365, description="Look back this many days"),
    limit: int = Query(100, ge=1, le=500, description="Max rows to return"),
    db: Session = Depends(get_db),
):
    """Recent insider transactions across all tracked tickers, newest first."""
    activity_type = type.lower().strip()
    codes = _TYPE_CODES.get(activity_type, _TYPE_CODES["buys"])

    cache_key = f"insider:activity:{activity_type}:{min_value}:{days}:{limit}"
    cached = cache_service.get(cache_key)
    if cached:
        return {"cached": True, **cached}

    since = today_et() - timedelta(days=days)
    # StockFundamental is 1:1 with Ticker (ticker_id is its primary key), so the
    # outer join carries the name fallback without multiplying rows.
    query = (
        db.query(
            InsiderTransaction,
            Ticker.symbol,
            Ticker.name,
            StockFundamental.additional_data,
        )
        .join(Ticker, Ticker.id == InsiderTransaction.ticker_id)
        .outerjoin(StockFundamental, StockFundamental.ticker_id == Ticker.id)
        .filter(InsiderTransaction.transaction_code.in_(codes))
        .filter(InsiderTransaction.filed_date >= since)
        .filter(InsiderTransaction.value >= min_value)
        .order_by(desc(InsiderTransaction.filed_date), desc(InsiderTransaction.id))
        .limit(limit)
    )

    results = [
        _serialize(txn, symbol, _resolve_company_name(name, additional))
        for txn, symbol, name, additional in query.all()
    ]
    payload = {
        "results": results,
        "count": len(results),
        "filters": {
            "type": activity_type,
            "min_value": min_value,
            "days": days,
            "limit": limit,
        },
        "cached": False,
    }
    cache_service.set(cache_key, payload, ttl=settings.EDGAR_ACTIVITY_CACHE_TTL)
    return payload


@router.get("/insider-activity/{ticker}")
def get_insider_activity_for_ticker(
    ticker: str,
    type: str = Query("all", description="buys | sells | all"),
    days: int = Query(90, ge=1, le=730, description="Look back this many days"),
    limit: int = Query(200, ge=1, le=1000, description="Max rows to return"),
    db: Session = Depends(get_db),
):
    """Per-ticker insider transaction history, newest first."""
    symbol = ticker.upper().strip()
    activity_type = type.lower().strip()
    codes = _TYPE_CODES.get(activity_type, _TYPE_CODES["all"])

    row = (
        db.query(Ticker, StockFundamental.additional_data)
        .outerjoin(StockFundamental, StockFundamental.ticker_id == Ticker.id)
        .filter(Ticker.symbol == symbol)
        .first()
    )
    if row is None:
        return {"symbol": symbol, "results": [], "count": 0}

    ticker_obj, additional = row
    company = _resolve_company_name(ticker_obj.name, additional)

    since = today_et() - timedelta(days=days)
    query = (
        db.query(InsiderTransaction)
        .filter(InsiderTransaction.ticker_id == ticker_obj.id)
        .filter(InsiderTransaction.transaction_code.in_(codes))
        .filter(InsiderTransaction.filed_date >= since)
        .order_by(desc(InsiderTransaction.filed_date), desc(InsiderTransaction.id))
        .limit(limit)
    )

    results = [_serialize(txn, symbol, company) for txn in query.all()]
    return {
        "symbol": symbol,
        "company": company,
        "results": results,
        "count": len(results),
        "filters": {"type": activity_type, "days": days, "limit": limit},
    }
