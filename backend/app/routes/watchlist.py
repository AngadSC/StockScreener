from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload

from app.database.connection import get_db
from app.database.models import Watchlist, Stock, User
from app.models.watchlist import WatchlistItemCreate, WatchlistItemResponse, WatchlistResponse
from app.services.auth import get_current_active_user

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("", response_model=WatchlistResponse)
def get_watchlist(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's watchlist.
    
    Returns all stocks in the watchlist with full fundamental data.
    Requires authentication.
    """
    watchlist_items = db.query(Watchlist).options(
        joinedload(Watchlist.stock)
    ).filter(
        Watchlist.user_id == current_user.id
    ).all()
    
    return {
        "items": watchlist_items,
        "total": len(watchlist_items)
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
    ticker = item.ticker.upper()
    
    # Check if stock exists
    stock = db.query(Stock).filter(Stock.ticker == ticker).first()
    if not stock:
        raise HTTPException(
            status_code=404,
            detail=f"Stock {ticker} not found in database"
        )
    
    # Check if already in watchlist
    existing = db.query(Watchlist).filter(
        Watchlist.user_id == current_user.id,
        Watchlist.ticker == ticker
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Stock {ticker} already in watchlist"
        )
    
    # Add to watchlist
    watchlist_item = Watchlist(
        user_id=current_user.id,
        ticker=ticker
    )
    
    db.add(watchlist_item)
    db.commit()
    db.refresh(watchlist_item)
    
    return watchlist_item

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
    ticker = ticker.upper()
    
    watchlist_item = db.query(Watchlist).filter(
        Watchlist.user_id == current_user.id,
        Watchlist.ticker == ticker
    ).first()
    
    if not watchlist_item:
        raise HTTPException(
            status_code=404,
            detail=f"Stock {ticker} not in watchlist"
        )
    
    db.delete(watchlist_item)
    db.commit()
    
    return {
        "message": f"Stock {ticker} removed from watchlist",
        "ticker": ticker
    }