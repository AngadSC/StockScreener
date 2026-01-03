from typing import List
import pandas as pd

def get_all_us_tickers() -> List[str]:
    """
    Fetch comprehensive list of all US exchange traded stocks.
    Sources: NASDAQ FTP (most reliable)
    
    Returns:
        List of ~7,000-8,000 ticker symbols
    """
    all_tickers = []
    
    try:
        print("📋 Fetching US stock tickers from NASDAQ FTP...")
        
        # NASDAQ-listed stocks
        nasdaq_url = "ftp://ftp.nasdaqtrader.com/symboldirectory/nasdaqlisted.txt"
        nasdaq_df = pd.read_csv(nasdaq_url, sep="|")
        nasdaq_df = nasdaq_df[nasdaq_df['Test Issue'] == 'N']  # Exclude test issues
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
        all_tickers = list(set(all_tickers))  # Remove duplicates
        
        print(f"✓ Fetched {len(all_tickers)} US stock tickers")
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
        
        print(f"✓ Fetched {len(tickers)} S&P 500 tickers")
        return tickers
    except Exception as e:
        print(f"✗ Error fetching S&P 500 list: {e}")
        return []
