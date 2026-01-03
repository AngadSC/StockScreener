"""
Test 1: Basic yfinance 1.0.0 compatibility
Tests: Single ticker, session injection, history format
"""

import yfinance as yf
from curl_cffi import requests
import pandas as pd

print("\n" + "="*70)
print("TEST 1: Basic yfinance 1.0.0 + curl-cffi")
print("="*70 + "\n")

# Test 1.1: Create stealth session
print("1.1 Testing stealth session creation...")
try:
    session = requests.Session(impersonate="chrome110")
    print("✓ Session created with impersonate='chrome110'")
except Exception as e:
    print(f"✗ Failed with chrome110: {e}")
    print("   Trying generic 'chrome'...")
    try:
        session = requests.Session(impersonate="chrome")
        print("✓ Session created with impersonate='chrome'")
    except Exception as e2:
        print(f"✗ Failed: {e2}")
        exit(1)

# Test 1.2: Single ticker with session
print("\n1.2 Testing single ticker fetch (AAPL, 1 month)...")
try:
    ticker = yf.Ticker("AAPL", session=session)
    df = ticker.history(period="1mo", auto_adjust=True, actions=True)
    
    if df.empty:
        print("✗ DataFrame is empty!")
        exit(1)
    
    print(f"✓ Fetched {len(df)} days of data")
    print(f"   Columns: {list(df.columns)}")
    print(f"   Date range: {df.index[0]} to {df.index[-1]}")
    print(f"\n   Sample (first 3 rows):")
    print(df.head(3))
    
    # Check for OHLCV
    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        print(f"✗ Missing required columns: {missing}")
        exit(1)
    
    print(f"✓ All required OHLCV columns present")
    
    # Check for dividends/splits
    if 'Dividends' in df.columns:
        div_count = (df['Dividends'] > 0).sum()
        print(f"✓ Dividends column present ({div_count} dividend events)")
    
    if 'Stock Splits' in df.columns:
        split_count = (df['Stock Splits'] > 0).sum()
        print(f"✓ Stock Splits column present ({split_count} split events)")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 1.3: Date range fetch (critical for our use case)
print("\n1.3 Testing date range fetch (start/end parameters)...")
try:
    from datetime import datetime, timedelta
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    ticker = yf.Ticker("MSFT", session=session)
    df = ticker.history(
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
        auto_adjust=True,
        actions=True
    )
    
    print(f"✓ Date range fetch works ({len(df)} days)")
    print(f"   Requested: {start_date.date()} to {end_date.date()}")
    print(f"   Received: {df.index[0].date()} to {df.index[-1].date()}")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "="*70)
print("✅ TEST 1 PASSED - Basic yfinance 1.0.0 works!")
print("="*70 + "\n")
