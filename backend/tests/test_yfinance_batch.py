"""
Test 2: Batch ticker download
Tests: Multi-ticker format, multi-index handling, session injection
This is CRITICAL - our code relies heavily on batch downloads
"""

import yfinance as yf
from curl_cffi import requests
import pandas as pd
from datetime import datetime, timedelta

print("\n" + "="*70)
print("TEST 2: Batch Ticker Download")
print("="*70 + "\n")

# Create session
session = requests.Session(impersonate="chrome110")

# Test 2.1: Small batch (3 tickers)
print("2.1 Testing small batch download (AAPL, MSFT, GOOGL)...")
try:
    tickers = ['AAPL', 'MSFT', 'GOOGL']
    
    data = yf.download(
        tickers=tickers,
        period="5d",
        session=session,
        threads=False,  # CRITICAL: Must be False for stealth
        auto_adjust=True,
        actions=True,
        progress=False,
        
    )
    
    if data.empty:
        print("✗ DataFrame is empty!")
        exit(1)
    
    print(f"✓ Downloaded data for {len(tickers)} tickers")
    print(f"   Shape: {data.shape}")
    print(f"   Index type: {type(data.index)}")
    print(f"   Columns: {data.columns}")
    print(f"\n   Sample data:")
    print(data.head(3))
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 2.2: Convert to long format (CRITICAL for our database insertion)
print("\n2.2 Testing multi-index to long format conversion...")
try:
    # Check if multi-index
    if isinstance(data.columns, pd.MultiIndex):
        print("✓ Detected multi-index format (expected)")
        
        # Convert to long format
        df = data.stack(level=1, future_stack=True).reset_index()
        df.columns = ['date', 'ticker', 'Open', 'High', 'Low', 'Close', 'Volume', 'Dividends', 'Stock Splits']
        
        print(f"✓ Converted to long format")
        print(f"   Shape: {df.shape}")
        print(f"   Columns: {list(df.columns)}")
        print(f"\n   Sample (first 5 rows):")
        print(df.head(5))
        
        # Verify we have all tickers
        unique_tickers = df['ticker'].unique()
        print(f"\n✓ Unique tickers in result: {list(unique_tickers)}")
        
        if set(unique_tickers) != set(tickers):
            print(f"⚠️  Warning: Expected {tickers}, got {list(unique_tickers)}")
        
        # Check for NaN values
        nan_count = df[['Open', 'High', 'Low', 'Close']].isna().sum().sum()
        print(f"   NaN values in OHLC: {nan_count}")
        
    else:
        print("⚠️  Warning: Not multi-index format (single ticker?)")
        print(f"   Columns: {data.columns}")
    
except Exception as e:
    print(f"✗ Conversion error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 2.3: Date range batch (what we use for delta sync)
print("\n2.3 Testing batch with date range (delta sync scenario)...")
try:
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    tickers = ['TSLA', 'NVDA', 'AMD']
    
    data = yf.download(
        tickers=tickers,
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
        session=session,
        threads=False,
        auto_adjust=True,
        actions=True,
        progress=False
    )
    
    print(f"✓ Downloaded {len(tickers)} tickers with date range")
    print(f"   Shape: {data.shape}")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 2.4: Large batch (100 tickers - what we use in production)
print("\n2.4 Testing production-size batch (100 tickers)...")
print("   This will take ~20 seconds with jitter...")

try:
    import time
    
    # Get 100 tickers (S&P 500 subset)
    large_batch = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'UNH', 'JNJ',
        'V', 'WMT', 'XOM', 'LLY', 'JPM', 'PG', 'MA', 'AVGO', 'HD', 'CVX',
        'MRK', 'ABBV', 'COST', 'PEP', 'ADBE', 'KO', 'TMO', 'MCD', 'CSCO', 'ACN',
        'CRM', 'ABT', 'NFLX', 'LIN', 'NKE', 'DHR', 'DIS', 'AMD', 'VZ', 'TXN',
        'CMCSA', 'PM', 'ORCL', 'NEE', 'INTC', 'WFC', 'COP', 'UPS', 'RTX', 'BMY',
        'IBM', 'HON', 'UNP', 'QCOM', 'BA', 'ELV', 'AMGN', 'LOW', 'SPGI', 'GE',
        'INTU', 'SBUX', 'CAT', 'DE', 'GS', 'MS', 'AXP', 'BLK', 'MDT', 'SCHW',
        'ADI', 'GILD', 'CVS', 'AMT', 'TJX', 'BKNG', 'LRCX', 'ADP', 'PLD', 'MMC',
        'C', 'SYK', 'REGN', 'VRTX', 'NOW', 'ISRG', 'MO', 'CB', 'ZTS', 'MDLZ',
        'CI', 'DUK', 'SO', 'PGR', 'BDX', 'EQIX', 'EOG', 'APH', 'ITW', 'CL'
    ]
    
    start_time = time.time()
    
    data = yf.download(
        tickers=large_batch,
        period="5d",
        session=session,
        threads=False,
        auto_adjust=True,
        progress=False
    )
    
    elapsed = time.time() - start_time
    
    print(f"✓ Downloaded {len(large_batch)} tickers")
    print(f"   Time: {elapsed:.1f} seconds")
    print(f"   Shape: {data.shape}")
    
    if data.empty:
        print("✗ No data returned!")
        exit(1)
    
    # Convert to long format
    df = data.stack(level=1, future_stack=True).reset_index()
    df.columns = ['date', 'ticker', 'Open', 'High', 'Low', 'Close', 'Volume', 'Dividends', 'Stock Splits']
    
    unique_tickers = len(df['ticker'].unique())
    print(f"✓ Got data for {unique_tickers}/{len(large_batch)} tickers")
    
    if unique_tickers < len(large_batch) * 0.9:
        print(f"⚠️  Warning: Only got {unique_tickers}/{len(large_batch)} tickers (90% threshold)")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "="*70)
print("✅ TEST 2 PASSED - Batch downloads work!")
print("="*70 + "\n")
