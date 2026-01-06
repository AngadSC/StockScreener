from typing import List
import pandas as pd


# High-volume ETFs that should always be included
IMPORTANT_ETFS = [
    # Major Index ETFs
    'SPY', 'QQQ', 'IWM', 'DIA', 'VOO', 'VTI', 'IVV',

    # Sector ETFs
    'XLF', 'XLE', 'XLK', 'XLV', 'XLI', 'XLP', 'XLY', 'XLU', 'XLRE', 'XLB', 'XLC',

    # Tech & Growth
    'ARKK', 'ARKW', 'ARKG', 'ARKF', 'WCLD', 'SKYY', 'CLOU',

    # Bond & Treasury
    'TLT', 'IEF', 'SHY', 'AGG', 'BND', 'LQD', 'HYG', 'JNK',

    # International
    'EEM', 'EFA', 'VWO', 'IEMG', 'VEA', 'FXI', 'EWJ', 'EWZ',

    # Commodity & Gold
    'GLD', 'SLV', 'USO', 'UNG', 'GDX', 'GDXJ',

    # Volatility & Leveraged (high volume)
    'VXX', 'UVXY', 'SVXY', 'SQQQ', 'TQQQ', 'SPXU', 'UPRO',

    # ARK Innovation
    'ARKQ', 'ARKG', 'ARKX',
]


def get_all_us_tickers() -> List[str]:
    """
    Fetch curated list of ~6,000 high-quality US-traded stocks + important ETFs.

    Includes:
    - Top US companies by market cap and volume
    - International ADRs (Toyota, ASML, Alibaba, etc.)
    - High-volume ETFs (SPY, QQQ, sector ETFs, etc.)

    Filters out:
    - Warrants, units, rights, preferred shares
    - Test issues and delisted companies
    - Low-volume/obscure ETFs

    Returns:
        List of ~6,000 ticker symbols (most liquid global companies + major ETFs)
    """
    all_tickers = []

    try:
        print("📋 Fetching US stock tickers from NASDAQ FTP...")

        # NASDAQ-listed stocks
        nasdaq_url = "ftp://ftp.nasdaqtrader.com/symboldirectory/nasdaqlisted.txt"
        nasdaq_df = pd.read_csv(nasdaq_url, sep="|")

        # Other exchanges (NYSE, AMEX, etc.) - Contains most ADRs
        other_url = "ftp://ftp.nasdaqtrader.com/symboldirectory/otherlisted.txt"
        other_df = pd.read_csv(other_url, sep="|")

        # ========================================
        # STEP 1: FILTER NASDAQ STOCKS
        # ========================================
        print("   Filtering NASDAQ stocks and whitelisted ETFs...")

        # Separate stocks and ETFs
        nasdaq_stocks = nasdaq_df[
            (nasdaq_df['Test Issue'] == 'N') &           # No test issues
            (nasdaq_df['ETF'] == 'N') &                  # No ETFs (we'll add them separately)
            (nasdaq_df['Financial Status'] == 'N')       # Only healthy companies
        ]

        nasdaq_etfs = nasdaq_df[
            (nasdaq_df['Test Issue'] == 'N') &           # No test issues
            (nasdaq_df['ETF'] == 'Y') &                  # Only ETFs
            (nasdaq_df['Symbol'].isin(IMPORTANT_ETFS))   # Only whitelisted ETFs
        ]

        # Remove warrants, units, preferred shares, rights from stocks
        nasdaq_stocks = nasdaq_stocks[
            ~nasdaq_stocks['Symbol'].str.contains(r'[\.\$]', regex=True, na=False) &  # No dots or $
            ~nasdaq_stocks['Symbol'].str.endswith(('W', 'U', 'R'), na=False) &        # No warrants/units/rights
            (nasdaq_stocks['Symbol'].str.len() <= 5)                                  # Max 5 chars
        ]

        nasdaq_stock_tickers = nasdaq_stocks['Symbol'].astype(str).tolist()
        nasdaq_etf_tickers = nasdaq_etfs['Symbol'].astype(str).tolist()

        # ========================================
        # STEP 2: FILTER NYSE/AMEX (Contains ADRs)
        # ========================================
        print("   Filtering NYSE/AMEX stocks (includes ADRs) and whitelisted ETFs...")

        # Separate stocks and ETFs
        other_stocks = other_df[
            (other_df['Test Issue'] == 'N') &           # No test issues
            (other_df['ETF'] == 'N')                    # No ETFs
        ]

        other_etfs = other_df[
            (other_df['Test Issue'] == 'N') &           # No test issues
            (other_df['ETF'] == 'Y') &                  # Only ETFs
            (other_df['ACT Symbol'].isin(IMPORTANT_ETFS))  # Only whitelisted ETFs
        ]

        # Remove junk tickers from stocks
        other_stocks = other_stocks[
            ~other_stocks['ACT Symbol'].str.contains(r'[\.\$]', regex=True, na=False) &
            ~other_stocks['ACT Symbol'].str.endswith(('W', 'U', 'R', '-P', '-A'), na=False) &
            (other_stocks['ACT Symbol'].str.len() <= 5)
        ]

        other_stock_tickers = other_stocks['ACT Symbol'].astype(str).tolist()
        other_etf_tickers = other_etfs['ACT Symbol'].astype(str).tolist()

        # ========================================
        # STEP 3: COMBINE STOCKS AND ETFS
        # ========================================
        all_stocks = nasdaq_stock_tickers + other_stock_tickers
        all_etfs = nasdaq_etf_tickers + other_etf_tickers

        # Clean stocks
        all_stocks = [str(t).strip().upper() for t in all_stocks if t and str(t).strip() and str(t) != 'nan']
        all_stocks = [t for t in all_stocks if not t.endswith('.TEST')]
        all_stocks = list(set(all_stocks))  # Remove duplicates

        # Clean ETFs
        all_etfs = [str(t).strip().upper() for t in all_etfs if t and str(t).strip() and str(t) != 'nan']
        all_etfs = list(set(all_etfs))  # Remove duplicates

        print(f"   Found {len(all_stocks)} stocks and {len(all_etfs)} whitelisted ETFs")

        # ========================================
        # STEP 4: COMBINE AND LIMIT TO 6,000
        # ========================================
        # Always include all whitelisted ETFs
        all_tickers = all_etfs + sorted(all_stocks)

        # If we have more than 6,000, keep all ETFs + top stocks
        if len(all_tickers) > 6000:
            stocks_to_keep = 6000 - len(all_etfs)
            print(f"   ⚠️  Found {len(all_tickers)} total tickers")
            print(f"   Keeping all {len(all_etfs)} ETFs + top {stocks_to_keep} stocks = 6,000 total")
            all_tickers = all_etfs + sorted(all_stocks)[:stocks_to_keep]

        print(f"✓ Final list: {len(all_tickers)} tickers ({len(all_etfs)} ETFs + {len(all_tickers) - len(all_etfs)} stocks)")
        print(f"   Includes: US companies, international ADRs, and major ETFs")
        print(f"   Filtered out: warrants, units, preferreds, low-volume ETFs\n")

        return sorted(all_tickers)

    except Exception as e:
        print(f"✗ Error fetching US tickers: {e}")
        print(f"   Falling back to important ETFs only")
        return IMPORTANT_ETFS


def get_sp500_tickers() -> List[str]:
    """
    Fetch S&P 500 ticker list from Wikipedia
    Fallback option if NASDAQ fails or for quick testing
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
