from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.database.models import Ticker, DailyOHLCV, StockFundamental
from app.utils.data_fetcher import fmp_client
from app.utils.market_calendar import is_trading_day, get_last_trading_day
from app.services.cache import cache_service
from app.services.stock_service import get_active_tickers
from datetime import datetime, timedelta, date as date_type
import time
from typing import List

scheduler = AsyncIOScheduler()


def update_all_stocks_nightly():
    """
    Nightly Batch Job: Update all active stocks using FMP Batch Quote API
    
    Strategy:
    - Only updates stocks that have been initialized (exist in stock_prices table)
    - Fetches today's OHLCV from FMP in batches of 100
    - Appends to existing historical data in PostgreSQL
    - Updates fundamentals in Stock table
    - Runs at 9 PM ET after market close
    """
    db = SessionLocal()
    start_time = datetime.now()
    
    try:
        print("\n" + "="*70)
        print(f" NIGHTLY STOCK UPDATE STARTED")
        print(f"   Time: {start_time.strftime('%Y-%m-%d %H:%M:%S ET')}")
        print("="*70 + "\n")
        
        # Check if today is a trading day
        today = datetime.now().date()
        if not is_trading_day(today):
            print("📅 Market closed today (weekend/holiday), skipping update")
            return
        
        # Get list of active tickers (stocks already in database)
        active_tickers = get_active_tickers(db)
        
        if not active_tickers:
            print("📋 No active stocks to update yet")
            print("   (Stocks will be added as users request them)")
            return
        
        total = len(active_tickers)
        batch_size = 100
        
        print(f"📋 Updating {total} active stocks in batches of {batch_size}...\n")
        
        # Track statistics
        stats = {
            'updated_prices': 0,
            'updated_fundamentals': 0,
            'failed': 0,
            'no_data': 0
        }
        
        # Process in batches
        for i in range(0, total, batch_size):
            batch = active_tickers[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total + batch_size - 1) // batch_size
            
            print(f"📦 Processing batch {batch_num}/{total_batches} ({len(batch)} stocks)...")
            
            try:
                # Fetch batch quotes from FMP
                quotes = fmp_client.get_batch_quotes(batch, quiet=True)
                
                if not quotes:
                    print(f"   ✗ No data returned for batch {batch_num}")
                    stats['no_data'] += len(batch)
                    continue
                
                # Process each quote
                for quote in quotes:
                    try:
                        ticker = quote.get('symbol')
                        if not ticker:
                            continue
                        
                        ticker = ticker.upper()
                        
                        # Extract data from FMP response
                        price_data = {
                            'open': quote.get('open'),
                            'high': quote.get('dayHigh'),
                            'low': quote.get('dayLow'),
                            'close': quote.get('price'),  # Current price = close for EOD
                            'volume': quote.get('volume')
                        }
                        
                        # Skip if missing critical data
                        if not all([price_data['open'], price_data['high'],
                                   price_data['low'], price_data['close']]):
                            stats['no_data'] += 1
                            continue

                        # 1. Get or create Ticker
                        ticker_obj = db.query(Ticker).filter(Ticker.symbol == ticker).first()

                        if not ticker_obj:
                            # Create new ticker
                            ticker_obj = Ticker(
                                symbol=ticker,
                                name=quote.get('name'),
                                exchange=quote.get('exchange')
                            )
                            db.add(ticker_obj)
                            db.flush()  # Get the ID

                        # 2. Update/Insert today's price record
                        price_record = DailyOHLCV(
                            ticker_id=ticker_obj.id,
                            date=today,
                            open=float(price_data['open']),
                            high=float(price_data['high']),
                            low=float(price_data['low']),
                            close=float(price_data['close']),
                            volume=int(price_data['volume']) if price_data['volume'] else 0
                        )
                        db.merge(price_record)  # Use merge to handle duplicates
                        stats['updated_prices'] += 1

                        # 3. Update StockFundamental
                        fundamental = db.query(StockFundamental).filter(
                            StockFundamental.ticker_id == ticker_obj.id
                        ).first()

                        if fundamental:
                            # Update existing fundamentals
                            fundamental.current_price = price_data['close']
                            fundamental.day_change_percent = quote.get('changesPercentage')
                            fundamental.volume = price_data['volume']
                            fundamental.market_cap = quote.get('marketCap')
                            fundamental.fifty_two_week_high = quote.get('yearHigh')
                            fundamental.fifty_two_week_low = quote.get('yearLow')
                            fundamental.pe_ratio = quote.get('pe')
                            fundamental.last_updated = datetime.now()
                        else:
                            # Create new fundamental entry
                            fundamental = StockFundamental(
                                ticker_id=ticker_obj.id,
                                current_price=price_data['close'],
                                day_change_percent=quote.get('changesPercentage'),
                                volume=price_data['volume'],
                                market_cap=quote.get('marketCap'),
                                fifty_two_week_high=quote.get('yearHigh'),
                                fifty_two_week_low=quote.get('yearLow'),
                                pe_ratio=quote.get('pe')
                            )
                            db.add(fundamental)

                        stats['updated_fundamentals'] += 1
                        
                        # Invalidate cache for this ticker
                        cache_service.delete(f"stock:{ticker}")
                        cache_service.delete(f"prices:{ticker}:historical")
                        
                    except Exception as e:
                        print(f"   ✗ Error processing {ticker}: {e}")
                        stats['failed'] += 1
                        continue
                
                # Commit batch
                db.commit()
                print(f"   ✓ Batch {batch_num} complete")
                
                # Small delay between batches
                if i + batch_size < total:
                    time.sleep(1)
                
            except Exception as e:
                print(f"   ✗ Batch {batch_num} failed: {e}")
                db.rollback()
                stats['failed'] += len(batch)
                continue
        
        # Clear pattern-based caches
        print("\n🗑️  Clearing screener caches...")
        cache_service.clear_pattern("screener:*")
        
        # Final report
        end_time = datetime.now()
        duration = (end_time - start_time).seconds / 60
        success_rate = ((stats['updated_prices']) / total * 100) if total > 0 else 0
        
        print("\n" + "="*70)
        print(f"✅ NIGHTLY UPDATE COMPLETE")
        print(f"   Duration: {duration:.1f} minutes")
        print(f"   Prices updated: {stats['updated_prices']}")
        print(f"   Fundamentals updated: {stats['updated_fundamentals']}")
        print(f"   Failed: {stats['failed']}")
        print(f"   No data: {stats['no_data']}")
        print(f"   Success rate: {success_rate:.1f}%")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR in nightly job: {e}")
        db.rollback()
        
    finally:
        db.close()


def trim_old_price_data():
    """
    Weekly job: Remove price data older than configured retention period
    
    - Runs Sunday at 3 AM ET
    - Keeps only the last N years of data (configured in settings)
    - Reclaims database storage space
    """
    db = SessionLocal()
    
    try:
        print("\n🗑️  TRIMMING OLD PRICE DATA")
        
        # Calculate cutoff date
        retention_years = getattr(settings, 'STOCK_HISTORY_YEARS', 4)
        cutoff_date = datetime.now().date() - timedelta(days=365 * retention_years)
        
        print(f"   Retention: {retention_years} years")
        print(f"   Cutoff date: {cutoff_date}")
        
        # Delete old records
        deleted = db.query(DailyOHLCV).filter(DailyOHLCV.date < cutoff_date).delete()
        db.commit()
        
        print(f"   ✓ Deleted {deleted} old price records")
        print(f"   ✓ Database space reclaimed")
        
        # Clear all price caches (data may have changed)
        cache_service.clear_pattern("prices:*")
        
    except Exception as e:
        print(f"   ✗ Error trimming data: {e}")
        db.rollback()
        
    finally:
        db.close()


# ====================================
# SCHEDULER CONFIGURATION
# ====================================

@scheduler.scheduled_job('cron', hour=21, minute=0, timezone='America/New_York')
def scheduled_nightly_update():
    """Runs at 9:00 PM ET every night"""
    print("⏰ Triggering nightly stock update...")
    update_all_stocks_nightly()


@scheduler.scheduled_job('cron', day_of_week='sun', hour=3, minute=0, timezone='America/New_York')
def scheduled_data_trimming():
    """Runs Sunday at 3:00 AM ET"""
    print("⏰ Triggering weekly data trimming...")
    trim_old_price_data()


def start_scheduler():
    """Start the APScheduler"""
    scheduler.start()
    print("✓ Scheduler initialized")
    print("   Nightly updates: 9:00 PM ET daily (active stocks only)")
    print("   Data trimming: 3:00 AM ET Sunday")
