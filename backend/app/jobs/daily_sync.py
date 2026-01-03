from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database.connection import SessionLocal
from app.database.models import Ticker, DailyOHLCV, StockSplit, Dividend
from app.providers.factory import ProviderFactory
from app.utils.market_calendar import is_trading_day, get_last_trading_day
from app.services.cache import cache_service
from datetime import datetime, timedelta
import pandas as pd

# ============================================
# DAILY DELTA SYNC JOB
# Updates OHLCV data for all initialized stocks
# Only fetches NEW days since last update
# ============================================

def daily_delta_sync():
    """
    Nightly job: Update OHLCV for all stocks in database
    Only fetches days missing since last DB date (delta sync)
    """
    db = SessionLocal()
    start_time = datetime.now()
    
    stats = {
        'total_tickers': 0,
        'updated': 0,
        'failed': 0,
        'no_update_needed': 0,
        'records_inserted': 0
    }
    
    try:
        print("\n" + "="*70)
        print(f"🔄 DAILY DELTA SYNC STARTED")
        print(f"   Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70 + "\n")
        
        # Check if today is a trading day
        today = datetime.now().date()
        if not is_trading_day(today):
            print("📅 Market closed today (weekend/holiday), skipping sync")
            return stats
        
        # Get the last trading day
        last_trading_day = get_last_trading_day()
        
        # Find the last date we have in DB (global)
        last_db_date = db.query(func.max(DailyOHLCV.date)).scalar()
        
        if not last_db_date:
            print("⚠️  No data in database yet. Run bulk population first.")
            return stats
        
        print(f"📊 Database state:")
        print(f"   Last DB date: {last_db_date}")
        print(f"   Last trading day: {last_trading_day}")
        
        # Check if we need to update
        if last_db_date >= last_trading_day:
            print(f"✓ Database is up to date, no sync needed\n")
            return stats
        
        # Calculate delta (dates to fetch)
        delta_start = last_db_date + timedelta(days=1)
        delta_end = last_trading_day
        
        print(f"   Delta range: {delta_start} to {delta_end}")
        
        # Get all tickers that exist in DB
        tickers = db.query(Ticker.symbol).all()
        ticker_list = [t[0] for t in tickers]
        stats['total_tickers'] = len(ticker_list)
        
        print(f"   Tickers to update: {stats['total_tickers']}\n")
        
        if not ticker_list:
            print("⚠️  No tickers in database")
            return stats
        
        # Get provider
        provider = ProviderFactory.get_realtime_provider()
        print(f"✓ Using provider: {provider.name}\n")
        
        # Batch tickers
        batch_size = 100
        batches = [ticker_list[i:i+batch_size] for i in range(0, len(ticker_list), batch_size)]
        
        print(f"📦 Processing {len(batches)} batches...")
        
        # Process each batch
        for batch_num, batch in enumerate(batches, 1):
            try:
                print(f"   Batch {batch_num}/{len(batches)} ({len(batch)} tickers)...", end=" ")
                
                # Fetch delta data
                df = provider.get_batch_historical_prices(
                    tickers=batch,
                    start_date=delta_start,
                    end_date=delta_end,
                    is_bulk_load=False  # Use shorter jitter for daily updates
                )
                
                if df is None or df.empty:
                    print("✗ No data")
                    stats['failed'] += len(batch)
                    continue
                
                # Insert data
                records = _upsert_delta_data(db, df)
                stats['records_inserted'] += records
                stats['updated'] += len(batch)
                
                print(f"✓ {records} records")
                
            except Exception as e:
                print(f"✗ Failed: {e}")
                stats['failed'] += len(batch)
                continue
        
        # Clear caches
        print("\n🗑️  Clearing price caches...")
        cache_service.clear_pattern("prices:*")
        cache_service.clear_pattern("stock:*")
        
        # Final report
        end_time = datetime.now()
        duration = (end_time - start_time).seconds / 60
        
        print("\n" + "="*70)
        print(f"✅ DAILY DELTA SYNC COMPLETE")
        print(f"   Duration: {duration:.1f} minutes")
        print(f"   Updated: {stats['updated']}/{stats['total_tickers']}")
        print(f"   Failed: {stats['failed']}")
        print(f"   Records inserted: {stats['records_inserted']}")
        print("="*70 + "\n")
        
        return stats
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        db.rollback()
        return stats
        
    finally:
        db.close()


def _upsert_delta_data(db: Session, df: pd.DataFrame) -> int:
    """
    Upsert delta data into database
    Uses INSERT ... ON CONFLICT DO UPDATE for idempotency
    """
    records_inserted = 0
    
    for _, row in df.iterrows():
        # Get ticker_id
        ticker_obj = db.query(Ticker).filter(Ticker.symbol == row['ticker']).first()
        if not ticker_obj:
            continue
        
        # Upsert OHLCV
        ohlcv = DailyOHLCV(
            ticker_id=ticker_obj.id,
            date=row['date'],
            open=float(row['Open']),
            high=float(row['High']),
            low=float(row['Low']),
            close=float(row['Close']),
            volume=int(row['Volume'])
        )
        db.merge(ohlcv)
        records_inserted += 1
    
    # Handle dividends/splits if present
    if hasattr(df, '_dividends') and not df._dividends.empty:
        for _, row in df._dividends.iterrows():
            ticker_obj = db.query(Ticker).filter(Ticker.symbol == row['ticker']).first()
            if ticker_obj:
                div = Dividend(
                    ticker_id=ticker_obj.id,
                    date=row['date'],
                    amount=float(row['Dividends'])
                )
                db.merge(div)
    
    if hasattr(df, '_splits') and not df._splits.empty:
        for _, row in df._splits.iterrows():
            ticker_obj = db.query(Ticker).filter(Ticker.symbol == row['ticker']).first()
            if ticker_obj:
                split = StockSplit(
                    ticker_id=ticker_obj.id,
                    date=row['date'],
                    ratio=float(row['Stock Splits'])
                )
                db.merge(split)
    
    db.commit()
    return records_inserted
