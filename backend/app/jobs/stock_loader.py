from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session
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

    Strategy:
    - Step 1: Fetch fundamentals using YahooQuery (50 tickers per API call)
    - Step 2: Fetch historical prices using YFinance (100 tickers per API call)
    - Only updates stocks that exist in the database
    - Runs nightly at 9 PM ET or can be manually triggered by admin

    Args:
        manual_trigger: If True, bypasses trading day check (for admin-initiated updates)
    """
    db = SessionLocal()
    start_time = datetime.now()

    try:
        print("\n" + "="*70)
        print(f" {'MANUAL' if manual_trigger else 'NIGHTLY'} STOCK UPDATE STARTED")
        print(f"   Time: {start_time.strftime('%Y-%m-%d %H:%M:%S ET')}")
        print("="*70 + "\n")

        # Check if today is a trading day (skip for manual triggers)
        today = datetime.now().date()
        if not manual_trigger and not is_trading_day(today):
            print("📅 Market closed today (weekend/holiday), skipping update")
            return

        # Get list of active tickers
        active_tickers = get_active_tickers(db)

        if not active_tickers:
            print("📋 No active stocks to update yet")
            print("   (Stocks will be added as users request them)")
            return

        total = len(active_tickers)

        print(f"📋 Updating {total} active stocks...\n")

        # Track statistics
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
        fundamentals_batch_size = settings.YAHOOQUERY_BATCH_SIZE  # 50 tickers per call

        for i in range(0, total, fundamentals_batch_size):
            batch = active_tickers[i:i + fundamentals_batch_size]
            batch_num = (i // fundamentals_batch_size) + 1
            total_batches = (total + fundamentals_batch_size - 1) // fundamentals_batch_size

            print(f"📦 Fundamentals batch {batch_num}/{total_batches} ({len(batch)} tickers)...")

            try:
                # Fetch batch fundamentals (ONE API CALL for all tickers!)
                fundamentals_data = fundamentals_provider.get_batch_fundamentals(batch)

                if not fundamentals_data:
                    print(f"   ✗ No fundamentals data returned for batch {batch_num}")
                    stats['no_data'] += len(batch)
                    continue

                # Process each ticker's fundamentals
                for ticker_symbol, fund_data in fundamentals_data.items():
                    try:
                        # Get or create ticker
                        ticker_obj = db.query(Ticker).filter(
                            Ticker.symbol == ticker_symbol
                        ).first()

                        if not ticker_obj:
                            # Create new ticker
                            ticker_obj = Ticker(
                                symbol=ticker_symbol,
                                name=fund_data.get('additional_data', {}).get('price', {}).get('shortName'),
                                exchange=fund_data.get('additional_data', {}).get('price', {}).get('exchange')
                            )
                            db.add(ticker_obj)
                            db.flush()

                        # Update or create fundamentals
                        fundamental = db.query(StockFundamental).filter(
                            StockFundamental.ticker_id == ticker_obj.id
                        ).first()

                        if fundamental:
                            # Update existing
                            fundamental.current_price = fund_data.get('current_price')
                            fundamental.day_change_percent = fund_data.get('day_change_percent')
                            fundamental.volume = fund_data.get('volume')
                            fundamental.avg_volume = fund_data.get('avg_volume')
                            fundamental.market_cap = fund_data.get('market_cap')
                            fundamental.pe_ratio = fund_data.get('pe_ratio')
                            fundamental.forward_pe = fund_data.get('forward_pe')
                            fundamental.peg_ratio = fund_data.get('peg_ratio')
                            fundamental.price_to_book = fund_data.get('price_to_book')
                            fundamental.price_to_sales = fund_data.get('price_to_sales')
                            fundamental.ev_to_ebitda = fund_data.get('ev_to_ebitda')
                            fundamental.profit_margin = fund_data.get('profit_margin')
                            fundamental.operating_margin = fund_data.get('operating_margin')
                            fundamental.roe = fund_data.get('roe')
                            fundamental.roa = fund_data.get('roa')
                            fundamental.debt_to_equity = fund_data.get('debt_to_equity')
                            fundamental.current_ratio = fund_data.get('current_ratio')
                            fundamental.quick_ratio = fund_data.get('quick_ratio')
                            fundamental.revenue_growth = fund_data.get('revenue_growth')
                            fundamental.earnings_growth = fund_data.get('earnings_growth')
                            fundamental.dividend_yield = fund_data.get('dividend_yield')
                            fundamental.dividend_rate = fund_data.get('dividend_rate')
                            fundamental.payout_ratio = fund_data.get('payout_ratio')
                            fundamental.beta = fund_data.get('beta')
                            fundamental.fifty_two_week_high = fund_data.get('fifty_two_week_high')
                            fundamental.fifty_two_week_low = fund_data.get('fifty_two_week_low')
                            fundamental.sector = fund_data.get('sector')
                            fundamental.industry = fund_data.get('industry')
                            fundamental.last_updated = datetime.now()
                        else:
                            # Create new
                            fundamental = StockFundamental(
                                ticker_id=ticker_obj.id,
                                current_price=fund_data.get('current_price'),
                                day_change_percent=fund_data.get('day_change_percent'),
                                volume=fund_data.get('volume'),
                                avg_volume=fund_data.get('avg_volume'),
                                market_cap=fund_data.get('market_cap'),
                                pe_ratio=fund_data.get('pe_ratio'),
                                forward_pe=fund_data.get('forward_pe'),
                                peg_ratio=fund_data.get('peg_ratio'),
                                price_to_book=fund_data.get('price_to_book'),
                                price_to_sales=fund_data.get('price_to_sales'),
                                ev_to_ebitda=fund_data.get('ev_to_ebitda'),
                                profit_margin=fund_data.get('profit_margin'),
                                operating_margin=fund_data.get('operating_margin'),
                                roe=fund_data.get('roe'),
                                roa=fund_data.get('roa'),
                                debt_to_equity=fund_data.get('debt_to_equity'),
                                current_ratio=fund_data.get('current_ratio'),
                                quick_ratio=fund_data.get('quick_ratio'),
                                revenue_growth=fund_data.get('revenue_growth'),
                                earnings_growth=fund_data.get('earnings_growth'),
                                dividend_yield=fund_data.get('dividend_yield'),
                                dividend_rate=fund_data.get('dividend_rate'),
                                payout_ratio=fund_data.get('payout_ratio'),
                                beta=fund_data.get('beta'),
                                fifty_two_week_high=fund_data.get('fifty_two_week_high'),
                                fifty_two_week_low=fund_data.get('fifty_two_week_low'),
                                sector=fund_data.get('sector'),
                                industry=fund_data.get('industry')
                            )
                            db.add(fundamental)

                        stats['updated_fundamentals'] += 1

                    except Exception as e:
                        print(f"   ✗ Error processing {ticker_symbol}: {e}")
                        stats['failed'] += 1
                        continue

                # Commit batch
                db.commit()
                print(f"   ✓ Batch {batch_num} complete ({len(fundamentals_data)} fundamentals updated)")

            except Exception as e:
                print(f"   ✗ Batch {batch_num} failed: {e}")
                db.rollback()
                stats['failed'] += len(batch)
                continue

        # ====================================
        # STEP 2: UPDATE HISTORICAL PRICES
        # ====================================
        print("\n" + "=" * 70)
        print("STEP 2: Updating Historical Prices (YFinance)")
        print("=" * 70 + "\n")

        historical_provider = ProviderFactory.get_historical_provider()
        price_batch_size = settings.YFINANCE_BATCH_SIZE  # 100 tickers per call

        # Calculate date range (fetch last trading day)
        end_date = today
        start_date = get_last_trading_day(today) if not manual_trigger else today - timedelta(days=5)

        for i in range(0, total, price_batch_size):
            batch = active_tickers[i:i + price_batch_size]
            batch_num = (i // price_batch_size) + 1
            total_batches = (total + price_batch_size - 1) // price_batch_size

            print(f"📦 Price batch {batch_num}/{total_batches} ({len(batch)} tickers)...")

            try:
                # Fetch batch historical prices (ONE API CALL for 100 tickers!)
                prices_df = historical_provider.get_batch_historical_prices(
                    batch,
                    start_date,
                    end_date,
                    is_bulk_load=False  # Use daily jitter settings
                )

                if prices_df is None or prices_df.empty:
                    print(f"   ✗ No price data returned for batch {batch_num}")
                    stats['no_data'] += len(batch)
                    continue

                # Process each ticker's prices
                for ticker_symbol in batch:
                    try:
                        # Get ticker object
                        ticker_obj = db.query(Ticker).filter(
                            Ticker.symbol == ticker_symbol
                        ).first()

                        if not ticker_obj:
                            continue

                        # Extract this ticker's data from multi-index DataFrame
                        if ticker_symbol in prices_df.columns.get_level_values(1):
                            ticker_data = prices_df.xs(ticker_symbol, level=1, axis=1)

                            # Insert/update price records
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
                                    db.merge(price_record)  # Use merge to handle duplicates
                                    stats['updated_prices'] += 1

                            # Invalidate cache
                            cache_service.delete(f"stock:{ticker_symbol}")
                            cache_service.delete(f"prices:{ticker_symbol}:historical")

                    except Exception as e:
                        print(f"   ✗ Error processing {ticker_symbol}: {e}")
                        stats['failed'] += 1
                        continue

                # Commit batch
                db.commit()
                print(f"   ✓ Batch {batch_num} complete")

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
        success_rate = ((stats['updated_fundamentals']) / total * 100) if total > 0 else 0

        print("\n" + "="*70)
        print(f"✅ BATCH UPDATE COMPLETE")
        print(f"   Duration: {duration:.1f} minutes")
        print(f"   Fundamentals updated: {stats['updated_fundamentals']}")
        print(f"   Price records added: {stats['updated_prices']}")
        print(f"   Failed: {stats['failed']}")
        print(f"   No data: {stats['no_data']}")
        print(f"   Success rate: {success_rate:.1f}%")
        print("="*70 + "\n")

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR in batch job: {e}")
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
        retention_years = settings.STOCK_HISTORY_YEARS
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
    print("   Nightly updates: 9:00 PM ET daily (active stocks only)")
    print("   Data trimming: 3:00 AM ET Sunday")
