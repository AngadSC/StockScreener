"""
Database initialization script.
Run this once to create all tables in PostgreSQL.

Usage:
    python init_db.py
"""

from app.database.connection import engine, Base
from app.database.models import (
    User,
    Ticker,
    DailyOHLCV,
    StockFundamental,
    StockSplit,
    Dividend,
    Watchlist,
    PopulationProgress,
    FailedTicker
)

def init_database():
    """Create all database tables"""
    print("🔧 Initializing database...")
    print(f"   Creating tables for the new optimized schema")

    # Drop all tables (WARNING: Only use in development!)
    # Base.metadata.drop_all(bind=engine)

    # Create all tables
    Base.metadata.create_all(bind=engine)

    print("✅ Database initialized successfully!")
    print("\n📊 Tables created:")
    print("   - users")
    print("   - tickers")
    print("   - daily_ohlcv")
    print("   - stock_fundamentals")
    print("   - stock_splits")
    print("   - dividends")
    print("   - watchlists")
    print("   - population_progress")
    print("   - failed_tickers")

if __name__ == "__main__":
    init_database()
