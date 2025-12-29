from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.database.models import Stock, StockPrice
from app.utils.data_fetcher import (
    fetch_stock_fundamentals,
    get_all_us_tickers,
    fetch_price_history
)
from app.services.cache import cache_service
from datetime import datetime, timedelta
import time


scheduler = AsyncIOScheduler()

def update_all_stocks_nightly():
    """
    Nightly job: Update fundamentals for all US stocks.
    
    - Runs at 9 PM ET (after market close)
    - Fetches ~8,000 US stocks
    - Takes ~4.5 hours (rate limited to 30/min)
    - Updates existing stocks, adds new ones
    """
    db = SessionLocal()
    start_time = datetime.now()
    
    try:
        print("\n" + "="*70)
        print(f" NIGHTLY STOCK UPDATE STARTED")
        print(f"   Time: {start_time.strftime('%Y-%m-%d %H:%M:%S ET')}")
        print("="*70 + "\n")
        
        # Get all US stock tickers
        tickers = get_all_us_tickers()
        total = len(tickers)
        
        print(f"📋 Processing {total} tickers...\n")
        
        # Track statistics
        stats = {
            'updated': 0,
            'created': 0,
            'failed': 0,
            'no_data': 0
        }
        
        for i, ticker in enumerate(tickers, 1):
            try:
                # Fetch fundamentals (automatically rate limited)
                fundamentals = fetch_stock_fundamentals(ticker, quiet=True)
                
                if not fundamentals:
                    stats['no_data'] += 1
                    continue
                
                # Check if stock exists
                stock = db.query(Stock).filter(Stock.ticker == ticker).first()
                
                if stock:
                    # Update existing stock
                    for key, value in fundamentals.items():
                        if key != "ticker" and hasattr(stock, key):
                            setattr(stock, key, value)
                    stats['updated'] += 1
                else:
                    # Create new stock
                    stock = Stock(**fundamentals)
                    db.add(stock)
                    stats['created'] += 1
                
                # Commit every 10 stocks (batch commits for performance)
                if i % 10 == 0:
                    db.commit()
                
                # Progress report every 100 stocks
                if i % 100 == 0:
                    elapsed = (datetime.now() - start_time).seconds / 60
                    rate = i / elapsed if elapsed > 0 else 0
                    eta = (total - i) / rate if rate > 0 else 0
                    
                    print(f"📊 Progress: {i}/{total} ({i/total*100:.1f}%)")
                    print(f"   ✓ Updated: {stats['updated']} | Created: {stats['created']}")
                    print(f"   ✗ Failed: {stats['failed']} | No data: {stats['no_data']}")
                    print(f"   ⏱  Rate: {rate:.1f}/min | ETA: {eta:.0f} min\n")
                    
            except Exception as e:
                print(f"✗ Error processing {ticker}: {e}")
                stats['failed'] += 1
                db.rollback()
                continue
        
        # Final commit
        db.commit()
        
        # Clear all stock-related caches (data is fresh now)
        print("\n🗑️  Clearing caches...")
        cache_service.clear_pattern("stock:*")
        cache_service.clear_pattern("screener:*")
        cache_service.clear_pattern("prices:*")
        
        # Final report
        end_time = datetime.now()
        duration = (end_time - start_time).seconds / 60
        success_rate = ((stats['updated'] + stats['created']) / total * 100) if total > 0 else 0
        
        print("\n" + "="*70)
        print(f"✅ NIGHTLY UPDATE COMPLETE")
        print(f"   Duration: {duration:.1f} minutes ({duration/60:.1f} hours)")
        print(f"   Updated: {stats['updated']}")
        print(f"   Created: {stats['created']}")
        print(f"   Failed: {stats['failed']}")
        print(f"   No data: {stats['no_data']}")
        print(f"   Success rate: {success_rate:.1f}%")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR in nightly job: {e}")
        db.rollback()
        
    finally:
        db.close()

def update_price_history():
    """
    Optional: Update 1 year of price history for all stocks.
    
    Run this less frequently (weekly?) as it takes longer.
    Only stores 1 year to save database space.
    """
    db = SessionLocal()
    
    try:
        print("\n📈 Updating price history...")
        
        # Get all tickers from database
        stocks = db.query(Stock.ticker).all()
        tickers = [s.ticker for s in stocks]
        
        print(f"Fetching prices for {len(tickers)} stocks...")
        
        for i, ticker in enumerate(tickers, 1):
            try:
                # Fetch 1 year of daily prices
                df = fetch_price_history(ticker, period="1y", quiet=True)
                
                if df is None or df.empty:
                    continue
                
                # Delete old prices for this ticker
                db.query(StockPrice).filter(StockPrice.ticker == ticker).delete()
                
                # Insert new prices
                for date, row in df.iterrows():
                    price = StockPrice(
                        ticker=ticker,
                        date=date.date(),
                        open=row['Open'],
                        high=row['High'],
                        low=row['Low'],
                        close=row['Close'],
                        volume=row['Volume']
                    )
                    db.add(price)
                
                # Commit every 10 stocks
                if i % 10 == 0:
                    db.commit()
                    print(f"  Progress: {i}/{len(tickers)}")
                    
            except Exception as e:
                print(f"✗ Error fetching prices for {ticker}: {e}")
                db.rollback()
                continue
        
        db.commit()
        print("✓ Price history update complete")
        
    except Exception as e:
        print(f"❌ Error updating price history: {e}")
        db.rollback()
        
    finally:
        db.close()

@scheduler.scheduled_job('cron', hour=21, minute=0, timezone='America/New_York')
def scheduled_nightly_update():
    """Runs at 9:00 PM ET every night"""
    print("⏰ Triggering nightly stock update...")
    update_all_stocks_nightly()


# we can run a job on sunday as well so we can get the data for monday
@scheduler.scheduled_job('cron', day_of_week='sun', hour=2, minute=0, timezone='America/New_York')
def scheduled_price_update():
    """Runs Sunday at 2:00 AM ET"""
    print("⏰ Triggering weekly price history update...")
    update_price_history()


def start_scheduler():
    """Start the APScheduler"""
    scheduler.start()
    print("✓ Scheduler initialized")
    print("   Nightly fundamentals update: 9:00 PM ET daily")
    print("   Weekly price history update: 2:00 AM ET Sunday")
