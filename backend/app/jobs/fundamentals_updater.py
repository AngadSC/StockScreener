from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.database.models import Ticker, StockFundamental
from app.providers.factory import ProviderFactory
from app.services.cache import cache_service
from datetime import datetime, timedelta
from typing import Dict, Any
import json

# ============================================
# FUNDAMENTALS UPDATER JOB
# Updates fundamental data for 1/7th of stocks daily
# Full refresh cycle = 7 days
# ============================================

def update_fundamentals_daily():
    """
    Daily job: Update fundamentals for 1/7th of all stocks
    Cycles through entire database over 7 days
    """
    db = SessionLocal()
    start_time = datetime.now()
    
    stats = {
        'total_tickers': 0,
        'segment_size': 0,
        'updated': 0,
        'failed': 0,
        'skipped': 0
    }
    
    try:
        print("\n" + "="*70)
        print(f"📊 FUNDAMENTALS UPDATE STARTED")
        print(f"   Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70 + "\n")
        
        # Determine which day of cycle (0-6)
        day_of_week = datetime.now().weekday()  # Monday=0, Sunday=6
        
        # Get all tickers
        all_tickers = db.query(Ticker).order_by(Ticker.id).all()
        total_count = len(all_tickers)
        stats['total_tickers'] = total_count
        
        if total_count == 0:
            print("⚠️  No tickers in database")
            return stats
        
        # Calculate segment for today
        segment_size = total_count // 7
        start_idx = day_of_week * segment_size
        
        # Last day gets remainder
        if day_of_week == 6:
            end_idx = total_count
        else:
            end_idx = start_idx + segment_size
        
        today_tickers = all_tickers[start_idx:end_idx]
        stats['segment_size'] = len(today_tickers)
        
        print(f"📅 Day {day_of_week + 1}/7 of update cycle")
        print(f"   Total tickers in DB: {total_count}")
        print(f"   Today's segment: {stats['segment_size']} tickers")
        print(f"   Index range: {start_idx} to {end_idx}")
        print()
        
        # Get provider
        provider = ProviderFactory.get_fundamentals_provider()
        print(f"✓ Using provider: {provider.name}\n")
        
        # Batch tickers for efficient fetching
        batch_size = 50  # yahooquery can handle 50 at once
        ticker_symbols = [t.symbol for t in today_tickers]
        batches = [ticker_symbols[i:i+batch_size] for i in range(0, len(ticker_symbols), batch_size)]
        
        print(f"📦 Processing {len(batches)} batches...\n")
        
        # Process each batch
        for batch_num, batch in enumerate(batches, 1):
            try:
                print(f"   Batch {batch_num}/{len(batches)} ({len(batch)} tickers)...", end=" ")
                
                # Fetch batch fundamentals
                fundamentals_data = provider.get_batch_fundamentals(batch)
                
                if not fundamentals_data:
                    print("✗ No data")
                    stats['failed'] += len(batch)
                    continue
                
                # Update each ticker
                updated_count = 0
                for ticker_symbol, fund_data in fundamentals_data.items():
                    ticker_obj = db.query(Ticker).filter(Ticker.symbol == ticker_symbol).first()
                    if not ticker_obj:
                        continue
                    
                    # Upsert fundamentals
                    _upsert_fundamentals(db, ticker_obj.id, fund_data)
                    updated_count += 1
                    
                    # Invalidate cache
                    cache_service.delete(f"stock:{ticker_symbol}")
                
                stats['updated'] += updated_count
                print(f"✓ {updated_count} updated")
                
            except Exception as e:
                print(f"✗ Failed: {e}")
                stats['failed'] += len(batch)
                db.rollback()
                continue
        
        # Clear screener caches (fundamentals changed)
        print("\n🗑️  Clearing screener caches...")
        cache_service.clear_pattern("screener:*")
        
        # Final report
        end_time = datetime.now()
        duration = (end_time - start_time).seconds / 60
        
        print("\n" + "="*70)
        print(f"✅ FUNDAMENTALS UPDATE COMPLETE")
        print(f"   Duration: {duration:.1f} minutes")
        print(f"   Updated: {stats['updated']}/{stats['segment_size']}")
        print(f"   Failed: {stats['failed']}")
        print(f"   Next segment: Day {(day_of_week + 1) % 7 + 1}/7")
        print("="*70 + "\n")
        
        return stats
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        db.rollback()
        return stats
        
    finally:
        db.close()


def _upsert_fundamentals(db: Session, ticker_id: int, fund_data: Dict[str, Any]):
    """
    Upsert fundamental data for a ticker
    
    Args:
        db: Database session
        ticker_id: Ticker ID
        fund_data: Fundamental data dict
    """
    # Check if record exists
    fundamental = db.query(StockFundamental).filter(
        StockFundamental.ticker_id == ticker_id
    ).first()
    
    if not fundamental:
        fundamental = StockFundamental(ticker_id=ticker_id)
        db.add(fundamental)
    
    # Update all fields
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
    
    fundamental.market_cap = fund_data.get('market_cap')
    fundamental.volume = fund_data.get('volume')
    fundamental.avg_volume = fund_data.get('avg_volume')
    fundamental.beta = fund_data.get('beta')
    
    fundamental.current_price = fund_data.get('current_price')
    fundamental.day_change_percent = fund_data.get('day_change_percent')
    fundamental.fifty_two_week_high = fund_data.get('fifty_two_week_high')
    fundamental.fifty_two_week_low = fund_data.get('fifty_two_week_low')
    
    fundamental.sector = fund_data.get('sector')
    fundamental.industry = fund_data.get('industry')
    
    # Store everything else in JSONB
    fundamental.additional_data = fund_data.get('additional_data', {})
    
    fundamental.last_updated = datetime.now()
    
    db.commit()


def update_single_ticker_fundamentals(ticker_symbol: str) -> bool:
    """
    Update fundamentals for a single ticker (on-demand)
    
    Args:
        ticker_symbol: Stock ticker
    
    Returns:
        True if successful, False otherwise
    """
    db = SessionLocal()
    
    try:
        # Get ticker
        ticker = db.query(Ticker).filter(Ticker.symbol == ticker_symbol.upper()).first()
        if not ticker:
            print(f"✗ Ticker {ticker_symbol} not found in database")
            return False
        
        # Get provider
        provider = ProviderFactory.get_fundamentals_provider()
        
        # Fetch fundamentals
        fund_data = provider.get_fundamentals(ticker_symbol)
        
        if not fund_data:
            print(f"✗ No fundamental data for {ticker_symbol}")
            return False
        
        # Upsert
        _upsert_fundamentals(db, ticker.id, fund_data)
        
        # Clear cache
        cache_service.delete(f"stock:{ticker_symbol}")
        
        print(f"✓ Updated fundamentals for {ticker_symbol}")
        return True
        
    except Exception as e:
        print(f"✗ Error updating {ticker_symbol}: {e}")
        db.rollback()
        return False
        
    finally:
        db.close()
