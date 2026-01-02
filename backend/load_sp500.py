"""
Quick test: Load only S&P 500 stocks (~500 stocks, ~17 minutes)
"""

from app.database.connection import SessionLocal
from app.database.models import Stock
from app.utils.data_fetcher import get_sp500_tickers, fetch_stock_fundamentals
from datetime import datetime

def load_sp500():
    """Load S&P 500 stocks into database"""
    db = SessionLocal()
    
    try:
        print("\n" + "="*60)
        print("📊 LOADING S&P 500 STOCKS")
        print("="*60 + "\n")
        
        # Get S&P 500 tickers
        tickers = get_sp500_tickers()
        total = len(tickers)
        
        if not tickers:
            print("❌ Failed to fetch S&P 500 tickers")
            return
        
        print(f"📋 Processing {total} S&P 500 stocks...\n")
        
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
                    print(f"⚠️  {ticker}: No data available")
                    continue
                
                # Check if stock exists
                stock = db.query(Stock).filter(Stock.ticker == ticker).first()
                
                if stock:
                    # Update existing stock
                    for key, value in fundamentals.items():
                        if key != "ticker" and hasattr(stock, key):
                            setattr(stock, key, value)
                    stats['updated'] += 1
                    print(f"✓ {ticker}: Updated")
                else:
                    # Create new stock
                    stock = Stock(**fundamentals)
                    db.add(stock)
                    stats['created'] += 1
                    print(f"✓ {ticker}: Created")
                
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
                print(f"✗ {ticker}: Error - {e}")
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
        print("✅ S&P 500 LOADING COMPLETE")
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
    print("\n🚀 Starting S&P 500 stock loader...\n")
    load_sp500()
    print("✨ Done!\n")
