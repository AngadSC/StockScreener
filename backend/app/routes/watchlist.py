from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload

from app.database.connection import get_db
from app.database.models import Watchlist, Ticker, User, StockFundamental
from app.models.watchlist import WatchlistItemCreate, WatchlistItemResponse, WatchlistResponse
from app.services.auth import get_current_active_user

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


def _build_item_response(item: Watchlist) -> dict:
    """Convert a Watchlist ORM object into a WatchlistItemResponse-compatible dict."""
    ticker_obj = item.ticker
    fund = ticker_obj.fundamentals if ticker_obj else None

    stock = {
        "ticker": ticker_obj.symbol if ticker_obj else "",
        "name": ticker_obj.name if ticker_obj else None,
        "sector": fund.sector if fund else None,
        "industry": fund.industry if fund else None,
        "market_cap": fund.market_cap if fund else None,
        "current_price": fund.current_price if fund else None,
        "day_change_percent": fund.day_change_percent if fund else None,
        "pe_ratio": fund.pe_ratio if fund else None,
        "forward_pe": fund.forward_pe if fund else None,
        "peg_ratio": fund.peg_ratio if fund else None,
        "pb_ratio": fund.price_to_book if fund else None,
        "ps_ratio": fund.price_to_sales if fund else None,
        "ev_to_ebitda": fund.ev_to_ebitda if fund else None,
        "profit_margin": fund.profit_margin if fund else None,
        "operating_margin": fund.operating_margin if fund else None,
        "roe": fund.roe if fund else None,
        "roa": fund.roa if fund else None,
        "debt_to_equity": fund.debt_to_equity if fund else None,
        "current_ratio": fund.current_ratio if fund else None,
        "quick_ratio": fund.quick_ratio if fund else None,
        "revenue_growth": fund.revenue_growth if fund else None,
        "earnings_growth": fund.earnings_growth if fund else None,
        "dividend_yield": fund.dividend_yield if fund else None,
        "dividend_rate": fund.dividend_rate if fund else None,
        "payout_ratio": fund.payout_ratio if fund else None,
        "volume": fund.volume if fund else None,
        "avg_volume": fund.avg_volume if fund else None,
        "beta": fund.beta if fund else None,
        "fifty_two_week_high": fund.fifty_two_week_high if fund else None,
        "fifty_two_week_low": fund.fifty_two_week_low if fund else None,
        "last_updated": fund.last_updated if fund else None,
    }

    return {
        "id": item.id,
        "ticker": ticker_obj.symbol if ticker_obj else "",
        "added_at": item.added_at,
        "stock": stock,
    }


@router.get("", response_model=WatchlistResponse)
def get_watchlist(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's watchlist.

    Returns all stocks in the watchlist with fundamental data.
    Requires authentication.
    """
    watchlist_items = db.query(Watchlist).options(
        joinedload(Watchlist.ticker).joinedload(Ticker.fundamentals)
    ).filter(
        Watchlist.user_id == current_user.id
    ).all()

    return {
        "items": [_build_item_response(item) for item in watchlist_items],
        "total": len(watchlist_items),
    }

@router.post("", response_model=WatchlistItemResponse)
def add_to_watchlist(
    item: WatchlistItemCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Add a stock to watchlist.

    - Stock must exist in database
    - Cannot add duplicate stocks
    - Requires authentication
    """
    ticker_symbol = item.ticker.upper()

    # Check if ticker exists (eager-load fundamentals for the response)
    ticker_obj = db.query(Ticker).options(
        joinedload(Ticker.fundamentals)
    ).filter(Ticker.symbol == ticker_symbol).first()

    if not ticker_obj:
        raise HTTPException(
            status_code=404,
            detail=f"Stock {ticker_symbol} not found in database"
        )

    # Check if already in watchlist
    existing = db.query(Watchlist).filter(
        Watchlist.user_id == current_user.id,
        Watchlist.ticker_id == ticker_obj.id
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Stock {ticker_symbol} already in watchlist"
        )

    # Add to watchlist
    watchlist_item = Watchlist(
        user_id=current_user.id,
        ticker_id=ticker_obj.id
    )

    db.add(watchlist_item)
    db.commit()
    db.refresh(watchlist_item)

    # Re-load with relationships for response
    watchlist_item.ticker = ticker_obj
    return _build_item_response(watchlist_item)

@router.delete("/{ticker}")
def remove_from_watchlist(
    ticker: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Remove a stock from watchlist.

    Returns 404 if stock not in watchlist.
    Requires authentication.
    """
    ticker_symbol = ticker.upper()

    # Get the ticker ID
    ticker_obj = db.query(Ticker).filter(Ticker.symbol == ticker_symbol).first()
    if not ticker_obj:
        raise HTTPException(
            status_code=404,
            detail=f"Stock {ticker_symbol} not found"
        )

    watchlist_item = db.query(Watchlist).filter(
        Watchlist.user_id == current_user.id,
        Watchlist.ticker_id == ticker_obj.id
    ).first()

    if not watchlist_item:
        raise HTTPException(
            status_code=404,
            detail=f"Stock {ticker_symbol} not in watchlist"
        )

    db.delete(watchlist_item)
    db.commit()

    return {
        "message": f"Stock {ticker_symbol} removed from watchlist",
        "ticker": ticker_symbol
    }