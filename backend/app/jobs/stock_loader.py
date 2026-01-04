from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from app.database.connection import SessionLocal
from app.database.models import Ticker, DailyOHLCV, StockFundamental
from app.providers.factory import ProviderFactory
from app.utils.market_calendar import is_trading_day, get_last_trading_day
from app.services.cache import cache_service
from app.config import settings
from datetime import datetime, timedelta, date as date_type
import time
from typing import List
import pandas as pd

scheduler = AsyncIOScheduler()


def get_active_tickers(db: Session) -> List[str]:
    """
    Get list of tickers that have fundamental data.
    These are the stocks actively tracked in the system.
    """
    tickers = db.query(Ticker.symbol).join(
        StockFundamental,
        Ticker.id == StockFundamental.ticker_id
    ).distinct().all()

    return [t[0] for t in tickers]


def update_all_stocks_batch(manual_trigger: bool = False):
    """
    Batch Job: Update all active stocks using provider system.
    Strategy: Optimized with Bulk Upserts for price updates.
    """
    db = SessionLocal()
    start_time = datetime.now()

    try:
        print("\n" + "="*70)
        print(f" {'MANUAL' if manual_trigger else 'NIGHTLY'} STOCK UPDATE STARTED")
        print(f"   Time: {start_time.strftime('%Y-%m-%d %H:%M:%S ET')}")
        print("="*70 + "\n")

        today = datetime.now().date()
        if not manual_trigger and not is_trading_day(today):
            print("📅 Market closed today (weekend/holiday), skipping update")
            return

        active_tickers = get_active_tickers(db)
        if not active_tickers:
            print("📋 No active stocks to update yet")
            return

        total = len(active_tickers)
        print(f"📋 Updating {total} active stocks...\n")

        stats = {
            'updated_prices': 0,
            'updated_fundamentals': 0,
            'failed': 0,
            'no_data': 0
        }

        # ====================================
        # STEP 1: UPDATE FUNDAMENTALS
        # ====================================
        print("=" * 70)
        print("STEP 1: Updating Fundamentals (YahooQuery)")
        print("=" * 70 + "\n")

        fundamentals_provider = ProviderFactory.get_fundamentals_provider()
        fundamentals_batch_size = settings.YAHOOQUERY_BATCH_SIZE 

        for i in range(0, total, fundamentals_batch_size):
            batch = active_tickers[i:i + fundamentals_batch_size]
            batch_num = (i // fundamentals_batch_size) + 1
            total_batches = (total + fundamentals_batch_size - 1) // fundamentals_batch_size

            print(f"📦 Fundamentals batch {batch_num}/{total_batches} ({len(batch)} tickers)...")

            try:
                fundamentals_data = fundamentals_provider.get_batch_fundamentals(batch)
                if not fundamentals_data:
                    stats['no_data'] += len(batch)
                    continue

                for ticker_symbol, fund_data in fundamentals_data.items():
                    try:
                        ticker_obj = db.query(Ticker).filter(Ticker.symbol == ticker_symbol).first()
                        if not ticker_obj:
                            ticker_obj = Ticker(
                                symbol=ticker_symbol,
                                name=fund_data.get('additional_data', {}).get('price', {}).get('shortName'),
                                exchange=fund_data.get('additional_data', {}).get('price', {}).get('exchange')
                            )
                            db.add(ticker_obj)
                            db.flush()

                        fundamental = db.query(StockFundamental).filter(
                            StockFundamental.ticker_id == ticker_obj.id
                        ).first()

                        # Update existing or create new fundamental record
                        if fundamental:
                            for key, val in fund_data.items():
                                if hasattr(fundamental, key) and key != 'ticker':
                                    setattr(fundamental, key, val)
                            fundamental.last_updated = datetime.now()
                        else:
                            new_fund = StockFundamental(ticker_id=ticker_obj.id, **{k:v for k,v in fund_data.items() if k != 'ticker'})
                            db.add(new_fund)

                        stats['updated_fundamentals'] += 1
                    except Exception as e:
                        print(f"   ✗ Error processing {ticker_symbol}: {e}")
                        stats['failed'] += 1

                db.commit()
                print(f"   ✓ Batch {batch_num} complete")

            except Exception as e:
                print(f"   ✗ Batch {batch_num} failed: {e}")
                db.rollback()
                stats['failed'] += len(batch)

        # ====================================
        # STEP 2: UPDATE HISTORICAL PRICES (Optimized)
        # ====================================
        print("\n" + "=" * 70)
        print("STEP 2: Updating Historical Prices (YFinance)")
        print("=" * 70 + "\n")

        historical_provider = ProviderFactory.get_historical_provider()
        price_batch_size = settings.YFINANCE_BATCH_SIZE 

        end_date = today
        start_date = get_last_trading_day(today) if not manual_trigger else today - timedelta(days=5)

        for i in range(0, total, price_batch_size):
            batch = active_tickers[i:i + price_batch_size]
            batch_num = (i // price_batch_size) + 1
            
            print(f"📦 Price batch {batch_num} ({len(batch)} tickers)...")

            try:
                prices_df = historical_provider.get_batch_historical_prices(
                    batch, start_date, end_date, is_bulk_load=False
                )

                if prices_df is None or prices_df.empty:
                    stats['no_data'] += len(batch)
                    continue

                # Prepare Bulk Upsert
                ticker_objs = db.query(Ticker).filter(Ticker.symbol.in_(batch)).all()
                ticker_map = {t.symbol: t.id for t in ticker_objs}
                rows_to_upsert = []

                # Handle multi-ticker dataframe from provider
                if 'ticker' in prices_df.columns:
                    for _, row in prices_df.iterrows():
                        t_id = ticker_map.get(row['ticker'])
                        if t_id:
                            rows_to_upsert.append({
                                "ticker_id": t_id, "date": row['date'],
                                "open": float(row['Open']), "high": float(row['High']),
                                "low": float(row['Low']), "close": float(row['Close']),
                                "volume": int(row['Volume'])
                            })
                else:
                    # Multi-index format
                    for ticker_symbol in batch:
                        t_id = ticker_map.get(ticker_symbol)
                        if t_id and ticker_symbol in prices_df.columns.get_level_values(1):
                            ticker_data = prices_df.xs(ticker_symbol, level=1, axis=1)
                            for date_idx, row in ticker_data.iterrows():
                                if pd.notna(row.get('Close')):
                                    rows_to_upsert.append({
                                        "ticker_id": t_id, "date": date_idx.date(),
                                        "open": float(row['Open']), "high": float(row['High']),
                                        "low": float(row['Low']), "close": float(row['Close']),
                                        "volume": int(row['Volume'])
                                    })

                if rows_to_upsert:
                    stmt = insert(DailyOHLCV).values(rows_to_upsert)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['ticker_id', 'date'],
                        set_={col: getattr(stmt.excluded, col) for col in ["open", "high", "low", "close", "volume"]}
                    )
                    db.execute(stmt)
                    stats['updated_prices'] += len(rows_to_upsert)

                # Invalidate caches
                for ticker in batch:
                    cache_service.delete(f"stock:{ticker}")
                    cache_service.delete(f"prices:{ticker}:historical")

                db.commit()
                print(f"   ✓ Batch {batch_num} complete")

            except Exception as e:
                print(f"   ✗ Batch {batch_num} failed: {e}")
                db.rollback()
                stats['failed'] += len(batch)

        print("\n🗑️  Clearing screener caches...")
        cache_service.clear_pattern("screener:*")

        end_time = datetime.now()
        duration = (end_time - start_time).seconds / 60
        print(f"\n✅ BATCH UPDATE COMPLETE in {duration:.1f} mins")

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR in batch job: {e}")
        db.rollback()
    finally:
        db.close()


def trim_old_price_data():
    """Weekly job: Remove price data older than configured retention period"""
    db = SessionLocal()
    try:
        print("\n🗑️  TRIMMING OLD PRICE DATA")
        cutoff_date = datetime.now().date() - timedelta(days=365 * settings.STOCK_HISTORY_YEARS)
        deleted = db.query(DailyOHLCV).filter(DailyOHLCV.date < cutoff_date).delete()
        db.commit()
        print(f"   ✓ Deleted {deleted} old price records")
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
    update_all_stocks_batch(manual_trigger=False)


@scheduler.scheduled_job('cron', day_of_week='sun', hour=3, minute=0, timezone='America/New_York')
def scheduled_data_trimming():
    """Runs Sunday at 3:00 AM ET"""
    print("⏰ Triggering weekly data trimming...")
    trim_old_price_data()


def start_scheduler():
    """Start the APScheduler"""
    scheduler.start()
    print("✓ Scheduler initialized")