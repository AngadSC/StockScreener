from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.database.models import Ticker, DailyOHLCV, StockSplit, Dividend, PopulationProgress, FailedTicker
from app.providers.factory import ProviderFactory
from app.utils.ticker_list import get_all_us_tickers
from app.utils.market_calendar import get_last_trading_day
from datetime import datetime, timedelta, date
from typing import List
import pandas as pd
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select


# ============================================
# BULK POPULATION JOB
# Populates all 8,000 US stocks with 5 years of historical data
# ============================================

def populate_all_stocks(resume: bool = True) -> dict:
    """
    One-time bulk population job: Fetch 5 years of OHLCV for all US stocks
    
    Args:
        resume: If True, resume from last checkpoint. If False, start fresh.
    
    Returns:
        Dict with statistics
    """
    db = SessionLocal()
    start_time = datetime.now()
    
    stats = {
        'total_tickers': 0,
        'total_batches': 0,
        'completed_batches': 0,
        'failed_batches': 0,
        'records_inserted': 0,
        'failed_tickers': 0,
        'start_time': start_time,
        'end_time': None,
        'duration_minutes': 0
    }
    
    try:
        print("\n" + "="*80)
        print(f"🚀 BULK POPULATION STARTED")
        print(f"   Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Resume mode: {resume}")
        print("="*80 + "\n")
        
        # Get all US tickers
        all_tickers = get_all_us_tickers()
        
        if not all_tickers:
            print("✗ Failed to fetch ticker list")
            return stats
        
        stats['total_tickers'] = len(all_tickers)
        
        # Batch into groups of 100
        batch_size = 100
        batches = [all_tickers[i:i+batch_size] for i in range(0, len(all_tickers), batch_size)]
        stats['total_batches'] = len(batches)
        
        print(f"📊 Configuration:")
        print(f"   Total tickers: {stats['total_tickers']}")
        print(f"   Batch size: {batch_size}")
        print(f"   Total batches: {stats['total_batches']}")
        print(f"   History period: 5 years")
        
        # Calculate date range
        end_date = get_last_trading_day()
        start_date = end_date - timedelta(days=365 * 5)
        
        print(f"   Date range: {start_date} to {end_date}")
        print(f"   Estimated time: {stats['total_batches'] * 20 / 60:.1f} hours")
        print()
        
        # Get provider
        provider = ProviderFactory.get_historical_provider()
        print(f"✓ Using provider: {provider.name}\n")
        
        # Check for existing progress (if resuming)
        completed_batch_numbers = set()
        if resume:
            completed = db.query(PopulationProgress).filter(
                PopulationProgress.status == 'completed'
            ).all()
            completed_batch_numbers = {p.batch_number for p in completed}
            
            if completed_batch_numbers:
                print(f"📌 Resuming from checkpoint: {len(completed_batch_numbers)} batches already completed\n")
        
        # Process each batch
        for batch_num, batch in enumerate(batches, 1):
            
            # Skip if already completed (resume mode)
            if batch_num in completed_batch_numbers:
                print(f"⏩ Batch {batch_num}/{stats['total_batches']} already completed, skipping...")
                stats['completed_batches'] += 1
                continue
            
            print(f"📦 Processing batch {batch_num}/{stats['total_batches']} ({len(batch)} tickers)...")
            
            # Create progress record
            progress = PopulationProgress(
                batch_number=batch_num,
                ticker_list=batch,
                start_time=datetime.now(),
                status='in_progress'
            )
            db.add(progress)
            db.commit()
            
            try:
                # Fetch batch data from provider
                df = provider.get_batch_historical_prices(
                    tickers=batch,
                    start_date=start_date,
                    end_date=end_date,
                    is_bulk_load=True  # Triggers longer jitter
                )
                
                if df is None or df.empty:
                    print(f"   ✗ No data returned for batch {batch_num}")
                    progress.status = 'failed'
                    progress.error_message = 'No data returned from provider'
                    progress.end_time = datetime.now()
                    db.commit()
                    stats['failed_batches'] += 1
                    
                    # Add all tickers to failed queue
                    for ticker in batch:
                        failed = FailedTicker(
                            ticker=ticker,
                            batch_number=batch_num,
                            error_message='No data in batch response'
                        )
                        db.add(failed)
                    db.commit()
                    stats['failed_tickers'] += len(batch)
                    continue
                
                # Insert data into database
                records_inserted = _insert_batch_data(db, df)
                
                # Mark batch as completed
                progress.status = 'completed'
                progress.end_time = datetime.now()
                progress.records_inserted = records_inserted
                db.commit()
                
                stats['completed_batches'] += 1
                stats['records_inserted'] += records_inserted
                
                elapsed = (datetime.now() - start_time).seconds / 60
                avg_time_per_batch = elapsed / stats['completed_batches'] if stats['completed_batches'] > 0 else 0
                remaining_batches = stats['total_batches'] - stats['completed_batches']
                eta_minutes = remaining_batches * avg_time_per_batch
                
                print(f"   ✓ Batch {batch_num} complete ({records_inserted} records)")
                print(f"   📈 Progress: {stats['completed_batches']}/{stats['total_batches']} ({stats['completed_batches']/stats['total_batches']*100:.1f}%)")
                print(f"   ⏱  Elapsed: {elapsed:.1f} min | ETA: {eta_minutes:.1f} min\n")
                
            except Exception as e:
                print(f"   ✗ Batch {batch_num} failed: {e}")
                
                # Mark batch as failed
                progress.status = 'failed'
                progress.error_message = str(e)
                progress.end_time = datetime.now()
                db.commit()
                
                stats['failed_batches'] += 1
                
                # Add tickers to retry queue
                for ticker in batch:
                    failed = FailedTicker(
                        ticker=ticker,
                        batch_number=batch_num,
                        error_message=str(e)
                    )
                    db.add(failed)
                db.commit()
                stats['failed_tickers'] += len(batch)
                
                continue
        
        # Final statistics
        end_time = datetime.now()
        stats['end_time'] = end_time
        stats['duration_minutes'] = (end_time - start_time).seconds / 60
        
        print("\n" + "="*80)
        print(f"✅ BULK POPULATION COMPLETE")
        print(f"   Duration: {stats['duration_minutes']:.1f} minutes ({stats['duration_minutes']/60:.2f} hours)")
        print(f"   Completed batches: {stats['completed_batches']}/{stats['total_batches']}")
        print(f"   Failed batches: {stats['failed_batches']}")
        print(f"   Records inserted: {stats['records_inserted']:,}")
        print(f"   Failed tickers: {stats['failed_tickers']}")
        print(f"   Success rate: {stats['completed_batches']/stats['total_batches']*100:.1f}%")
        print("="*80 + "\n")
        
        # Retry failed tickers if any
        if stats['failed_tickers'] > 0:
            print(f"⚠️  {stats['failed_tickers']} tickers failed during bulk load")
            print(f"   Run retry_failed_tickers() to attempt individual retries\n")
        
        return stats
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        return stats
        
    finally:
        db.close()


def _insert_batch_data(db: Session, df: pd.DataFrame) -> int:
    """
    Optimized Bulk Upsert for 8,000 stocks population.
    """
    # 1. Pre-fetch all tickers in the batch to get their IDs in one go
    ticker_symbols = df['ticker'].unique().tolist()
    ticker_objs = db.query(Ticker).filter(Ticker.symbol.in_(ticker_symbols)).all()
    ticker_map = {t.symbol: t.id for t in ticker_objs}
    
    # Identify missing tickers and create them
    missing_symbols = set(ticker_symbols) - set(ticker_map.keys())
    for symbol in missing_symbols:
        new_ticker = Ticker(symbol=symbol)
        db.add(new_ticker)
    
    if missing_symbols:
        db.flush() # Get IDs for new tickers
        # Refresh the map
        ticker_objs = db.query(Ticker).filter(Ticker.symbol.in_(ticker_symbols)).all()
        ticker_map = {t.symbol: t.id for t in ticker_objs}

    # 2. Prepare data for Bulk Upsert
    rows_to_upsert = []
    for _, row in df.iterrows():
        t_id = ticker_map.get(row['ticker'])
        if not t_id: continue
        
        rows_to_upsert.append({
            "ticker_id": t_id,
            "date": row['date'],
            "open": float(row['Open']) if pd.notna(row['Open']) else None,
            "high": float(row['High']) if pd.notna(row['High']) else None,
            "low": float(row['Low']) if pd.notna(row['Low']) else None,
            "close": float(row['Close']),
            "volume": int(row['Volume'])
        })

    # 3. Execute the PostgreSQL Bulk Upsert
    if rows_to_upsert:
        stmt = insert(DailyOHLCV).values(rows_to_upsert)
        stmt = stmt.on_conflict_do_update(
            index_elements=['ticker_id', 'date'],
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume
            }
        )
        db.execute(stmt)
        db.commit()
        
    return len(rows_to_upsert)


def retry_failed_tickers() -> dict:
    """
    Retry tickers that failed during bulk population
    Uses individual requests (slower but more reliable)
    """
    db = SessionLocal()
    
    stats = {
        'total_failed': 0,
        'retried': 0,
        'succeeded': 0,
        'permanent_failures': 0
    }
    
    try:
        # Get failed tickers
        failed = db.query(FailedTicker).filter(
            FailedTicker.status == 'pending',
            FailedTicker.retry_count < 3  # Max 3 retries
        ).all()
        
        stats['total_failed'] = len(failed)
        
        if not stats['total_failed']:
            print("✓ No failed tickers to retry")
            return stats
        
        print(f"\n🔄 Retrying {stats['total_failed']} failed tickers...\n")
        
        provider = ProviderFactory.get_historical_provider()
        
        end_date = get_last_trading_day()
        start_date = end_date - timedelta(days=365 * 5)
        
        for failed_ticker in failed:
            ticker_symbol = failed_ticker.ticker
            
            print(f"  Retrying {ticker_symbol} (attempt {failed_ticker.retry_count + 1}/3)...")
            
            failed_ticker.status = 'retrying'
            failed_ticker.retry_count += 1
            failed_ticker.last_attempt = datetime.now()
            db.commit()
            
            try:
                # Fetch single ticker
                df = provider.get_historical_prices(ticker_symbol, start_date, end_date)
                
                if df is None or df.empty:
                    print(f"    ✗ No data for {ticker_symbol}")
                    failed_ticker.status = 'pending'
                    failed_ticker.error_message = 'No data returned'
                    db.commit()
                    continue
                
                # Get or create ticker
                ticker_obj = db.query(Ticker).filter(Ticker.symbol == ticker_symbol).first()
                if not ticker_obj:
                    ticker_obj = Ticker(symbol=ticker_symbol)
                    db.add(ticker_obj)
                    db.flush()
                
                ticker_id = ticker_obj.id
                
                # Insert data
                for idx, row in df.iterrows():
                    ohlcv = DailyOHLCV(
                        ticker_id=ticker_id,
                        date=idx,
                        open=float(row['Open']),
                        high=float(row['High']),
                        low=float(row['Low']),
                        close=float(row['Close']),
                        volume=int(row['Volume'])
                    )
                    db.merge(ohlcv)
                
                db.commit()
                
                # Remove from failed queue
                db.delete(failed_ticker)
                db.commit()
                
                stats['succeeded'] += 1
                print(f"    ✓ {ticker_symbol} succeeded ({len(df)} records)")
                
            except Exception as e:
                print(f"    ✗ {ticker_symbol} failed: {e}")
                
                if failed_ticker.retry_count >= 3:
                    failed_ticker.status = 'permanent_failure'
                    stats['permanent_failures'] += 1
                else:
                    failed_ticker.status = 'pending'
                
                failed_ticker.error_message = str(e)
                db.commit()
            
            stats['retried'] += 1
        
        print(f"\n✅ Retry complete:")
        print(f"   Succeeded: {stats['succeeded']}")
        print(f"   Permanent failures: {stats['permanent_failures']}")
        print(f"   Remaining pending: {stats['total_failed'] - stats['succeeded'] - stats['permanent_failures']}\n")
        
        return stats
        
    finally:
        db.close()
