import time
from datetime import datetime, timedelta
import pandas as pd
from app.database.connection import SessionLocal
from app.database.models import Ticker, DailyOHLCV
from app.providers.factory import ProviderFactory
from app.config import settings

def load_sp500_historical():
    """Load historical prices with detailed debug timing"""
    db = SessionLocal()
    
    try:
        print("\n" + "="*70)
        print("📈 LOADING S&P 500 HISTORICAL PRICES (DEBUG MODE)")
        print("="*70 + "\n")
        
        tickers = db.query(Ticker).all()
        if not tickers:
            print("❌ No tickers in database.")
            return
        
        ticker_symbols = [t.symbol for t in tickers]
        total = len(ticker_symbols)
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=365 * settings.STOCK_HISTORY_YEARS)
        provider = ProviderFactory.get_historical_provider()
        
        stats = {'batches_processed': 0, 'price_records_added': 0, 'tickers_processed': 0}
        start_time = time.perf_counter()
        
        batch_size = 10 
        batches = [ticker_symbols[i:i + batch_size] for i in range(0, total, batch_size)]
        
        for batch_num, batch in enumerate(batches, 1):
            batch_start = time.perf_counter()
            try:
                print(f"📦 Batch {batch_num}/{len(batches)}: {', '.join(batch[:3])}...")
                
                # TIMER 1: Download
                dl_start = time.perf_counter()
                prices_df = provider.get_batch_historical_prices(batch, start_date, end_date, is_bulk_load=True)
                dl_end = time.perf_counter()
                print(f"   ⏱️  Download Time: {dl_end - dl_start:.2f}s")
                
                if prices_df is None or prices_df.empty:
                    continue

                # TIMER 2: Processing & DB Merging
                proc_start = time.perf_counter()
                batch_records = 0
                
                for ticker_symbol in batch:
                    ticker_ticker_start = time.perf_counter()
                    
                    ticker_obj = db.query(Ticker).filter(Ticker.symbol == ticker_symbol).first()
                    if not ticker_obj: continue
                    
                    # Extract ticker data from DataFrame
                    if 'ticker' in prices_df.columns:
                        ticker_data = prices_df[prices_df['ticker'] == ticker_symbol]
                    else:
                        if ticker_symbol in prices_df.columns.get_level_values(1):
                            ticker_data = prices_df.xs(ticker_symbol, level=1, axis=1)
                        else: continue

                    # TIMER 3: The Row-by-Row Merge (The likely bottleneck)
                    merge_start = time.perf_counter()
                    for idx, row in ticker_data.iterrows():
                        if pd.notna(row.get('Close')):
                            price_record = DailyOHLCV(
                                ticker_id=ticker_obj.id,
                                date=idx.date() if not isinstance(idx, int) else row['date'],
                                open=float(row['Open']) if pd.notna(row['Open']) else None,
                                high=float(row['High']) if pd.notna(row['High']) else None,
                                low=float(row['Low']) if pd.notna(row['Low']) else None,
                                close=float(row['Close']),
                                volume=int(row['Volume']) if pd.notna(row['Volume']) else 0
                            )
                            db.merge(price_record) # <--- This is slow
                            batch_records += 1
                    
                    merge_end = time.perf_counter()
                    ticker_total = merge_end - ticker_ticker_start
                    print(f"      🔹 {ticker_symbol}: {len(ticker_data)} rows merged in {merge_end - merge_start:.2f}s (Total: {ticker_total:.2f}s)")
                
                proc_end = time.perf_counter()
                print(f"   ⏱️  Total Processing Time: {proc_end - proc_start:.2f}s")

                # TIMER 4: Commit
                commit_start = time.perf_counter()
                db.commit()
                commit_end = time.perf_counter()
                print(f"   ⏱️  DB Commit Time: {commit_end - commit_start:.2f}s")
                
                stats['tickers_processed'] += len(batch)
                stats['price_records_added'] += batch_records
                print(f"   ✅ Batch {batch_num} done in {time.perf_counter() - batch_start:.2f}s\n")
                
            except Exception as e:
                print(f"   ✗ Batch failed: {e}")
                db.rollback()
                
    finally:
        db.close()