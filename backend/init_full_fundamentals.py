from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.database.connection import SessionLocal
from app.database.models import Ticker, StockFundamental
from app.jobs.fundamentals_updater import _update_ticker_info, _upsert_fundamentals
from app.providers.factory import ProviderFactory
from app.services.cache import cache_service
from datetime import datetime, timedelta

def initialize_remaining_fundamentals():
    """
    SMART INITIALIZATION: 
    Only fetches fundamentals for stocks that:
    1. Have NEVER been updated (missing from stock_fundamentals table)
    2. OR haven't been updated in the last 24 hours
    
    Skips the 780 tickers you already processed.
    """
    db = SessionLocal()
    start_time = datetime.now()
    
    stats = {
        'total_needed': 0,
        'updated': 0,
        'failed': 0,
        'skipped': 0
    }
    
    try:
        print("\n" + "="*70)
        print(f"🚀 INITIALIZING REMAINING FUNDAMENTALS (SMART RESUME)")
        print(f"   Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70 + "\n")
        
        # Define "Fresh" as updated within the last 24 hours
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        # 1. Get IDs of tickers that are already fresh
        fresh_ticker_ids = db.query(StockFundamental.ticker_id).filter(
            StockFundamental.last_updated >= cutoff_time
        ).all()
        fresh_ids_set = {t[0] for t in fresh_ticker_ids}
        
        stats['skipped'] = len(fresh_ids_set)
        print(f"⏭️  Skipping {stats['skipped']} tickers (already updated in last 24h)")
        
        # 2. Get tickers that NEED updating (Not in fresh set)
        tickers_to_update = db.query(Ticker).filter(
            Ticker.id.not_in(fresh_ids_set)
        ).order_by(Ticker.id).all()
        
        stats['total_needed'] = len(tickers_to_update)
        
        if not tickers_to_update:
            print("✅ All tickers are up to date! Nothing to do.")
            return
            
        print(f"📋 Found {len(tickers_to_update)} remaining tickers to process")
        
        # 3. Get provider
        provider = ProviderFactory.get_fundamentals_provider()
        print(f"✓ Using provider: {provider.name}\n")
        
        # 4. Batch Process
        batch_size = 50
        ticker_symbols = [t.symbol for t in tickers_to_update]
        batches = [ticker_symbols[i:i+batch_size] for i in range(0, len(ticker_symbols), batch_size)]
        
        print(f"📦 Processing {len(batches)} batches...")
        
        for batch_num, batch in enumerate(batches, 1):
            try:
                print(f"   Batch {batch_num}/{len(batches)} ({len(batch)} tickers)...", end=" ")
                
                # Fetch data
                fundamentals_data = provider.get_batch_fundamentals(batch)
                
                if not fundamentals_data:
                    print("✗ No data returned (skipping batch)")
                    stats['failed'] += len(batch)
                    continue
                
                # Update DB
                updated_count = 0
                for ticker_symbol, fund_data in fundamentals_data.items():
                    ticker_obj = db.query(Ticker).filter(Ticker.symbol == ticker_symbol).first()
                    if not ticker_obj:
                        continue
                    
                    # Use existing helper functions
                    _update_ticker_info(db, ticker_obj, fund_data)
                    _upsert_fundamentals(db, ticker_obj.id, fund_data)
                    
                    updated_count += 1
                
                stats['updated'] += updated_count
                print(f"✓ {updated_count} updated")
                
            except Exception as e:
                print(f"✗ Failed: {e}")
                stats['failed'] += len(batch)
                db.rollback()
                continue

        # 5. Clear Cache
        print("\n🗑️  Clearing screener caches...")
        cache_service.clear_pattern("screener:*")
        
        end_time = datetime.now()
        duration = (end_time - start_time).seconds / 60
        
        print("\n" + "="*70)
        print(f"✅ SMART INITIALIZATION COMPLETE")
        print(f"   Duration: {duration:.1f} minutes")
        print(f"   Total Skipped: {stats['skipped']}")
        print(f"   Newly Updated: {stats['updated']}/{stats['total_needed']}")
        print("="*70 + "\n")

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    initialize_remaining_fundamentals()