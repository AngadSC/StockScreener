"""
Optimized historical price loader using PostgreSQL Bulk Upserts.
"""
import time
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy.dialects.postgresql import insert

from app.database.connection import SessionLocal
from app.database.models import Ticker, DailyOHLCV
from app.providers.factory import ProviderFactory
from app.config import settings

def load_sp500_historical():
    """Load historical prices using lightning-fast bulk upserts"""
    db = SessionLocal()
    
    try:
        print("\n" + "="*70)
        print("🚀 STARTING BULK HISTORICAL LOAD")
        print("="*70 + "\n")
        
        # 1. PRE-FETCH TICKERS (Optimization)
        ticker_objs = db.query(Ticker).all()
        if not ticker_objs:
            print("❌ No tickers in database.")
            return
        
        ticker_map = {t.symbol: t.id for t in ticker_objs}
        ticker_symbols = list(ticker_map.keys())
        total_tickers = len(ticker_symbols)
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=365 * settings.STOCK_HISTORY_YEARS)
        provider = ProviderFactory.get_historical_provider()
        
        stats = {'records': 0, 'tickers': 0}
        script_start = time.perf_counter()
        
        # 2. BATCHING
        batch_size = 50
        batches = [ticker_symbols[i:i + batch_size] for i in range(0, total_tickers, batch_size)]
        
        for batch_num, batch in enumerate(batches, 1):
            batch_start = time.perf_counter()
            try:
                print(f"📦 Batch {batch_num}/{len(batches)} ({', '.join(batch[:3])}...)")
                
                # --- STEP 1: DOWNLOAD ---
                dl_start = time.perf_counter()
                prices_df = provider.get_batch_historical_prices(batch, start_date, end_date, is_bulk_load=True)
                if prices_df is None or prices_df.empty:
                    continue
                print(f"   ⏱️  Download: {time.perf_counter() - dl_start:.2f}s")

                # --- STEP 2: PREPARE DATA ---
                prep_start = time.perf_counter()
                rows_to_upsert = []
                
                for _, row in prices_df.iterrows():
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
                
                print(f"   ⏱️  Data Prep: {time.perf_counter() - prep_start:.2f}s")

                # --- STEP 3: BULK UPSERT (The Performance Fix) ---
                if rows_to_upsert:
                    db_start = time.perf_counter()
                    
                    # Create the "INSERT ... ON CONFLICT" statement
                    stmt = insert(DailyOHLCV).values(rows_to_upsert)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['ticker_id', 'date'], # Composite Primary Key
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
                    
                    db_time = time.perf_counter() - db_start
                    stats['records'] += len(rows_to_upsert)
                    stats['tickers'] += len(batch)
                    print(f"   ⏱️  DB Bulk Upsert: {db_time:.2f}s for {len(rows_to_upsert)} rows")
                
                print(f"   ✅ Batch {batch_num} Total: {time.perf_counter() - batch_start:.2f}s")
                print(f"   📊 Total Progress: {stats['tickers']}/{total_tickers} tickers\n")
                
            except Exception as e:
                print(f"   ✗ Batch {batch_num} failed: {e}")
                db.rollback()
                if "429" in str(e): break
                continue
        
        print(f"\n✅ FINISHED: {stats['records']:,} records in {(time.perf_counter() - script_start)/60:.2f} mins")
        
    finally:
        db.close()

if __name__ == "__main__":
    load_sp500_historical()