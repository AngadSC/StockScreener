from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import date, datetime
import time
import random
import yfinance as yf
from curl_cffi import requests
from app.providers.base import StockDataProvider
from app.config import settings

# ============================================
# USER AGENT ROTATION (20 recent browsers)
# ============================================
USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    
    # Firefox on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
    
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    
    # Chrome on Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    
    # Firefox on Linux
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
]


class YFinanceProvider(StockDataProvider):
    """
    YFinance provider with stealth features:
    - curl_cffi for TLS fingerprint mimicry
    - User-Agent rotation
    - Random jitter between requests
    """
    
    def __init__(self):
        self._session = None
        self._request_count = 0
    
    @property
    def name(self) -> str:
        return "yfinance"
    
    def _get_session(self):
        """Create or return stealth session"""
        if self._session is None:
            # Use curl_cffi to mimic Chrome browser
            self._session = requests.Session(impersonate="chrome110")
            
            # Set random user agent
            self._session.headers['User-Agent'] = random.choice(USER_AGENTS)
        
        return self._session
    
    def _rotate_user_agent(self):
        """Rotate user agent for next request"""
        if self._session:
            self._session.headers['User-Agent'] = random.choice(USER_AGENTS)
    
    def _apply_jitter(self, is_bulk_load: bool = False):
        """Apply random sleep to avoid rate limiting"""
        if not settings.RATE_LIMIT_ENABLED:
            return
        
        if is_bulk_load:
            sleep_time = random.uniform(
                settings.YFINANCE_INITIAL_JITTER_MIN,
                settings.YFINANCE_INITIAL_JITTER_MAX
            )
        else:
            sleep_time = random.uniform(
                settings.YFINANCE_DAILY_JITTER_MIN,
                settings.YFINANCE_DAILY_JITTER_MAX
            )
        
        time.sleep(sleep_time)
        self._request_count += 1
        
        # Rotate user agent every 10 requests
        if self._request_count % 10 == 0:
            self._rotate_user_agent()
    
    def get_historical_prices(
        self,
        ticker: str,
        start_date: date,
        end_date: date
    ) -> Optional[pd.DataFrame]:
        """Fetch historical data for single stock"""
        try:
            session = self._get_session()
            
            stock = yf.Ticker(ticker, session=session)
            df = stock.history(
                start=start_date,
                end=end_date,
                auto_adjust=True,  # Use adjusted prices
                actions=True       # Include splits/dividends
            )
            
            if df.empty:
                print(f"✗ No data for {ticker}")
                return None
            
            # Extract OHLCV
            result = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
            result.index = pd.to_datetime(result.index).date
            
            # Store splits and dividends separately (will be handled by service layer)
            if 'Dividends' in df.columns:
                dividends = df[df['Dividends'] > 0]['Dividends']
                if not dividends.empty:
                    result._dividends = dividends  # Attach as metadata
            
            if 'Stock Splits' in df.columns:
                splits = df[df['Stock Splits'] > 0]['Stock Splits']
                if not splits.empty:
                    result._splits = splits  # Attach as metadata
            
            return result
            
        except Exception as e:
            print(f"✗ YFinance error for {ticker}: {e}")
            return None
    
    def get_batch_historical_prices(
        self,
        tickers: List[str],
        start_date: date,
        end_date: date,
        is_bulk_load: bool = False
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical data for multiple stocks
        Returns long-format DataFrame ready for database insertion
        """
        try:
            session = self._get_session()
            
            # Download batch
            data = yf.download(
                tickers=tickers,
                start=start_date,
                end=end_date,
                session=session,
                threads=False,  # Critical: No threading to avoid detection
                auto_adjust=True,
                actions=True,
                progress=False,
                show_errors=False
            )
            
            if data.empty:
                print(f"✗ No data for batch")
                return None
            
            # Handle single ticker vs multiple tickers
            if len(tickers) == 1:
                # Single ticker - simple format
                ticker = tickers[0]
                df = data[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
                df['ticker'] = ticker
                df['date'] = df.index.date
                df = df.reset_index(drop=True)
            else:
                # Multiple tickers - multi-index format
                # Convert from wide format (columns per ticker) to long format
                df = data.stack(level=1, future_stack=True).reset_index()
                df.columns = ['date', 'ticker', 'Open', 'High', 'Low', 'Close', 'Volume', 'Dividends', 'Stock Splits']
                df['date'] = pd.to_datetime(df['date']).dt.date
            
            # Drop rows with NaN in critical columns
            df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])
            
            # Ensure volume is integer
            df['Volume'] = df['Volume'].fillna(0).astype('int64')
            
            # Filter to only requested columns for OHLCV
            result = df[['date', 'ticker', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
            
            # Extract dividends and splits if present
            if 'Dividends' in df.columns:
                dividends = df[df['Dividends'] > 0][['date', 'ticker', 'Dividends']]
                if not dividends.empty:
                    result._dividends = dividends
            
            if 'Stock Splits' in df.columns:
                splits = df[df['Stock Splits'] > 0][['date', 'ticker', 'Stock Splits']]
                if not splits.empty:
                    result._splits = splits
            
            # Apply jitter after batch
            self._apply_jitter(is_bulk_load=is_bulk_load)
            
            return result
            
        except Exception as e:
            print(f"✗ YFinance batch error: {e}")
            return None
    
    def get_fundamentals(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Fetch fundamental data for single stock"""
        try:
            session = self._get_session()
            stock = yf.Ticker(ticker, session=session)
            info = stock.info
            
            if not info or len(info) < 5:
                return None
            
            # Extract and normalize fundamental data
            fundamentals = {
                'ticker': ticker,
                
                # Valuation
                'pe_ratio': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'peg_ratio': info.get('pegRatio'),
                'price_to_book': info.get('priceToBook'),
                'price_to_sales': info.get('priceToSalesTrailing12Months'),
                'ev_to_ebitda': info.get('enterpriseToEbitda'),
                
                # Profitability
                'profit_margin': info.get('profitMargins'),
                'operating_margin': info.get('operatingMargins'),
                'roe': info.get('returnOnEquity'),
                'roa': info.get('returnOnAssets'),
                
                # Financial Health
                'debt_to_equity': info.get('debtToEquity'),
                'current_ratio': info.get('currentRatio'),
                'quick_ratio': info.get('quickRatio'),
                
                # Growth
                'revenue_growth': info.get('revenueGrowth'),
                'earnings_growth': info.get('earningsGrowth'),
                
                # Dividends
                'dividend_yield': info.get('dividendYield'),
                'dividend_rate': info.get('dividendRate'),
                'payout_ratio': info.get('payoutRatio'),
                
                # Size & Trading
                'market_cap': info.get('marketCap'),
                'volume': info.get('volume'),
                'avg_volume': info.get('averageVolume'),
                'beta': info.get('beta'),
                
                # Price
                'current_price': info.get('currentPrice') or info.get('regularMarketPrice'),
                'day_change_percent': info.get('regularMarketChangePercent'),
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
                
                # Classification
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                
                # Everything else goes in additional_data
                'additional_data': {k: v for k, v in info.items() if k not in [
                    'trailingPE', 'forwardPE', 'pegRatio', 'priceToBook', 
                    'priceToSalesTrailing12Months', 'enterpriseToEbitda',
                    'profitMargins', 'operatingMargins', 'returnOnEquity', 'returnOnAssets',
                    'debtToEquity', 'currentRatio', 'quickRatio',
                    'revenueGrowth', 'earningsGrowth',
                    'dividendYield', 'dividendRate', 'payoutRatio',
                    'marketCap', 'volume', 'averageVolume', 'beta',
                    'currentPrice', 'regularMarketPrice', 'regularMarketChangePercent',
                    'fiftyTwoWeekHigh', 'fiftyTwoWeekLow',
                    'sector', 'industry'
                ]}
            }
            
            return fundamentals
            
        except Exception as e:
            print(f"✗ YFinance fundamentals error for {ticker}: {e}")
            return None
    
    def get_batch_fundamentals(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        YFinance doesn't support batch fundamentals efficiently
        This method calls get_fundamentals() for each ticker
        """
        results = {}
        
        for ticker in tickers:
            fundamentals = self.get_fundamentals(ticker)
            if fundamentals:
                results[ticker] = fundamentals
            
            # Small delay between requests
            if settings.RATE_LIMIT_ENABLED:
                time.sleep(random.uniform(0.5, 1.5))
        
        return results
    
    def supports_batch(self) -> bool:
        """YFinance supports batch for OHLCV, not for fundamentals"""
        return True
    
    def get_rate_limit_info(self) -> Dict[str, Any]:
        """Return rate limit info for monitoring"""
        return {
            'provider': 'yfinance',
            'requests_made': self._request_count,
            'rate_limit': 'Unknown (uses stealth to avoid limits)',
            'jitter_enabled': settings.RATE_LIMIT_ENABLED
        }
