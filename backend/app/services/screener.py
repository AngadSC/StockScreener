from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, asc, or_, nulls_last
from app.database.models import Ticker, StockFundamental
from app.models.stock import StockFilter
from typing import List, Tuple, Dict, Any, Optional
import math


# Real, sortable columns on StockFundamental. Any sort_by outside this set
# falls back to a sensible default rather than raising on order_by(...).
SORTABLE_FIELDS = {
    "pe_ratio",
    "forward_pe",
    "peg_ratio",
    "price_to_book",
    "price_to_sales",
    "ev_to_ebitda",
    "profit_margin",
    "operating_margin",
    "roe",
    "roa",
    "debt_to_equity",
    "current_ratio",
    "quick_ratio",
    "revenue_growth",
    "earnings_growth",
    "dividend_yield",
    "dividend_rate",
    "payout_ratio",
    "market_cap",
    "volume",
    "avg_volume",
    "beta",
    "current_price",
    "day_change_percent",
    "fifty_two_week_high",
    "fifty_two_week_low",
}


def _resolve_company_name(ticker: Ticker, fundamental: Optional[StockFundamental]) -> Optional[str]:
    if ticker.name:
        return ticker.name

    if not fundamental:
        return None

    additional = fundamental.additional_data if isinstance(fundamental.additional_data, dict) else {}
    if not isinstance(additional, dict):
        return None

    # YahooQuery structure: additional_data.price.{shortName,longName}
    price = additional.get('price')
    if isinstance(price, dict):
        name = price.get('shortName') or price.get('longName') or price.get('name')
        if name:
            return name

    # YahooQuery summary module sometimes contains names
    summary = additional.get('summary')
    if isinstance(summary, dict):
        name = summary.get('shortName') or summary.get('longName') or summary.get('name')
        if name:
            return name

    # YFinance structure: additional_data.{shortName,longName,displayName}
    for key in ('shortName', 'longName', 'displayName', 'name'):
        name = additional.get(key)
        if name:
            return name

    return None

def _build_search_filter(term: str):
    like_term = f"%{term}%"
    return or_(
        Ticker.symbol.ilike(like_term),
        Ticker.name.ilike(like_term),
        StockFundamental.additional_data['price']['shortName'].astext.ilike(like_term),
        StockFundamental.additional_data['price']['longName'].astext.ilike(like_term),
        StockFundamental.additional_data['summary']['shortName'].astext.ilike(like_term),
        StockFundamental.additional_data['summary']['longName'].astext.ilike(like_term),
        StockFundamental.additional_data['shortName'].astext.ilike(like_term),
        StockFundamental.additional_data['longName'].astext.ilike(like_term),
        StockFundamental.additional_data['displayName'].astext.ilike(like_term),
    )

def get_search_suggestions(
    db: Session,
    term: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    query = db.query(Ticker, StockFundamental).outerjoin(
        StockFundamental,
        Ticker.id == StockFundamental.ticker_id
    )

    query = query.filter(_build_search_filter(term))
    results = query.order_by(Ticker.symbol.asc()).limit(limit).all()

    suggestions = []
    for ticker, fundamental in results:
        suggestions.append({
            'ticker': ticker.symbol,
            'name': _resolve_company_name(ticker, fundamental)
        })

    return suggestions

def _get_field(obj: Optional[StockFundamental], field: str):
    if not obj:
        return None
    return getattr(obj, field)


def _json_safe_value(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _json_safe_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {key: _json_safe_value(value) for key, value in row.items()}

def screen_stocks(db: Session, filters: StockFilter) -> Tuple[List[Dict[str, Any]], int]:
    """
    Screen stocks based on filters (pure SQL - FAST).

    Returns:
        Tuple of (matching stock dicts, total count)
    """
    # Join Ticker and StockFundamental (outer join to allow search by name even if fundamentals missing)
    query = db.query(Ticker, StockFundamental).outerjoin(
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

    if filters.max_beta is not None:
        conditions.append(StockFundamental.beta <= filters.max_beta)
        conditions.append(StockFundamental.beta != None)

    if filters.min_roe is not None:
        conditions.append(StockFundamental.roe >= filters.min_roe)
        conditions.append(StockFundamental.roe != None)

    if filters.min_revenue_growth is not None:
        conditions.append(StockFundamental.revenue_growth >= filters.min_revenue_growth)
        conditions.append(StockFundamental.revenue_growth != None)

    if filters.min_price is not None:
        conditions.append(StockFundamental.current_price >= filters.min_price)
    if filters.max_price is not None:
        conditions.append(StockFundamental.current_price <= filters.max_price)
    if filters.min_volume is not None:
        conditions.append(StockFundamental.volume >= filters.min_volume)
        conditions.append(StockFundamental.volume != None)
    if filters.min_avg_volume is not None:
        conditions.append(StockFundamental.avg_volume >= filters.min_avg_volume)
        conditions.append(StockFundamental.avg_volume != None)

    # Search by ticker symbol or company name (case-insensitive)
    if filters.search:
        term = filters.search.strip()
        if term:
            conditions.append(_build_search_filter(term))

    # Apply all conditions
    if conditions:
        query = query.filter(and_(*conditions))

    # Market movers should not be dominated by NULL rows.
    if filters.sort_by == "day_change_percent":
        query = query.filter(
            StockFundamental.day_change_percent != None,
            StockFundamental.day_change_percent < 1000,
            StockFundamental.day_change_percent > -1000,
        )

    # Get total count
    total = query.count()

    # Sorting
    sort_by = filters.sort_by if filters.sort_by in SORTABLE_FIELDS else "market_cap"
    sort_column = getattr(StockFundamental, sort_by)
    if filters.sort_order == "desc":
        query = query.order_by(nulls_last(desc(sort_column)), Ticker.symbol.asc())
    else:
        query = query.order_by(nulls_last(asc(sort_column)), Ticker.symbol.asc())

    # Pagination
    results = query.offset(filters.skip).limit(filters.limit).all()

    # Convert to dicts for API response
    stocks = []
    for ticker, fundamental in results:
        stock_row = {
            'ticker': ticker.symbol,
            'name': _resolve_company_name(ticker, fundamental),
            'sector': _get_field(fundamental, 'sector'),
            'industry': _get_field(fundamental, 'industry'),
            'market_cap': _get_field(fundamental, 'market_cap'),
            'pe_ratio': _get_field(fundamental, 'pe_ratio'),
            'forward_pe': _get_field(fundamental, 'forward_pe'),
            'peg_ratio': _get_field(fundamental, 'peg_ratio'),
            'pb_ratio': _get_field(fundamental, 'price_to_book'),
            'ps_ratio': _get_field(fundamental, 'price_to_sales'),
            'ev_to_ebitda': _get_field(fundamental, 'ev_to_ebitda'),
            'profit_margin': _get_field(fundamental, 'profit_margin'),
            'operating_margin': _get_field(fundamental, 'operating_margin'),
            'roe': _get_field(fundamental, 'roe'),
            'roa': _get_field(fundamental, 'roa'),
            'revenue_growth': _get_field(fundamental, 'revenue_growth'),
            'earnings_growth': _get_field(fundamental, 'earnings_growth'),
            'debt_to_equity': _get_field(fundamental, 'debt_to_equity'),
            'current_ratio': _get_field(fundamental, 'current_ratio'),
            'quick_ratio': _get_field(fundamental, 'quick_ratio'),
            'dividend_yield': _get_field(fundamental, 'dividend_yield'),
            'dividend_rate': _get_field(fundamental, 'dividend_rate'),
            'payout_ratio': _get_field(fundamental, 'payout_ratio'),
            'current_price': _get_field(fundamental, 'current_price'),
            'day_change_percent': _get_field(fundamental, 'day_change_percent'),
            'volume': _get_field(fundamental, 'volume'),
            'avg_volume': _get_field(fundamental, 'avg_volume'),
            'beta': _get_field(fundamental, 'beta'),
            'fifty_two_week_high': _get_field(fundamental, 'fifty_two_week_high'),
            'fifty_two_week_low': _get_field(fundamental, 'fifty_two_week_low'),
            'last_updated': fundamental.last_updated.isoformat() if fundamental and fundamental.last_updated else None
        }
        stocks.append(_json_safe_row(stock_row))

    return stocks, total
