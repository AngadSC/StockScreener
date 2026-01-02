"""
Quick test: Load first 500 US stocks from NASDAQ (~500 stocks, ~17 minutes)
Uses NASDAQ FTP instead of Wikipedia
"""

from app.database.connection import SessionLocal
from app.database.models import Stock
from app.utils.data_fetcher import get_all_us_tickers, fetch_stock_fundamentals
from datetime import datetime

def load_sp500():
    """Load first 500 US stocks from NASDAQ into database"""
    db = SessionLocal()
    
    try:
        print("\n" + "="*60)
        print("📊 LOADING TOP 500 US STOCKS (FROM NASDAQ)")
        print("="*60 + "\n")
        
        # Get all US tickers from NASDAQ FTP
        print("Fetching ticker list from NASDAQ FTP...")
        all_tickers = get_all_us_tickers()
        
        if not all_tickers:
            print("❌ Failed to fetch tickers from NASDAQ")
            return
        
        # Take first 500
        tickers = all_tickers[:500]
        total = len(tickers)
        
        print(f"✓ Fetched {len(all_tickers)} total US tickers")
        print(f"📋 Processing first {total} stocks...\n")
        
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
                # Fetch fundamentals (automatically rate limited)
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
                
                # Commit every 10 stocks
                if i % 10 == 0:
                    db.commit()
                    elapsed = (datetime.now() - start_time).seconds / 60
                    rate = i / elapsed if elapsed > 0 else 0
                    eta = (total - i) / rate if rate > 0 else 0
                    
                    print(f"\n📊 Progress: {i}/{total} ({i/total*100:.1f}%)")
                    print(f"   ✓ Created: {stats['created']} | Updated: {stats['updated']}")
                    print(f"   ✗ Failed: {stats['failed']} | No data: {stats['no_data']}")
                    print(f"   ⏱  Rate: {rate:.1f}/min | ETA: {eta:.0f} min\n")
                    
            except Exception as e:
                print(f"✗ [{i}/{total}] {ticker}: Error - {e}")
                stats['failed'] += 1
                db.rollback()
                continue
        
        # Final commit
        db.commit()
        
        # Final report
        end_time = datetime.now()
        duration = (end_time - start_time).seconds / 60
        success_rate = ((stats['created'] + stats['updated']) / total * 100) if total > 0 else 0
        
        print("\n" + "="*60)
        print("✅ STOCK LOADING COMPLETE")
        print("="*60)
        print(f"   Duration: {duration:.1f} minutes")
        print(f"   Created: {stats['created']}")
        print(f"   Updated: {stats['updated']}")
        print(f"   Failed: {stats['failed']}")
        print(f"   No data: {stats['no_data']}")
        print(f"   Success rate: {success_rate:.1f}%")
        print("="*60 + "\n")
        
        # Show final count
        final_count = db.query(Stock).count()
        print(f"📊 Total stocks in database: {final_count}\n")
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        db.rollback()
        
    finally:
        db.close()

if __name__ == "__main__":
    print("\n🚀 Starting stock loader (NASDAQ source)...\n")
    load_sp500()
    print("✨ Done!\n")