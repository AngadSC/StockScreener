from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from app.database.models import Stock
from app.models.stock import StockFilter
from typing import List, Tuple

def screen_stocks(db: Session, filters: StockFilter) -> Tuple[List[Stock], int]:
    """
    Apply filters to stocks and return matching stocks + total count
    """
    query = db.query(Stock)

    conditions = []

    if filters.min_pe is not None:
        conditions.append(Stock.pe_ratio >= filters.min_pe)
    if filters.max_pe is not None:
        conditions.append(Stock.pe_ratio <= filters.max_pe)
    
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
    
    if filters.max_debt_to_equity is not None:
        conditions.append(Stock.debt_to_equity <= filters.max_debt_to_equity)
    
    if filters.min_price is not None:
        conditions.append(Stock.current_price >= filters.min_price)
    if filters.max_price is not None:
        conditions.append(Stock.current_price <= filters.max_price)

    if conditions:
        query = query.filter(and_(*conditions)) 
    
    total = query.count()

    sort_column = getattr(Stock, filters.sort_by) 
    if filters.sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))
    
    stocks = query.offset(filters.skip).limit(filters.limit).all()  

    return stocks, total