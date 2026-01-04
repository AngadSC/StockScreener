from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, asc
from app.database.models import Ticker, StockFundamental
from app.models.stock import StockFilter
from typing import List, Tuple, Dict, Any

def screen_stocks(db: Session, filters: StockFilter) -> Tuple[List[Dict[str, Any]], int]:
    """
    Screen stocks based on filters (pure SQL - FAST).

    Returns:
        Tuple of (matching stock dicts, total count)
    """
    # Join Ticker and StockFundamental
    query = db.query(Ticker, StockFundamental).join(
        StockFundamental,
        Ticker.id == StockFundamental.ticker_id
    )

    # Build filter conditions
    conditions = []

    if filters.min_pe is not None:
        conditions.append(StockFundamental.pe_ratio >= filters.min_pe)
    if filters.max_pe is not None:
        conditions.append(StockFundamental.pe_ratio <= filters.max_pe)
        conditions.append(StockFundamental.pe_ratio != None)  # Exclude null PE

    if filters.min_market_cap is not None:
        conditions.append(StockFundamental.market_cap >= filters.min_market_cap)
    if filters.max_market_cap is not None:
        conditions.append(StockFundamental.market_cap <= filters.max_market_cap)

    if filters.sectors:
        conditions.append(StockFundamental.sector.in_(filters.sectors))
    if filters.industries:
        conditions.append(StockFundamental.industry.in_(filters.industries))

    if filters.min_dividend_yield is not None:
        conditions.append(StockFundamental.dividend_yield >= filters.min_dividend_yield)
        conditions.append(StockFundamental.dividend_yield != None)

    if filters.max_debt_to_equity is not None:
        conditions.append(StockFundamental.debt_to_equity <= filters.max_debt_to_equity)
        conditions.append(StockFundamental.debt_to_equity != None)

    if filters.min_price is not None:
        conditions.append(StockFundamental.current_price >= filters.min_price)
    if filters.max_price is not None:
        conditions.append(StockFundamental.current_price <= filters.max_price)

    # Apply all conditions
    if conditions:
        query = query.filter(and_(*conditions))

    # Get total count
    total = query.count()

    # Sorting
    if hasattr(StockFundamental, filters.sort_by):
        sort_column = getattr(StockFundamental, filters.sort_by)
        if filters.sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

    # Pagination
    results = query.offset(filters.skip).limit(filters.limit).all()

    # Convert to dicts for API response
    stocks = []
    for ticker, fundamental in results:
        stocks.append({
            'ticker': ticker.symbol,
            'name': ticker.name,
            'sector': fundamental.sector,
            'industry': fundamental.industry,
            'market_cap': fundamental.market_cap,
            'pe_ratio': fundamental.pe_ratio,
            'forward_pe': fundamental.forward_pe,
            'peg_ratio': fundamental.peg_ratio,
            'price_to_book': fundamental.price_to_book,
            'price_to_sales': fundamental.price_to_sales,
            'ev_to_ebitda': fundamental.ev_to_ebitda,
            'profit_margin': fundamental.profit_margin,
            'operating_margin': fundamental.operating_margin,
            'roe': fundamental.roe,
            'roa': fundamental.roa,
            'revenue_growth': fundamental.revenue_growth,
            'earnings_growth': fundamental.earnings_growth,
            'debt_to_equity': fundamental.debt_to_equity,
            'current_ratio': fundamental.current_ratio,
            'quick_ratio': fundamental.quick_ratio,
            'dividend_yield': fundamental.dividend_yield,
            'dividend_rate': fundamental.dividend_rate,
            'payout_ratio': fundamental.payout_ratio,
            'current_price': fundamental.current_price,
            'day_change_percent': fundamental.day_change_percent,
            'volume': fundamental.volume,
            'avg_volume': fundamental.avg_volume,
            'beta': fundamental.beta,
            'fifty_two_week_high': fundamental.fifty_two_week_high,
            'fifty_two_week_low': fundamental.fifty_two_week_low,
            'last_updated': fundamental.last_updated.isoformat() if fundamental.last_updated else None
        })

    return stocks, total
