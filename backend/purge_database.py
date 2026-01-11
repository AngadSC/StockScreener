"""
Purge all stock data from database
Run this to clear everything and start fresh
"""
from app.database.connection import SessionLocal
from app.database.models import Ticker, DailyOHLCV, StockFundamental, PopulationProgress, FailedTicker, Dividend, StockSplit

db = SessionLocal()

print('🗑️  Purging all stock data...')
print()

# Delete all data (order matters due to foreign keys)
deleted_fundamentals = db.query(StockFundamental).delete()
deleted_ohlcv = db.query(DailyOHLCV).delete()
deleted_dividends = db.query(Dividend).delete()
deleted_splits = db.query(StockSplit).delete()
deleted_failed = db.query(FailedTicker).delete()
deleted_progress = db.query(PopulationProgress).delete()
deleted_tickers = db.query(Ticker).delete()

db.commit()

print(f'✓ Deleted {deleted_fundamentals} fundamentals')
print(f'✓ Deleted {deleted_ohlcv:,} OHLCV records')
print(f'✓ Deleted {deleted_dividends} dividends')
print(f'✓ Deleted {deleted_splits} stock splits')
print(f'✓ Deleted {deleted_failed} failed tickers')
print(f'✓ Deleted {deleted_progress} progress records')
print(f'✓ Deleted {deleted_tickers} tickers')
print()
print('✅ Database purged successfully!')
print()

db.close()
