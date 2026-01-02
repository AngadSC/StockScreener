"""
Optimized Script: Load actual S&P 500 stocks into the database.
Uses Wikipedia source for accurate S&P 500 tickers and follows rate limits.
"""

from app.database.connection import SessionLocal
from app.database.models import Stock
from app.utils.data_fetcher import get_sp500_tickers, fetch_stock_fundamentals
from datetime import datetime
import time

def load_sp500():
    """Load actual S&P 500 stocks from Wikipedia into database"""
    db = SessionLocal()
    
    try:
        print("\n" + "="*60)
        print("📊 LOADING S&P 500 CONSTITUENTS")
        print("="*60 + "\n")
        
        # FIX: Get the actual S&P 500 list instead of the first 500 NASDAQ tickers
        print("Fetching S&P 500 ticker list from Wikipedia...")
        tickers = get_sp500_tickers()
        
        if not tickers:
            print("❌ Failed to fetch S&P 500 tickers")
            return
        
        total = len(tickers)
        print(f"✓ Found {total} S&P 500 tickers")
        print(f"📋 Processing stocks...\n")
        
        # Track statistics
        stats = {
            'updated': 0,
            'created': 0,
            'failed': 0,
            'no_data': 0
        }
        
        start_time = datetime.now()
        
        for i, ticker in enumerate(tickers, 1):
            try:
                # Fetch fundamentals (automatically rate limited via decorator)
                fundamentals = fetch_stock_fundamentals(ticker, quiet=True)
                
                if not fundamentals:
                    stats['no_data'] += 1
                    print(f"⚠️  [{i}/{total}] {ticker}: No data available")
                    continue
                
                # Check if stock exists
                stock = db.query(Stock).filter(Stock.ticker == ticker).first()
                
                if stock:
                    # Update existing stock
                    for key, value in fundamentals.items():
                        if key != "ticker" and hasattr(stock, key):
                            setattr(stock, key, value)
                    stats['updated'] += 1
                    print(f"✓ [{i}/{total}] {ticker}: Updated - {fundamentals.get('name', 'N/A')}")
                else:
                    # Create new stock
                    stock = Stock(**fundamentals)
                    db.add(stock)
                    stats['created'] += 1
                    print(f"✓ [{i}/{total}] {ticker}: Created - {fundamentals.get('name', 'N/A')}")
                
                # Commit in batches for performance and safety
                if i % 10 == 0:
                    db.commit()
                    elapsed = (datetime.now() - start_time).seconds / 60
                    rate = i / elapsed if elapsed > 0 else 0
                    eta = (total - i) / rate if rate > 0 else 0
                    
                    print(f"\n📊 Progress: {i}/{total} ({i/total*100:.1f}%)")
                    print(f"   ✓ Created: {stats['created']} | Updated: {stats['updated']}")
                    print(f"   ⏱  Rate: {rate:.1f}/min | ETA: {eta:.0f} min\n")
                    
            except Exception as e:
                print(f"✗ [{i}/{total}] {ticker}: Error - {e}")
                stats['failed'] += 1
                db.rollback()
                # Stop if we hit a persistent 429 during the loop
                if "429" in str(e):
                    print("🛑 Rate limit exceeded. Stopping to avoid IP ban.")
                    break
                continue
        
        # Final commit
        db.commit()
        
        # Final report
        end_time = datetime.now()
        duration = (end_time - start_time).seconds / 60
        success_rate = ((stats['created'] + stats['updated']) / i * 100) if i > 0 else 0
        
        print("\n" + "="*60)
        print("✅ S&P 500 LOADING COMPLETE")
        print("="*60)
        print(f"   Duration: {duration:.1f} minutes")
        print(f"   Created: {stats['created']}")
        print(f"   Updated: {stats['updated']}")
        print(f"   Failed: {stats['failed']}")
        print(f"   Success rate: {success_rate:.1f}%")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        db.rollback()
        
    finally:
        db.close()

if __name__ == "__main__":
    print("\n🚀 Starting stock loader...")
    # Add a small initial delay if you just ran into a 429 error
    load_sp500()
    print("✨ Done!\n")