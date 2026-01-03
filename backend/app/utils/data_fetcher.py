from typing import Optional, Dict, Any, List
import requests
import pandas as pd
from datetime import datetime, timedelta, date
import time
from functools import wraps
from app.config import settings

# ====================================
# RATE LIMITER
# ====================================

class RateLimiter:
    """Rate limiter to prevent hitting API limits"""
    
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
tiingo_limiter = RateLimiter(calls_per_minute=50)  # 50 requests/hour = ~0.83/min
fmp_limiter = RateLimiter(calls_per_minute=10)  # Conservative for free tier

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
# FMP API CLIENT
# ====================================

class FMPClient:
    """Financial Modeling Prep API Client"""
    
    def __init__(self):
        self.base_url = settings.FMP_BASE_URL
        self.api_key = settings.FMP_API_KEY
        self.batch_size = settings.FMP_BATCH_SIZE
    
    @rate_limited(fmp_limiter)
    def get_batch_quotes(self, tickers: List[str], quiet: bool = False) -> List[Dict[str, Any]]:
        """
        Fetch real-time/EOD quotes for multiple stocks in one request
        
        Args:
            tickers: List of ticker symbols (max 100 recommended)
            quiet: Suppress print statements
        
        Returns:
            List of quote dictionaries
        """
        try:
            # Join tickers with comma
            symbols = ",".join(tickers[:self.batch_size])
            
            url = f"{self.base_url}/quote/{symbols}"
            params = {"apikey": self.api_key}
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if not quiet:
                print(f"✓ Fetched {len(data)} quotes from FMP")
            
            return data
            
        except Exception as e:
            if not quiet:
                print(f"✗ FMP batch quote error: {e}")
            return []
    
    @rate_limited(fmp_limiter)
    def get_historical_prices(
        self, 
        ticker: str, 
        from_date: str, 
        to_date: str,
        quiet: bool = False
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical OHLCV data for a single stock
        
        Args:
            ticker: Stock symbol
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            quiet: Suppress prints
        
        Returns:
            DataFrame with historical prices
        """
        try:
            url = f"{self.base_url}/historical-price-full/{ticker}"
            params = {
                "apikey": self.api_key,
                "from": from_date,
                "to": to_date
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if "historical" not in data or not data["historical"]:
                if not quiet:
                    print(f"✗ No historical data for {ticker}")
                return None
            
            df = pd.DataFrame(data["historical"])
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            df = df.sort_index()
            
            # Rename columns to match our schema
            df = df.rename(columns={
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            })
            
            if not quiet:
                print(f"✓ Fetched {len(df)} historical records for {ticker}")
            
            return df[['Open', 'High', 'Low', 'Close', 'Volume']]
            
        except Exception as e:
            if not quiet:
                print(f"✗ FMP historical error for {ticker}: {e}")
            return None


# ====================================
# TIINGO API CLIENT
# ====================================

class TiingoClient:
    """Tiingo API Client for historical data"""
    
    def __init__(self):
        self.base_url = settings.TIINGO_BASE_URL
        self.api_key = settings.TIINGO_API_KEY
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Token {self.api_key}'
        }
    
    @rate_limited(tiingo_limiter)
    def get_historical_prices(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        quiet: bool = False
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical EOD prices from Tiingo
        
        Args:
            ticker: Stock symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            quiet: Suppress prints
        
        Returns:
            DataFrame with OHLCV data
        """
        try:
            url = f"{self.base_url}/tiingo/daily/{ticker}/prices"
            params = {
                'startDate': start_date,
                'endDate': end_date,
                'format': 'json'
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                if not quiet:
                    print(f"✗ No data from Tiingo for {ticker}")
                return None
            
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date']).dt.date
            df = df.set_index('date')
            
            # Use adjusted prices for consistency
            df = df.rename(columns={
                'adjOpen': 'Open',
                'adjHigh': 'High',
                'adjLow': 'Low',
                'adjClose': 'Close',
                'adjVolume': 'Volume'
            })
            
            if not quiet:
                print(f"✓ Fetched {len(df)} records from Tiingo for {ticker}")
            
            return df[['Open', 'High', 'Low', 'Close', 'Volume']]
            
        except Exception as e:
            if not quiet:
                print(f"✗ Tiingo error for {ticker}: {e}")
            return None
    
    @rate_limited(tiingo_limiter)
    def get_ticker_metadata(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a ticker from Tiingo"""
        try:
            url = f"{self.base_url}/tiingo/daily/{ticker}"
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"✗ Tiingo metadata error for {ticker}: {e}")
            return None


# ====================================
# SINGLETON INSTANCES
# ====================================

fmp_client = FMPClient()
tiingo_client = TiingoClient()


# ====================================
# TICKER LISTS (Keep existing functions)
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
        nasdaq_df = nasdaq_df[nasdaq_df['Test Issue'] == 'N']
        nasdaq_tickers = nasdaq_df['Symbol'].astype(str).tolist()
        
        # Other exchanges (NYSE, AMEX, etc.)
        other_url = "ftp://ftp.nasdaqtrader.com/symboldirectory/otherlisted.txt"
        other_df = pd.read_csv(other_url, sep="|")
        other_df = other_df[other_df['Test Issue'] == 'N']
        other_tickers = other_df['ACT Symbol'].astype(str).tolist()
        
        # Combine
        all_tickers = nasdaq_tickers + other_tickers
        
        # Clean
        all_tickers = [str(t).strip() for t in all_tickers if t and str(t).strip() and str(t) != 'nan']
        all_tickers = [t for t in all_tickers if not t.endswith('.TEST')]
        all_tickers = list(set(all_tickers))
        
        print(f"✓ Fetched {len(all_tickers)} US stock tickers from NASDAQ")
        return all_tickers
        
    except Exception as e:
        print(f"✗ Error fetching US tickers: {e}")
        return []


def get_sp500_tickers() -> List[str]:
    """
    Fetch S&P 500 ticker list from Wikipedia
    Fallback option if NASDAQ fails
    """
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
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
