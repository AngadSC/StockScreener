from sqlalchemy.orm import Session
from app.database.models import Stock, StockPrice
from app.utils.data_fetcher import fetch_stock_fundamentals
from app.services.cache import cache_service
from typing import Optional, List
from datetime import datetime, date
import yfinance as yf


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


def update_or_create_stock(db: Session, ticker: str) -> Optional[Stock]:
    """
    Fetch latest data from yfinance and update/create stock in database
    """
    fundamentals = fetch_stock_fundamentals(ticker)
    if not fundamentals:
        return None
    
    # Check if stock exists
    stock = get_stock_from_db(db, ticker)
    
    if stock:
        # Update existing
        for key, value in fundamentals.items():
            if key != "ticker" and hasattr(stock, key):
                setattr(stock, key, value)
    else:
        # Create new
        stock = Stock(**fundamentals)
        db.add(stock)
    
    db.commit()
    db.refresh(stock)
    
    # Invalidate cache
    cache_service.delete(f"stock:{ticker}")
    
    return stock

def get_stock_prices(db: Session, ticker: str, start_date: date, end_date: date) -> List[StockPrice]:
    """Get historical prices from database"""
    return db.query(StockPrice).filter(
        StockPrice.ticker == ticker.upper(),
        StockPrice.date >= start_date,
        StockPrice.date <= end_date
    ).order_by(StockPrice.date).all()

#imrpvoed bulk fetching 
def needs_price_update(db: Session, ticker: str, days_threshold: int = 1) -> bool:
    """Check if we need to fetch new price data"""
    latest = db.query(StockPrice).filter(
        StockPrice.ticker == ticker.upper()
    ).order_by(StockPrice.date.desc()).first()
    
    if not latest:
        return True
    
    days_old = (datetime.now().date() - latest.date).days
    return days_old >= days_threshold

def fetch_bulk_prices(
    db: Session, 
    tickers: List[str], 
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> dict:
    """
    Fetch prices for multiple stocks efficiently
    Returns: {"success": [...], "failed": [...]}
    """
    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).date()
    if not end_date:
        end_date = datetime.now().date()
    
    success = []
    failed = []
    
    print(f"Fetching prices for {len(tickers)} tickers...")
    
    try:
        # Bulk download
        data = yf.download(
            tickers,
            start=start_date,
            end=end_date,
            group_by='ticker',
            auto_adjust=True,
            progress=False
        )
        
        if len(tickers) == 1:
            ticker = tickers[0]
            _store_prices_for_ticker(db, ticker, data)
            success.append(ticker)
        else:
            for ticker in tickers:
                try:
                    ticker_data = data[ticker]
                    if not ticker_data.empty:
                        _store_prices_for_ticker(db, ticker, ticker_data)
                        success.append(ticker)
                    else:
                        failed.append(ticker)
                except Exception as e:
                    print(f"Error processing {ticker}: {e}")
                    failed.append(ticker)
        
        db.commit()
        
    except Exception as e:
        print(f"Bulk download error: {e}")
        db.rollback()
        failed.extend(tickers)
    
    return {"success": success, "failed": failed}

def _store_prices_for_ticker(db: Session, ticker: str, data: pd.DataFrame):
    """Helper to store price data for a single ticker"""
    ticker = ticker.upper()
    
    for date_idx, row in data.iterrows():
        if pd.isna(row['Open']) or pd.isna(row['Close']):
            continue
            
        price = StockPrice(
            ticker=ticker,
            date=date_idx.date() if hasattr(date_idx, 'date') else date_idx,
            open=float(row['Open']),
            high=float(row['High']),
            low=float(row['Low']),
            close=float(row['Close']),
            volume=int(row['Volume']) if not pd.isna(row['Volume']) else 0
        )
        db.merge(price)

def get_prices_for_model(db: Session, ticker: str, lookback_days: int = 365) -> pd.DataFrame:
    """
    Get price data formatted for ML models
    Auto-fetches if missing
    """
    ticker = ticker.upper()
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=lookback_days)
    
    # Check if we have data
    if needs_price_update(db, ticker):
        print(f"Fetching fresh data for {ticker}...")
        fetch_bulk_prices(db, [ticker], start_date, end_date)
    
    # Query from database
    prices = get_stock_prices(db, ticker, start_date, end_date)
    
    # Convert to DataFrame
    df = pd.DataFrame([{
        'date': p.date,
        'open': p.open,
        'high': p.high,
        'low': p.low,
        'close': p.close,
        'volume': p.volume
    } for p in prices])
    
    if not df.empty:
        df.set_index('date', inplace=True)
    
    return df

def fetch_and_store_prices(db: Session, ticker: str, period: str = "1y") -> bool:
    """
    Fetch historical prices from yfinance and store in database
    period: '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'
    """
    period_map = {
        "1d": 1, "5d": 5, "1mo": 30, "3mo": 90,
        "6mo": 180, "1y": 365, "2y": 730, "5y": 1825, "max": 3650
    }
    days = period_map.get(period, 365)
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    result = fetch_bulk_prices(db, [ticker], start_date, end_date)
    return ticker in result["success"]