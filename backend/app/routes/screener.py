from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.screener import screen_stocks
from app.services.cache import cache_service
from app.models.stock import StockFilter, StockDetail
from typing import List, Optional

router = APIRouter(prefix="/screener", tags=["screener"])


@router.get("/screen")
def screen_stocks_endpoint(
    # Valuation filters
    min_pe: Optional[float] = Query(None, description="Minimum P/E ratio"),
    max_pe: Optional[float] = Query(None, description="Maximum P/E ratio"),
    min_market_cap: Optional[int] = Query(None, description="Minimum market cap ($)"),
    max_market_cap: Optional[int] = Query(None, description="Maximum market cap ($)"),
    
    # Sector/Industry filters
    sectors: Optional[List[str]] = Query(None, description="Filter by sectors"),
    industries: Optional[List[str]] = Query(None, description="Filter by industries"),
    
    # Financial health
    min_dividend_yield: Optional[float] = Query(None, description="Minimum dividend yield (%)"),
    max_debt_to_equity: Optional[float] = Query(None, description="Maximum debt-to-equity ratio"),
    
    # Price filters
    min_price: Optional[float] = Query(None, description="Minimum stock price ($)"),
    max_price: Optional[float] = Query(None, description="Maximum stock price ($)"),
    
    # Pagination
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    limit: int = Query(50, ge=1, le=500, description="Number of results to return"),
    
    # Sorting
    sort_by: str = Query("market_cap", description="Field to sort by"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    
    db: Session = Depends(get_db)
):
    cache_key = f"screener:{min_pe}:{max_pe}:{min_market_cap}:{max_market_cap}:{sectors}:{industries}:{min_dividend_yield}:{max_debt_to_equity}:{min_price}:{max_price}:{skip}:{limit}:{sort_by}:{sort_order}"

    # tyr the redis first 

    cached = cache_service.get(cache_key)

    if cached:
        return {
            "cached": True,
            **cached
        }
    
    filters = StockFilter(
        min_pe=min_pe,
        max_pe=max_pe,
        min_market_cap=min_market_cap,
        max_market_cap=max_market_cap,
        sectors=sectors,
        industries=industries,
        min_dividend_yield=min_dividend_yield,
        max_debt_to_equity=max_debt_to_equity,
        min_price=min_price,
        max_price=max_price,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order
    )

    stocks, total = screen_stocks(db, filters)

    # Format response (stocks are already dicts from the service)

    result = {
        "results": stocks,
        "total": total,
        "page": skip // limit + 1,
        "per_page": limit,
        "total_pages": (total + limit - 1) // limit,
        "cached": False
    }

    #cache for 1 hour 
    cache_service.set(cache_key, result, ttl=3600)
    
    return result

@router.get("/sectors")
def get_available_sectors(db: Session = Depends(get_db)):
    """
    Get list of all available sectors in the database.
    
    Useful for populating sector filter dropdowns.
    """
    cache_key = "screener:sectors"
    
    cached = cache_service.get(cache_key)
    if cached:
        return cached
    
    # Query distinct sectors
    from sqlalchemy import func
    from app.database.models import StockFundamental

    sectors = db.query(StockFundamental.sector).filter(StockFundamental.sector != None).distinct().all()
    sector_list = sorted([s[0] for s in sectors if s[0]])
    
    result = {
        "sectors": sector_list,
        "count": len(sector_list)
    }
    
    # Cache for 24 hours 
    cache_service.set(cache_key, result, ttl=86400)
    
    return result

@router.get("/industries")
def get_available_industries(db: Session = Depends(get_db)):
    """
    Get list of all available industries in the database.
    
    Useful for populating industry filter dropdowns.
    """
    cache_key = "screener:industries"
    
    cached = cache_service.get(cache_key)
    if cached:
        return cached
    
    from sqlalchemy import func
    from app.database.models import StockFundamental

    industries = db.query(StockFundamental.industry).filter(StockFundamental.industry != None).distinct().all()
    industry_list = sorted([i[0] for i in industries if i[0]])
    
    result = {
        "industries": industry_list,
        "count": len(industry_list)
    }
    
    # Cache for 24 hours
    cache_service.set(cache_key, result, ttl=86400)
    
    return result
