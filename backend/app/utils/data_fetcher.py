from typing import Optional, Dict, Any, List
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta, date
import time
from functools import wraps
from app.config import settings

# ====================================
# RATE LIMITER
# ====================================

class RateLimiter:
    """Rate limiter to prevent hitting yfinance limits"""
    
    def __init__(self, calls_per_minute: int = 30):
        self.calls_per_minute = calls_per_minute
        self.min_interval = 60.0 / calls_per_minute
        self.last_call = None
    
    def wait_if_needed(self):
        """Sleep if we're calling too fast"""
        if self.last_call is not None:
            elapsed = time.time() - self.last_call
            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                time.sleep(sleep_time)
        self.last_call = time.time()

# Global rate limiters
fundamentals_limiter = RateLimiter(calls_per_minute=settings.YFINANCE_REQUESTS_PER_MINUTE)
price_data_limiter = RateLimiter(calls_per_minute=settings.YFINANCE_REQUESTS_PER_MINUTE)

def rate_limited(limiter):
    """Decorator to rate limit function calls"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            limiter.wait_if_needed()
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ====================================
# TICKER LISTS
# ====================================

def get_all_us_tickers() -> List[str]:
    """
    Fetch comprehensive list of all US exchange traded stocks.
    Sources: NASDAQ FTP (most reliable)
    
    Returns:
        List of ~7,000-8,000 ticker symbols
    """
    all_tickers = []
    
    try:
        print("Fetching US stock tickers from NASDAQ FTP...")
        
        # NASDAQ-listed stocks
        nasdaq_url = "ftp://ftp.nasdaqtrader.com/symboldirectory/nasdaqlisted.txt"
        nasdaq_df = pd.read_csv(nasdaq_url, sep="|")
        nasdaq_df = nasdaq_df[nasdaq_df['Test Issue'] == 'N']  # Exclude test issues
        nasdaq_tickers = nasdaq_df['Symbol'].astype(str).tolist()  # Convert to string first
        
        # Other exchanges (NYSE, AMEX, etc.)
        other_url = "ftp://ftp.nasdaqtrader.com/symboldirectory/otherlisted.txt"
        other_df = pd.read_csv(other_url, sep="|")
        other_df = other_df[other_df['Test Issue'] == 'N']
        other_tickers = other_df['ACT Symbol'].astype(str).tolist()  # Convert to string first
        
        # Combine
        all_tickers = nasdaq_tickers + other_tickers
        
        # Clean - now safe to strip since they're all strings
        all_tickers = [str(t).strip() for t in all_tickers if t and str(t).strip() and str(t) != 'nan']
        all_tickers = [t for t in all_tickers if not t.endswith('.TEST')]
        all_tickers = list(set(all_tickers))  # Remove duplicates
        
        print(f"✓ Fetched {len(all_tickers)} US stock tickers from NASDAQ")
        return all_tickers
        
    except Exception as e:
        print(f"✗ Error fetching US tickers: {e}")
        return []


def get_sp500_tickers() -> List[str]:
    """
    Fetch S&P 500 ticker list from Wikipedia (with User-Agent header)
    Fallback option if NASDAQ fails
    """
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        
        # Add headers to avoid 403 error
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        tables = pd.read_html(url, storage_options=headers)
        df = tables[0]
        tickers = df['Symbol'].astype(str).tolist()
        tickers = [t.replace('.', '-') for t in tickers if str(t) != 'nan']
        
        print(f"✓ Fetched {len(tickers)} S&P 500 tickers from Wikipedia")
        return tickers
    except Exception as e:
        print(f"✗ Error fetching S&P 500 list: {e}")
        return []


# ====================================
# FUNDAMENTAL DATA
# ====================================

@rate_limited(fundamentals_limiter)
def fetch_stock_fundamentals(ticker: str, quiet: bool = False) -> Optional[Dict[str, Any]]:
    """
    Fetch fundamental data for a stock (RATE LIMITED).
    
    Args:
        ticker: Stock ticker symbol
        quiet: Suppress print statements
    
    Returns:
        Dict with fundamental metrics, or None if error
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        if not info or len(info) < 5:
            if not quiet:
                print(f"✗ No fundamental data for {ticker}")
            return None
        
        fundamentals = {
            # Basic info
            "ticker": ticker.upper(),
            "name": info.get("longName") or info.get("shortName"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "market_cap": info.get("marketCap"),
            
            # Valuation
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "peg_ratio": info.get("pegRatio"),
            "pb_ratio": info.get("priceToBook"),
            "ps_ratio": info.get("priceToSalesTrailing12Months"),
            "ev_to_ebitda": info.get("enterpriseToEbitda"),
            
            # Profitability
            "eps": info.get("trailingEps"),
            "profit_margin": info.get("profitMargins"),
            "operating_margin": info.get("operatingMargins"),
            "roe": info.get("returnOnEquity"),
            "roa": info.get("returnOnAssets"),
            
            # Growth
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            
            # Financial health
            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
            "quick_ratio": info.get("quickRatio"),
            
            # Dividends
            "dividend_yield": info.get("dividendYield"),
            "dividend_rate": info.get("dividendRate"),
            "payout_ratio": info.get("payoutRatio"),
            
            # Trading
            "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "day_change_percent": info.get("regularMarketChangePercent"),
            "volume": info.get("volume"),
            "avg_volume": info.get("averageVolume"),
            "beta": info.get("beta"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            
            # Store full raw data
            "raw_data": info
        }
        
        if not quiet:
            print(f"✓ Fundamentals for {ticker}")
        
        return fundamentals
        
    except Exception as e:
        if not quiet:
            print(f"✗ Error fetching {ticker}: {e}")
        return None


# ====================================
# HISTORICAL PRICE DATA
# ====================================

@rate_limited(price_data_limiter)
def fetch_price_history(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    quiet: bool = False
) -> Optional[pd.DataFrame]:
    """
    Fetch historical OHLCV data (RATE LIMITED).
    
    Args:
        ticker: Stock ticker
        period: '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'max'
        interval: '1m', '5m', '15m', '30m', '1h', '1d', '1wk', '1mo'
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        quiet: Suppress prints
    
    Returns:
        DataFrame with OHLCV data
    """
    try:
        stock = yf.Ticker(ticker)
        
        if start_date and end_date:
            history = stock.history(start=start_date, end=end_date, interval=interval)
        elif start_date:
            history = stock.history(start=start_date, interval=interval)
        else:
            history = stock.history(period=period, interval=interval)
        
        if history.empty:
            if not quiet:
                print(f"✗ No price data for {ticker}")
            return None
        
        history = history[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        history.index.name = 'Date'
        history = history.dropna(subset=['Open', 'High', 'Low', 'Close'])
        
        if not quiet:
            print(f"✓ Fetched {len(history)} price records for {ticker}")
        
        return history
        
    except Exception as e:
        if not quiet:
            print(f"✗ Error fetching prices for {ticker}: {e}")
        return None


@rate_limited(price_data_limiter)
def prepare_backtest_data(
    ticker: str,
    start_date: str,
    end_date: str,
    include_splits: bool = True,
    include_dividends: bool = True,
    quiet: bool = False
) -> Optional[pd.DataFrame]:
    """
    Prepare data for backtesting with returns, splits, dividends (RATE LIMITED).
    """
    try:
        stock = yf.Ticker(ticker)
        history = stock.history(start=start_date, end=end_date, actions=True)
        
        if history.empty:
            if not quiet:
                print(f"✗ No data for {ticker}")
            return None
        
        df = pd.DataFrame({
            'Open': history['Open'],
            'High': history['High'],
            'Low': history['Low'],
            'Close': history['Close'],
            'Volume': history['Volume'],
            'Adj_Close': history['Close'],
        })
        
        df['Returns'] = df['Adj_Close'].pct_change()
        
        if include_dividends and 'Dividends' in history.columns:
            df['Dividends'] = history['Dividends']
        
        if include_splits and 'Stock Splits' in history.columns:
            df['Stock_Splits'] = history['Stock Splits']
        
        df.index.name = 'Date'
        
        if not quiet:
            print(f"✓ Prepared {len(df)} days for {ticker}")
        
        return df
        
    except Exception as e:
        if not quiet:
            print(f"✗ Error preparing backtest data for {ticker}: {e}")
        return None


# ====================================
# TECHNICAL INDICATORS
# ====================================

def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add technical indicators to price DataFrame"""
    df = df.copy()
    
    # Moving Averages
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()
    
    df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()
    
    # MACD
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI_14'] = 100 - (100 / (1 + rs))
    
    # Bollinger Bands
    df['BB_Middle'] = df['Close'].rolling(window=20).mean()
    bb_std = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
    df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
    
    # Volume
    df['Volume_SMA_20'] = df['Volume'].rolling(window=20).mean()
    
    return df


# ====================================
# UTILITY FUNCTIONS
# ====================================

def validate_ticker(ticker: str) -> bool:
    """Check if ticker is valid"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return info and len(info) > 5 and info.get("regularMarketPrice") is not None
    except:
        return False