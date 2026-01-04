"""
Data fetching utilities - Pure utility functions only.

This module contains provider-agnostic utility functions:
- Ticker list fetchers (S&P 500, NASDAQ, etc.)
- Technical indicator calculations
- Data post-processing utilities

For actual data fetching, use the provider system:
- app.providers.yfinance_provider.YFinanceProvider
- app.providers.yahooquery_provider.YahooQueryProvider
"""

from typing import List
import pandas as pd


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
    Fetch S&P 500 ticker list from Wikipedia.

    Returns:
        List of ~500 S&P 500 ticker symbols
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
    """
    Add technical indicators to price DataFrame.

    Adds:
    - Moving Averages (SMA 20/50/200, EMA 12/26)
    - MACD and Signal
    - RSI (14)
    - Bollinger Bands
    - Volume SMA

    Args:
        df: DataFrame with OHLCV data (must have 'Close' and 'Volume' columns)

    Returns:
        DataFrame with added indicator columns
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
