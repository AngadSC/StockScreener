from sqlalchemy.orm import Session
from app.database.models import Stock, StockPrice
from app.utils.data_fetcher import fmp_client, tiingo_client
from app.utils.market_calendar import (
    get_last_trading_day, 
    detect_missing_days,
    get_trading_days_between
)
from app.services.cache import cache_service
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
import pandas as pd

# ====================================
# STOCK FUNDAMENTALS
# ====================================

def get_stock_from_db(db: Session, ticker: str) -> Optional[Stock]:
    """Get stock from database"""
    return db.query(Stock).filter(Stock.ticker == ticker.upper()).first()

def get_stock_with_cache(db: Session, ticker: str) -> Optional[dict]:
    """
    Get stock data with Redis caching:
    1. Check Redis cache
    2. If miss, query database
    3. If not in DB, return None
    4. Cache result in Redis
    """
    ticker = ticker.upper()
    cache_key = f"stock:{ticker}"
    
    # Try cache first
    cached = cache_service.get(cache_key)
    if cached:
        return cached
    
    # Query database
    stock = get_stock_from_db(db, ticker)
    if not stock:
        return None
    
    # Convert to dict and cache
    stock_dict = {
        "ticker": stock.ticker,
        "name": stock.name,
        "sector": stock.sector,
        "industry": stock.industry,
        "market_cap": stock.market_cap,
        
        # Valuation
        "pe_ratio": stock.pe_ratio,
        "forward_pe": stock.forward_pe,
        "peg_ratio": stock.peg_ratio,
        "pb_ratio": stock.pb_ratio,
        "ps_ratio": stock.ps_ratio,
        "ev_to_ebitda": stock.ev_to_ebitda,
        
        # Profitability
        "eps": stock.eps,
        "profit_margin": stock.profit_margin,
        "operating_margin": stock.operating_margin,
        "roe": stock.roe,
        "roa": stock.roa,
        
        # Growth
        "revenue_growth": stock.revenue_growth,
        "earnings_growth": stock.earnings_growth,
        
        # Financial health
        "debt_to_equity": stock.debt_to_equity,
        "current_ratio": stock.current_ratio,
        "quick_ratio": stock.quick_ratio,
        
        # Dividends
        "dividend_yield": stock.dividend_yield,
        "dividend_rate": stock.dividend_rate,
        "payout_ratio": stock.payout_ratio,
        
        # Trading
        "current_price": stock.current_price,
        "day_change_percent": stock.day_change_percent,
        "volume": stock.volume,
        "avg_volume": stock.avg_volume,
        "beta": stock.beta,
        "fifty_two_week_high": stock.fifty_two_week_high,
        "fifty_two_week_low": stock.fifty_two_week_low,
        
        # Metadata
        "last_updated": stock.last_updated.isoformat() if stock.last_updated else None,
        "created_at": stock.created_at.isoformat() if stock.created_at else None
    }
    
    cache_service.set(cache_key, stock_dict)
    return stock_dict


# ====================================
# PRICE HISTORY - POSTGRESQL FIRST
# ====================================

def get_price_history(
    db: Session, 
    ticker: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    use_cache: bool = True
) -> pd.DataFrame:
    """
    Get historical price data for a stock (PostgreSQL-first architecture)
    
    Flow:
    1. Check Redis cache (if enabled)
    2. Check if data exists in PostgreSQL
    3. If missing, initialize from Tiingo (4 years)
    4. If stale, fill gaps from Tiingo
    5. Cache result in Redis
    6. Return complete dataset
    
    Args:
        db: Database session
        ticker: Stock symbol
        start_date: Start date (defaults to 4 years ago)
        end_date: End date (defaults to last trading day)
        use_cache: Whether to use Redis cache
    
    Returns:
        DataFrame with OHLCV data
    """
    ticker = ticker.upper()
    
    # Set defaults
    if end_date is None:
        end_date = get_last_trading_day()
    if start_date is None:
        start_date = end_date - timedelta(days=365 * 4)  # 4 years
    
    # Check cache
    if use_cache:
        cache_key = f"prices:{ticker}:historical"
        cached = cache_service.get(cache_key)
        if cached:
            df = pd.DataFrame(cached)
            if not df.empty:
                df['date'] = pd.to_datetime(df['date']).dt.date
                df = df.set_index('date')
                # Filter to requested range
                return df[(df.index >= start_date) & (df.index <= end_date)]
    
    # Query database for existing data
    prices = db.query(StockPrice).filter(
        StockPrice.ticker == ticker
    ).order_by(StockPrice.date).all()
    
    # CASE 1: No data exists - Initialize from Tiingo
    if not prices:
        print(f"📥 Initializing {ticker} with {settings.STOCK_HISTORY_YEARS} years of data from Tiingo...")
        df = _initialize_stock_history(db, ticker, start_date, end_date)
        
        if df is not None and not df.empty:
            # Cache the result
            if use_cache:
                cache_data = df.reset_index().to_dict('records')
                cache_service.set(f"prices:{ticker}:historical", cache_data, ttl=settings.PRICE_HISTORY_CACHE_TTL)
            return df
        else:
            return pd.DataFrame()
    
    # Convert DB records to DataFrame
    df = pd.DataFrame([{
        'date': p.date,
        'Open': p.open,
        'High': p.high,
        'Low': p.low,
        'Close': p.close,
        'Volume': p.volume
    } for p in prices])
    
    if df.empty:
        return df
    
    df = df.set_index('date')
    df.index = pd.to_datetime(df.index).date
    
    # CASE 2: Check for gaps (freshness + missing days)
    latest_date = df.index.max()
    last_trading_day = get_last_trading_day()
    
    gaps_filled = False
    
    # Check if data is stale
    if latest_date < last_trading_day:
        print(f"📊 {ticker} data is stale (latest: {latest_date}, expected: {last_trading_day})")
        gap_start = latest_date + timedelta(days=1)
        gap_df = _fill_price_gap(db, ticker, gap_start, last_trading_day)
        
        if gap_df is not None and not gap_df.empty:
            df = pd.concat([df, gap_df])
            gaps_filled = True
    
    # Check for missing days within the range
    existing_dates = df.index.tolist()
    missing_days = detect_missing_days(existing_dates, start_date, end_date)
    
    if missing_days:
        print(f"📊 {ticker} has {len(missing_days)} missing trading days, filling gaps...")
        for missing_date in missing_days:
            # Fill small gaps (group consecutive days)
            gap_df = _fill_price_gap(db, ticker, missing_date, missing_date)
            if gap_df is not None and not gap_df.empty:
                df = pd.concat([df, gap_df])
                gaps_filled = True
    
    # Sort and remove duplicates
    df = df.sort_index()
    df = df[~df.index.duplicated(keep='last')]
    
    # Cache if we filled gaps
    if gaps_filled and use_cache:
        cache_data = df.reset_index().to_dict('records')
        cache_service.set(f"prices:{ticker}:historical", cache_data, ttl=settings.PRICE_HISTORY_CACHE_TTL)
    
    # Filter to requested range
    return df[(df.index >= start_date) & (df.index <= end_date)]


def _initialize_stock_history(
    db: Session,
    ticker: str,
    start_date: date,
    end_date: date
) -> Optional[pd.DataFrame]:
    """
    Initialize stock with historical data from Tiingo
    
    Args:
        db: Database session
        ticker: Stock symbol
        start_date: Start date
        end_date: End date
    
    Returns:
        DataFrame with historical prices
    """
    try:
        # Fetch from Tiingo
        df = tiingo_client.get_historical_prices(
            ticker,
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )
        
        if df is None or df.empty:
            print(f"✗ No historical data available for {ticker}")
            return None
        
        # Save to database
        for date_idx, row in df.iterrows():
            price = StockPrice(
                ticker=ticker,
                date=date_idx,
                open=float(row['Open']),
                high=float(row['High']),
                low=float(row['Low']),
                close=float(row['Close']),
                volume=int(row['Volume']) if not pd.isna(row['Volume']) else 0
            )
            db.merge(price)  # Use merge to handle duplicates
        
        db.commit()
        print(f"✓ Initialized {ticker} with {len(df)} records")
        
        return df
        
    except Exception as e:
        print(f"✗ Error initializing {ticker}: {e}")
        db.rollback()
        return None


def _fill_price_gap(
    db: Session,
    ticker: str,
    start_date: date,
    end_date: date
) -> Optional[pd.DataFrame]:
    """
    Fill missing price data using Tiingo
    
    Args:
        db: Database session
        ticker: Stock symbol
        start_date: Gap start date
        end_date: Gap end date
    
    Returns:
        DataFrame with gap-filled data
    """
    try:
        # Fetch missing data from Tiingo
        df = tiingo_client.get_historical_prices(
            ticker,
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d"),
            quiet=True
        )
        
        if df is None or df.empty:
            return None
        
        # Save to database
        for date_idx, row in df.iterrows():
            price = StockPrice(
                ticker=ticker,
                date=date_idx,
                open=float(row['Open']),
                high=float(row['High']),
                low=float(row['Low']),
                close=float(row['Close']),
                volume=int(row['Volume']) if not pd.isna(row['Volume']) else 0
            )
            db.merge(price)
        
        db.commit()
        print(f"✓ Filled gap for {ticker}: {start_date} to {end_date} ({len(df)} records)")
        
        # Invalidate cache
        cache_service.delete(f"prices:{ticker}:historical")
        
        return df
        
    except Exception as e:
        print(f"✗ Error filling gap for {ticker}: {e}")
        db.rollback()
        return None


# ====================================
# HELPER FUNCTIONS
# ====================================

def get_active_tickers(db: Session) -> List[str]:
    """
    Get list of tickers that have been initialized (have price data in DB)
    These are the stocks we'll update in the nightly batch job
    """
    result = db.query(StockPrice.ticker).distinct().all()
    return [r[0] for r in result]


def invalidate_stock_cache(ticker: str):
    """Invalidate all cache entries for a stock"""
    cache_service.delete(f"stock:{ticker}")
    cache_service.delete(f"prices:{ticker}:historical")
