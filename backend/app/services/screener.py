from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, asc
from app.database.models import Stock
from app.models.stock import StockFilter
from typing import List, Tuple

def screen_stocks(db: Session, filters: StockFilter) -> Tuple[List[Stock], int]:
    """
    Screen stocks based on filters (pure SQL - FAST).
    
    Returns:
        Tuple of (matching stocks, total count)
    """
    query = db.query(Stock)
    
    # Build filter conditions
    conditions = []
    
    if filters.min_pe is not None:
        conditions.append(Stock.pe_ratio >= filters.min_pe)
    if filters.max_pe is not None:
        conditions.append(Stock.pe_ratio <= filters.max_pe)
        conditions.append(Stock.pe_ratio != None)  # Exclude null PE
    
    if filters.min_market_cap is not None:
        conditions.append(Stock.market_cap >= filters.min_market_cap)
    if filters.max_market_cap is not None:
        conditions.append(Stock.market_cap <= filters.max_market_cap)
    
    if filters.sectors:
        conditions.append(Stock.sector.in_(filters.sectors))
    if filters.industries:
        conditions.append(Stock.industry.in_(filters.industries))
    
    if filters.min_dividend_yield is not None:
        conditions.append(Stock.dividend_yield >= filters.min_dividend_yield)
        conditions.append(Stock.dividend_yield != None)
    
    if filters.max_debt_to_equity is not None:
        conditions.append(Stock.debt_to_equity <= filters.max_debt_to_equity)
        conditions.append(Stock.debt_to_equity != None)
    
    if filters.min_price is not None:
        conditions.append(Stock.current_price >= filters.min_price)
    if filters.max_price is not None:
        conditions.append(Stock.current_price <= filters.max_price)
    
    # Apply all conditions
    if conditions:
        query = query.filter(and_(*conditions))
    
    # Get total count
    total = query.count()
    
    # Sorting
    if hasattr(Stock, filters.sort_by):
        sort_column = getattr(Stock, filters.sort_by)
        if filters.sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
    
    # Pagination
    stocks = query.offset(filters.skip).limit(filters.limit).all()
    
    return stocks, total
