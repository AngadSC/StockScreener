"""
Test 3: yahooquery batch fundamentals
Tests: Batch fundamentals fetch, module extraction
"""

from yahooquery import Ticker

print("\n" + "="*70)
print("TEST 3: yahooquery Batch Fundamentals")
print("="*70 + "\n")

# Test 3.1: Single ticker
print("3.1 Testing single ticker fundamentals (AAPL)...")
try:
    ticker = Ticker('AAPL')
    modules = ticker.get_modules([
        'summaryDetail',
        'defaultKeyStatistics',
        'financialData',
        'price'
    ])
    
    if 'AAPL' not in modules:
        print(f"✗ AAPL not in response: {modules.keys()}")
        exit(1)
    
    data = modules['AAPL']
    
    if isinstance(data, str) or 'error' in str(data).lower():
        print(f"✗ Error in response: {data}")
        exit(1)
    
    print(f"✓ Fetched fundamentals for AAPL")
    print(f"   Modules: {list(data.keys())}")
    
    # Extract sample values
    summary = data.get('summaryDetail', {})
    stats = data.get('defaultKeyStatistics', {})
    financials = data.get('financialData', {})
    
    print(f"\n   Sample data:")
    print(f"   P/E Ratio: {summary.get('trailingPE')}")
    print(f"   Market Cap: {summary.get('marketCap')}")
    print(f"   Debt/Equity: {financials.get('debtToEquity')}")
    print(f"   ROE: {financials.get('returnOnEquity')}")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 3.2: Batch tickers (the key advantage)
print("\n3.2 Testing batch fundamentals (10 tickers)...")
try:
    tickers_list = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'BRK-B', 'UNH', 'JNJ']
    
    tickers = Ticker(tickers_list)
    modules = tickers.get_modules([
        'summaryDetail',
        'defaultKeyStatistics',
        'financialData',
        'price'
    ])
    
    print(f"✓ Fetched fundamentals for batch")
    print(f"   Requested: {len(tickers_list)} tickers")
    print(f"   Received: {len(modules)} responses")
    
    # Check success rate
    success_count = 0
    for ticker_symbol in tickers_list:
        if ticker_symbol in modules:
            data = modules[ticker_symbol]
            if not isinstance(data, str) and 'error' not in str(data).lower():
                success_count += 1
                
                # Extract P/E as sample
                summary = data.get('summaryDetail', {})
                pe = summary.get('trailingPE')
                print(f"   {ticker_symbol}: P/E={pe}")
    
    print(f"\n✓ Success rate: {success_count}/{len(tickers_list)} ({success_count/len(tickers_list)*100:.1f}%)")
    
    if success_count < len(tickers_list) * 0.8:
        print(f"⚠️  Warning: Low success rate")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 3.3: Large batch (50 tickers - production size)
print("\n3.3 Testing production-size batch (50 tickers)...")
try:
    large_batch = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'UNH', 'JNJ',
        'V', 'WMT', 'XOM', 'LLY', 'JPM', 'PG', 'MA', 'AVGO', 'HD', 'CVX',
        'MRK', 'ABBV', 'COST', 'PEP', 'ADBE', 'KO', 'TMO', 'MCD', 'CSCO', 'ACN',
        'CRM', 'ABT', 'NFLX', 'LIN', 'NKE', 'DHR', 'DIS', 'AMD', 'VZ', 'TXN',
        'CMCSA', 'PM', 'ORCL', 'NEE', 'INTC', 'WFC', 'COP', 'UPS', 'RTX', 'BMY'
    ]
    
    import time
    start_time = time.time()
    
    tickers = Ticker(large_batch)
    modules = tickers.get_modules([
        'summaryDetail',
        'defaultKeyStatistics',
        'financialData',
        'price'
    ])
    
    elapsed = time.time() - start_time
    
    print(f"✓ Fetched {len(modules)} responses in {elapsed:.1f} seconds")
    print(f"   Average: {elapsed/len(large_batch):.2f} sec/ticker")
    
    # Count successes
    success_count = sum(1 for t in large_batch if t in modules and not isinstance(modules[t], str))
    print(f"   Success rate: {success_count}/{len(large_batch)} ({success_count/len(large_batch)*100:.1f}%)")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "="*70)
print("✅ TEST 3 PASSED - yahooquery works!")
print("="*70 + "\n")
