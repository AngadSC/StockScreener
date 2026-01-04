from typing import Optional, Dict, Any, List
import pandas as pd
from datetime import datetime, timedelta, date
import yfinance as yf
from app.config import settings


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
# YFINANCE DATA FETCHERS (NEW)
# ====================================

def prepare_backtest_data(
    ticker: str,
    start_date: str,
    end_date: str,
    include_splits: bool = True,
    include_dividends: bool = True,
    quiet: bool = False
) -> Optional[pd.DataFrame]:
    """
    Fetch extended historical data for backtesting using yfinance.
    
    Args:
        ticker: Stock symbol
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        include_splits: Include stock splits
        include_dividends: Include dividend data
        quiet: Suppress print statements
    
    Returns:
        DataFrame with OHLCV data and optional splits/dividends
    """
    try:
        if not quiet:
            print(f"📊 Fetching backtest data for {ticker}...")
        
        stock = yf.Ticker(ticker)
        
        # Fetch historical data
        df = stock.history(
            start=start_date,
            end=end_date,
            auto_adjust=True,  # Use adjusted prices
            actions=include_splits or include_dividends  # Include corporate actions
        )
        
        if df.empty:
            if not quiet:
                print(f"✗ No data for {ticker}")
            return None
        
        # Ensure Date is in the index
        if 'Date' in df.columns:
            df = df.set_index('Date')
        
        if not quiet:
            print(f"✓ Fetched {len(df)} records for {ticker}")
        
        return df
        
    except Exception as e:
        if not quiet:
            print(f"✗ Error fetching backtest data for {ticker}: {e}")
        return None


def fetch_price_history(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
    quiet: bool = False
) -> Optional[pd.DataFrame]:
    """
    Fetch price history using yfinance.
    
    Args:
        ticker: Stock symbol
        period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
        quiet: Suppress print statements
    
    Returns:
        DataFrame with OHLCV data
    """
    try:
        if not quiet:
            print(f"📊 Fetching {period} of {interval} data for {ticker}...")
        
        stock = yf.Ticker(ticker)
        
        df = stock.history(
            period=period,
            interval=interval,
            auto_adjust=True
        )
        
        if df.empty:
            if not quiet:
                print(f"✗ No data for {ticker}")
            return None
        
        # Ensure Date is in the index
        if 'Date' in df.columns:
            df = df.set_index('Date')
        
        if not quiet:
            print(f"✓ Fetched {len(df)} records for {ticker}")
        
        return df
        
    except Exception as e:
        if not quiet:
            print(f"✗ Error fetching price history for {ticker}: {e}")
        return None


def fetch_stock_fundamentals(ticker: str, quiet: bool = False) -> Optional[Dict[str, Any]]:
    """
    Fetch fundamental data for a single stock using yfinance.
    
    NOTE: For production, use YahooQueryProvider for batch fundamentals!
    This is a fallback for single-ticker requests.
    
    Args:
        ticker: Stock symbol
        quiet: Suppress print statements
    
    Returns:
        Dict with fundamental data
    """
    try:
        if not quiet:
            print(f"📊 Fetching fundamentals for {ticker}...")
        
        stock = yf.Ticker(ticker)
        info = stock.info
        
        if not info or len(info) < 5:
            if not quiet:
                print(f"✗ No fundamental data for {ticker}")
            return None
        
        # Extract fundamentals (same structure as yahooquery provider)
        fundamentals = {
            'ticker': ticker,
            'name': info.get('longName') or info.get('shortName'),
            'exchange': info.get('exchange'),
            
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
        }
        
        if not quiet:
            print(f"✓ Fetched fundamentals for {ticker}")
        
        return fundamentals
        
    except Exception as e:
        if not quiet:
            print(f"✗ Error fetching fundamentals for {ticker}: {e}")
        return None


# ====================================
# TECHNICAL INDICATORS
# ====================================

def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add technical indicators to price DataFrame.
    
    Adds:
    - Moving Averages (SMA 20/50/200, EMA 12/26)
    - MACD and Signal
    - RSI (14)
    - Bollinger Bands
    - Volume SMA
    """
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
