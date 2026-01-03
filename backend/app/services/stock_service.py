from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.database.models import Ticker, DailyOHLCV, StockFundamental, StockSplit, Dividend
from app.providers.factory import ProviderFactory
from app.utils.market_calendar import get_last_trading_day, detect_missing_days
from app.services.cache import cache_service
from app.config import settings
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
import pandas as pd

# ============================================
# STOCK DATA SERVICE
# PostgreSQL-first architecture
# ============================================

def get_stock_with_fundamentals(db: Session, ticker: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
    """
    Get stock data with fundamentals
    
    Flow:
    1. Check Redis cache
    2. Query PostgreSQL
    3. Cache result
    
    Args:
        db: Database session
        ticker: Stock symbol
        use_cache: Whether to use cache
    
    Returns:
        Dict with stock data and fundamentals
    """
    ticker = ticker.upper()
    cache_key = f"stock:{ticker}"
    
    # Check cache
    if use_cache:
        cached = cache_service.get(cache_key)
        if cached:
            return cached
    
    # Query database
    ticker_obj = db.query(Ticker).filter(Ticker.symbol == ticker).first()
    if not ticker_obj:
        return None
    
    # Get fundamentals
    fundamentals = db.query(StockFundamental).filter(
        StockFundamental.ticker_id == ticker_obj.id
    ).first()
    
    if not fundamentals:
        return None
    
    # Build response
    stock_data = {
        'ticker': ticker_obj.symbol,
        'name': ticker_obj.name,
        
        # Valuation
        'pe_ratio': fundamentals.pe_ratio,
        'forward_pe': fundamentals.forward_pe,
        'peg_ratio': fundamentals.peg_ratio,
        'price_to_book': fundamentals.price_to_book,
        'price_to_sales': fundamentals.price_to_sales,
        'ev_to_ebitda': fundamentals.ev_to_ebitda,
        
        # Profitability
        'profit_margin': fundamentals.profit_margin,
        'operating_margin': fundamentals.operating_margin,
        'roe': fundamentals.roe,
        'roa': fundamentals.roa,
        
        # Financial Health
        'debt_to_equity': fundamentals.debt_to_equity,
        'current_ratio': fundamentals.current_ratio,
        'quick_ratio': fundamentals.quick_ratio,
        
        # Growth
        'revenue_growth': fundamentals.revenue_growth,
        'earnings_growth': fundamentals.earnings_growth,
        
        # Dividends
        'dividend_yield': fundamentals.dividend_yield,
        'dividend_rate': fundamentals.dividend_rate,
        'payout_ratio': fundamentals.payout_ratio,
        
        # Size & Trading
        'market_cap': fundamentals.market_cap,
        'volume': fundamentals.volume,
        'avg_volume': fundamentals.avg_volume,
        'beta': fundamentals.beta,
        
        # Price
        'current_price': fundamentals.current_price,
        'day_change_percent': fundamentals.day_change_percent,
        'fifty_two_week_high': fundamentals.fifty_two_week_high,
        'fifty_two_week_low': fundamentals.fifty_two_week_low,
        
        # Classification
        'sector': fundamentals.sector,
        'industry': fundamentals.industry,
        
        # Metadata
        'last_updated': fundamentals.last_updated.isoformat() if fundamentals.last_updated else None,
        
        # Additional data
        'additional_data': fundamentals.additional_data
    }
    
    # Cache for 24 hours
    if use_cache:
        cache_service.set(cache_key, stock_data, ttl=settings.STOCK_CACHE_TTL)
    
    return stock_data


def get_price_history(
    db: Session,
    ticker: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    use_cache: bool = True
) -> pd.DataFrame:
    """
    Get historical price data for a stock
    
    Flow:
    1. Check Redis cache (for detailed view requests - 2 hour TTL)
    2. Query PostgreSQL
    3. Check for gaps and fill if needed
    4. Cache result
    
    Args:
        db: Database session
        ticker: Stock symbol
        start_date: Start date
        end_date: End date
        use_cache: Whether to use cache
    
    Returns:
        DataFrame with OHLCV data
    """
    ticker = ticker.upper()
    
    # Set defaults
    if end_date is None:
        end_date = get_last_trading_day()
    if start_date is None:
        start_date = end_date - timedelta(days=365)  # Default 1 year
    
    # Check cache (for detailed stock views)
    cache_key = f"prices:{ticker}:detailed"
    if use_cache:
        cached = cache_service.get(cache_key)
        if cached:
            df = pd.DataFrame(cached)
            if not df.empty:
                df['date'] = pd.to_datetime(df['date']).dt.date
                df = df.set_index('date')
                # Filter to requested range
                mask = (df.index >= start_date) & (df.index <= end_date)
                return df[mask]
    
    # Get ticker ID
    ticker_obj = db.query(Ticker).filter(Ticker.symbol == ticker).first()
    if not ticker_obj:
        return pd.DataFrame()
    
    # Query database
    prices = db.query(DailyOHLCV).filter(
        and_(
            DailyOHLCV.ticker_id == ticker_obj.id,
            DailyOHLCV.date >= start_date,
            DailyOHLCV.date <= end_date
        )
    ).order_by(DailyOHLCV.date).all()
    
    if not prices:
        return pd.DataFrame()
    
    # Convert to DataFrame
    df = pd.DataFrame([{
        'date': p.date,
        'Open': p.open,
        'High': p.high,
        'Low': p.low,
        'Close': p.close,
        'Volume': p.volume
    } for p in prices])
    
    df = df.set_index('date')
    
    # Check for gaps (optional - can be disabled for performance)
    # existing_dates = df.index.tolist()
    # missing = detect_missing_days(existing_dates, start_date, end_date)
    # if missing:
    #     # Fill gaps if needed (implementation depends on requirements)
    #     pass
    
    # Cache for 2 hours (for detailed views)
    if use_cache:
        cache_data = df.reset_index().to_dict('records')
        cache_service.set(cache_key, cache_data, ttl=settings.STOCK_DETAIL_CACHE_TTL)
    
    return df


def screen_stocks(
    db: Session,
    filters: Dict[str, Any],
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Screen stocks based on fundamental criteria
    
    ALWAYS queries PostgreSQL directly (no cache)
    
    Args:
        db: Database session
        filters: Dict of filter criteria
        limit: Max results
        offset: Pagination offset
    
    Returns:
        List of stocks matching criteria
    """
    # Build query
    query = db.query(Ticker, StockFundamental).join(
        StockFundamental,
        Ticker.id == StockFundamental.ticker_id
    )
    
    # Apply filters
    if 'pe_ratio_min' in filters and filters['pe_ratio_min'] is not None:
        query = query.filter(StockFundamental.pe_ratio >= filters['pe_ratio_min'])
    
    if 'pe_ratio_max' in filters and filters['pe_ratio_max'] is not None:
        query = query.filter(StockFundamental.pe_ratio <= filters['pe_ratio_max'])
    
    if 'market_cap_min' in filters and filters['market_cap_min'] is not None:
        query = query.filter(StockFundamental.market_cap >= filters['market_cap_min'])
    
    if 'market_cap_max' in filters and filters['market_cap_max'] is not None:
        query = query.filter(StockFundamental.market_cap <= filters['market_cap_max'])
    
    if 'debt_to_equity_max' in filters and filters['debt_to_equity_max'] is not None:
        query = query.filter(StockFundamental.debt_to_equity <= filters['debt_to_equity_max'])
    
    if 'dividend_yield_min' in filters and filters['dividend_yield_min'] is not None:
        query = query.filter(StockFundamental.dividend_yield >= filters['dividend_yield_min'])
    
    if 'roe_min' in filters and filters['roe_min'] is not None:
        query = query.filter(StockFundamental.roe >= filters['roe_min'])
    
    if 'sector' in filters and filters['sector']:
        query = query.filter(StockFundamental.sector == filters['sector'])
    
    if 'industry' in filters and filters['industry']:
        query = query.filter(StockFundamental.industry == filters['industry'])
    
    # Add more filters as needed...
    
    # Apply pagination
    results = query.limit(limit).offset(offset).all()
    
    # Format results
    stocks = []
    for ticker, fundamental in results:
        stocks.append({
            'ticker': ticker.symbol,
            'name': ticker.name,
            'sector': fundamental.sector,
            'industry': fundamental.industry,
            'market_cap': fundamental.market_cap,
            'pe_ratio': fundamental.pe_ratio,
            'dividend_yield': fundamental.dividend_yield,
            'current_price': fundamental.current_price,
            'day_change_percent': fundamental.day_change_percent,
            'roe': fundamental.roe,
            'debt_to_equity': fundamental.debt_to_equity
        })
    
    return stocks


def get_stock_splits(db: Session, ticker: str) -> List[Dict[str, Any]]:
    """Get stock split history"""
    ticker_obj = db.query(Ticker).filter(Ticker.symbol == ticker.upper()).first()
    if not ticker_obj:
        return []
    
    splits = db.query(StockSplit).filter(
        StockSplit.ticker_id == ticker_obj.id
    ).order_by(StockSplit.date.desc()).all()
    
    return [{
        'date': s.date.isoformat(),
        'ratio': s.ratio
    } for s in splits]


def get_dividends(db: Session, ticker: str) -> List[Dict[str, Any]]:
    """Get dividend history"""
    ticker_obj = db.query(Ticker).filter(Ticker.symbol == ticker.upper()).first()
    if not ticker_obj:
        return []
    
    dividends = db.query(Dividend).filter(
        Dividend.ticker_id == ticker_obj.id
    ).order_by(Dividend.date.desc()).all()
    
    return [{
        'date': d.date.isoformat(),
        'amount': d.amount
    } for d in dividends]


def get_all_sectors(db: Session) -> List[str]:
    """Get list of all sectors in database"""
    sectors = db.query(StockFundamental.sector).distinct().all()
    return [s[0] for s in sectors if s[0]]


def get_all_industries(db: Session) -> List[str]:
    """Get list of all industries in database"""
    industries = db.query(StockFundamental.industry).distinct().all()
    return [i[0] for i in industries if i[0]]


def get_database_stats(db: Session) -> Dict[str, Any]:
    """Get database statistics"""
    total_tickers = db.query(Ticker).count()
    total_prices = db.query(DailyOHLCV).count()
    total_fundamentals = db.query(StockFundamental).count()
    
    # Get date range
    min_date = db.query(func.min(DailyOHLCV.date)).scalar()
    max_date = db.query(func.max(DailyOHLCV.date)).scalar()
    
    return {
        'total_tickers': total_tickers,
        'total_price_records': total_prices,
        'total_fundamentals': total_fundamentals,
        'date_range': {
            'start': min_date.isoformat() if min_date else None,
            'end': max_date.isoformat() if max_date else None
        }
    }
