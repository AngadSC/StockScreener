from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from app.database.connection import SessionLocal
from app.database.models import Ticker, DailyOHLCV, StockFundamental
from app.providers.factory import ProviderFactory
from app.utils.market_calendar import is_trading_day, get_last_trading_day, get_previous_trading_day
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

    IMPORTANT FILTERING BEHAVIOR:
    - Only returns stocks that have StockFundamental records
    - New stocks without fundamentals will NOT be included
    - Stocks where fundamental fetch failed will NOT be included
    - This prevents updating price data for stocks we're not tracking
    - To update ALL stocks (including those without fundamentals), use get_all_tickers() instead

    Returns:
        List of ticker symbols that have fundamental data
    """
    tickers = db.query(Ticker.symbol).join(
        StockFundamental,
        Ticker.id == StockFundamental.ticker_id
    ).distinct().all()

    return [t[0] for t in tickers]


def get_all_tickers(db: Session) -> List[str]:
    """
    Get ALL tickers in the database, regardless of whether they have fundamentals.

    Use this when you want to update price data for all stocks, including:
    - New stocks that haven't been processed yet
    - Stocks where fundamental fetch failed
    - Stocks that are no longer tracked but still have price history

    Returns:
        List of all ticker symbols in the database
    """
    tickers = db.query(Ticker.symbol).distinct().all()
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

        # NOTE: Using get_active_tickers() - only updates stocks with fundamentals
        # To update ALL stocks in DB (including those without fundamentals), use get_all_tickers()
        active_tickers = get_all_tickers(db)
        if not active_tickers:
            print("📋 No active stocks to update yet")
            print("    Run bulk_population.py or fundamentals_updater.py first to populate fundamental data")
            return

        total = len(active_tickers)
        print(f"📋 Updating {total} active stocks (with fundamental data)...\n")

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

        # yfinance treats `end` as exclusive, so use next day to include today's close.
        end_date = today + timedelta(days=1)
        # IMPORTANT: Use get_previous_trading_day() to ensure start_date < end_date
        # This prevents Yahoo Finance "startDate == endDate" errors
        start_date = get_previous_trading_day(today) if not manual_trigger else today - timedelta(days=5)

        print(f"📅 Fetching prices from {start_date} to {end_date} (end-exclusive)\n")

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


@scheduler.scheduled_job('cron', day_of_week='mon-fri', hour=7, minute=45, timezone='America/New_York')
def scheduled_daily_brief():
    """Runs weekdays at 7:45 AM ET — sends the AI Daily Market Brief."""
    print("⏰ Triggering daily market brief...")
    # Imported lazily to avoid import cycles at scheduler module load.
    from app.jobs.daily_brief_job import run_daily_brief
    run_daily_brief()

@scheduler.scheduled_job('cron', day_of_week='mon-fri', hour=7, minute=0, timezone='America/New_York')
def scheduled_watchlist_digest():
    """Runs weekday mornings at 7:00 AM ET: Elite watchlist AI digest email."""
    print("⏰ Triggering Elite watchlist AI digest...")
    # Imported lazily so a digest-side import error can never break the scheduler.
    from app.jobs.watchlist_digest_job import run_watchlist_digest
    run_watchlist_digest()

@scheduler.scheduled_job('cron', hour=22, minute=30, timezone='America/New_York')
def scheduled_market_scans_warm():
    """Runs at 10:30 PM ET, after the nightly sync -- warms the market scanners cache"""
    from app.jobs.market_scans_job import warm_market_scans_cache
    warm_market_scans_cache()


def start_scheduler():
    """Start the APScheduler"""
    scheduler.start()
    print("✓ Scheduler initialized")
