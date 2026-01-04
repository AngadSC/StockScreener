"""
Optimized historical price loader with high-resolution debug timing.
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
    """Load historical prices with detailed debug timing and optimized DB hits"""
    db = SessionLocal()
    
    try:
        print("\n" + "="*70)
        print("📈 LOADING S&P 500 HISTORICAL PRICES (DEBUG MODE)")
        print("="*70 + "\n")
        
        # 1. PRE-FETCH TICKERS (Optimization: Prevents 500+ extra DB queries)
        print("Fetching tickers and building cache...")
        ticker_objs = db.query(Ticker).all()
        if not ticker_objs:
            print("❌ No tickers in database. Run load_sp500.py first!")
            return
        
        # Map symbol -> id for instant lookups
        ticker_map = {t.symbol: t.id for t in ticker_objs}
        ticker_symbols = list(ticker_map.keys())
        total = len(ticker_symbols)
        print(f"✓ Cached {total} tickers from database")
        
        # Date range setup
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=365 * settings.STOCK_HISTORY_YEARS)
        print(f"📅 Date range: {start_date} to {end_date} ({settings.STOCK_HISTORY_YEARS} years)")
        
        # Provider setup
        provider = ProviderFactory.get_historical_provider()
        print(f"✓ Using provider: {provider.name}")
        
        stats = {
            'batches_processed': 0,
            'price_records_added': 0,
            'tickers_processed': 0,
            'failed': 0
        }
        
        script_start = time.perf_counter()
        
        # Batching
        batch_size = 10 
        batches = [ticker_symbols[i:i + batch_size] for i in range(0, total, batch_size)]
        total_batches = len(batches)
        
        print(f"📦 Processing {total_batches} batches...\n")
        
        for batch_num, batch in enumerate(batches, 1):
            batch_start = time.perf_counter()
            try:
                print(f"📦 Batch {batch_num}/{total_batches} ({len(batch)} tickers): {', '.join(batch[:5])}...")
                
                # --- TIMER 1: DOWNLOAD ---
                dl_start = time.perf_counter()
                prices_df = provider.get_batch_historical_prices(
                    batch, start_date, end_date, is_bulk_load=True
                )
                dl_time = time.perf_counter() - dl_start
                print(f"   ⏱️  Download: {dl_time:.2f}s")
                
                if prices_df is None or prices_df.empty:
                    print(f"   ✗ No data returned for this batch.")
                    stats['failed'] += len(batch)
                    continue

                # --- TIMER 2: DATA PROCESSING ---
                proc_start = time.perf_counter()
                batch_records_count = 0
                
                for ticker_symbol in batch:
                    t_id = ticker_map.get(ticker_symbol)
                    if not t_id: continue
                    
                    # Extract ticker data (handles both 'long' and 'wide' pandas formats)
                    if 'ticker' in prices_df.columns:
                        ticker_data = prices_df[prices_df['ticker'] == ticker_symbol]
                    elif ticker_symbol in prices_df.columns.get_level_values(1):
                        ticker_data = prices_df.xs(ticker_symbol, level=1, axis=1)
                    else:
                        continue

                    for idx, row in ticker_data.iterrows():
                        if pd.notna(row.get('Close')):
                            # Use SQLAlchemy merge to handle existing records
                            # (Replace with bulk_insert_mappings for even more speed if table is empty)
                            price_record = DailyOHLCV(
                                ticker_id=t_id,
                                date=idx.date() if hasattr(idx, 'date') else row.get('date'),
                                open=float(row['Open']) if pd.notna(row['Open']) else None,
                                high=float(row['High']) if pd.notna(row['High']) else None,
                                low=float(row['Low']) if pd.notna(row['Low']) else None,
                                close=float(row['Close']),
                                volume=int(row['Volume']) if pd.notna(row['Volume']) else 0
                            )
                            db.merge(price_record)
                            batch_records_count += 1
                
                proc_time = time.perf_counter() - proc_start
                print(f"   ⏱️  Processing/Merge: {proc_time:.2f}s for {batch_records_count} rows")

                # --- TIMER 3: DB COMMIT ---
                commit_start = time.perf_counter()
                db.commit()
                commit_time = time.perf_counter() - commit_start
                print(f"   ⏱️  DB Commit: {commit_time:.2f}s")
                
                # Stats update
                stats['batches_processed'] += 1
                stats['price_records_added'] += batch_records_count
                stats['tickers_processed'] += len(batch)
                
                batch_total = time.perf_counter() - batch_start
                print(f"   ✅ Batch {batch_num} Total: {batch_total:.2f}s")
                print(f"   📊 Progress: {stats['tickers_processed']}/{total} tickers\n")
                
            except Exception as e:
                print(f"   ✗ Batch {batch_num} failed: {e}")
                db.rollback()
                stats['failed'] += len(batch)
                if "429" in str(e):
                    print("🛑 Rate limit exceeded. Stopping.")
                    break
                continue
        
        # Final Report
        total_duration = (time.perf_counter() - script_start) / 60
        print("\n" + "="*70)
        print("✅ HISTORICAL PRICE LOADING COMPLETE")
        print("="*70)
        print(f"   Total Duration: {total_duration:.2f} minutes")
        print(f"   Price records added: {stats['price_records_added']:,}")
        print(f"   Success Rate: {(stats['tickers_processed']/total)*100:.1f}%")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    load_sp500_historical()