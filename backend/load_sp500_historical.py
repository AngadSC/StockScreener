"""
Load historical price data for S&P 500 stocks using YFinance with rate limiting.
Assumes tickers are already in the database from load_sp500.py
"""

from app.database.connection import SessionLocal
from app.database.models import Ticker, DailyOHLCV
from app.providers.factory import ProviderFactory
from app.config import settings
from datetime import datetime, timedelta
import pandas as pd

def load_sp500_historical():
    """Load historical prices for all S&P 500 stocks in database"""
    db = SessionLocal()
    
    try:
        print("\n" + "="*70)
        print("📈 LOADING S&P 500 HISTORICAL PRICES")
        print("="*70 + "\n")
        
        # Get all tickers from database
        print("Fetching tickers from database...")
        tickers = db.query(Ticker).all()
        
        if not tickers:
            print("❌ No tickers in database. Run load_sp500.py first!")
            return
        
        ticker_symbols = [t.symbol for t in tickers]
        total = len(ticker_symbols)
        print(f"✓ Found {total} tickers in database")
        
        # Date range: Last 5 years
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=365 * settings.STOCK_HISTORY_YEARS)
        print(f"📅 Date range: {start_date} to {end_date}")
        print(f"📊 Years of data: {settings.STOCK_HISTORY_YEARS}")
        print()
        
        # Get YFinance provider
        provider = ProviderFactory.get_historical_provider()
        print(f"✓ Using provider: {provider.name}")
        print(f"✓ Batch size: 10 tickers per call (reduced to avoid timeouts)")
        print(f"✓ Rate limiting: {settings.YFINANCE_INITIAL_JITTER_MIN}-{settings.YFINANCE_INITIAL_JITTER_MAX}s between batches")
        print()
        
        # Track statistics
        stats = {
            'batches_processed': 0,
            'price_records_added': 0,
            'tickers_processed': 0,
            'failed': 0
        }
        
        start_time = datetime.now()
        
        # Process in batches - REDUCED SIZE
        batch_size = 10  # Smaller batches to avoid timeout
        batches = [ticker_symbols[i:i + batch_size] for i in range(0, total, batch_size)]
        total_batches = len(batches)
        
        print(f"📦 Processing {total_batches} batches...\n")
        
        for batch_num, batch in enumerate(batches, 1):
            try:
                print(f"📦 Batch {batch_num}/{total_batches} ({len(batch)} tickers): {', '.join(batch[:5])}{'...' if len(batch) > 5 else ''}")
                print(f"   🔄 Downloading data (this may take 1-2 minutes)...")
                
                # Fetch batch historical prices
                prices_df = provider.get_batch_historical_prices(
                    batch,
                    start_date,
                    end_date,
                    is_bulk_load=True  # Uses 15-25s jitter
                )
                
                print(f"   ✓ Download complete, processing data...")
                
                if prices_df is None or prices_df.empty:
                    print(f"   ✗ No data returned")
                    stats['failed'] += len(batch)
                    continue
                
                # Process each ticker's prices
                batch_records = 0
                for ticker_symbol in batch:
                    try:
                        # Get ticker object
                        ticker_obj = db.query(Ticker).filter(
                            Ticker.symbol == ticker_symbol
                        ).first()
                        
                        if not ticker_obj:
                            continue
                        
                        # Extract this ticker's data
                        if 'ticker' in prices_df.columns:
                            # Long format (multi-ticker)
                            ticker_data = prices_df[prices_df['ticker'] == ticker_symbol]
                            
                            for _, row in ticker_data.iterrows():
                                if pd.notna(row.get('Close')):
                                    price_record = DailyOHLCV(
                                        ticker_id=ticker_obj.id,
                                        date=row['date'],
                                        open=float(row['Open']) if pd.notna(row['Open']) else None,
                                        high=float(row['High']) if pd.notna(row['High']) else None,
                                        low=float(row['Low']) if pd.notna(row['Low']) else None,
                                        close=float(row['Close']),
                                        volume=int(row['Volume']) if pd.notna(row['Volume']) else 0
                                    )
                                    db.merge(price_record)
                                    batch_records += 1
                        else:
                            # Wide format (single ticker) - check multi-index
                            if ticker_symbol in prices_df.columns.get_level_values(1):
                                ticker_data = prices_df.xs(ticker_symbol, level=1, axis=1)
                                
                                for date_idx, row in ticker_data.iterrows():
                                    if pd.notna(row.get('Close')):
                                        price_record = DailyOHLCV(
                                            ticker_id=ticker_obj.id,
                                            date=date_idx.date(),
                                            open=float(row['Open']) if pd.notna(row['Open']) else None,
                                            high=float(row['High']) if pd.notna(row['High']) else None,
                                            low=float(row['Low']) if pd.notna(row['Low']) else None,
                                            close=float(row['Close']),
                                            volume=int(row['Volume']) if pd.notna(row['Volume']) else 0
                                        )
                                        db.merge(price_record)
                                        batch_records += 1
                        
                        stats['tickers_processed'] += 1
                        
                    except Exception as e:
                        print(f"   ✗ Error processing {ticker_symbol}: {e}")
                        stats['failed'] += 1
                        continue
                
                # Commit batch
                db.commit()
                stats['batches_processed'] += 1
                stats['price_records_added'] += batch_records
                
                # Progress report
                elapsed = (datetime.now() - start_time).seconds / 60
                rate = stats['tickers_processed'] / elapsed if elapsed > 0 else 0
                eta = (total - stats['tickers_processed']) / rate if rate > 0 else 0
                
                print(f"   ✓ Batch complete: {batch_records} price records added")
                print(f"\n📊 Progress: {stats['tickers_processed']}/{total} tickers ({stats['tickers_processed']/total*100:.1f}%)")
                print(f"   💾 Total records: {stats['price_records_added']:,}")
                print(f"   ⏱  Rate: {rate:.1f} tickers/min | ETA: {eta:.0f} min\n")
                
            except Exception as e:
                print(f"   ✗ Batch {batch_num} failed: {e}")
                db.rollback()
                stats['failed'] += len(batch)
                
                # Stop if persistent 429
                if "429" in str(e):
                    print("🛑 Rate limit exceeded. Stopping.")
                    break
                continue
        
        # Final report
        end_time = datetime.now()
        duration = (end_time - start_time).seconds / 60
        success_rate = (stats['tickers_processed'] / total * 100) if total > 0 else 0
        
        print("\n" + "="*70)
        print("✅ HISTORICAL PRICE LOADING COMPLETE")
        print("="*70)
        print(f"   Duration: {duration:.1f} minutes")
        print(f"   Batches processed: {stats['batches_processed']}/{total_batches}")
        print(f"   Tickers processed: {stats['tickers_processed']}/{total}")
        print(f"   Price records added: {stats['price_records_added']:,}")
        print(f"   Failed: {stats['failed']}")
        print(f"   Success rate: {success_rate:.1f}%")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        db.rollback()
        
    finally:
        db.close()

if __name__ == "__main__":
    print("\n🚀 Starting historical price loader...")
    load_sp500_historical()
    print("✨ Done!\n")
