"""
Database initialization script.
Run this once to create all tables in PostgreSQL.

Usage:
    python init_db.py
"""

from app.database.connection import engine, Base
from app.database.models import User, Stock, StockPrice, Watchlist

def init_database():
    """Create all database tables"""
    print("🔧 Initializing database...")
    print(f"   Creating tables: users, stocks, stock_prices, watchlists")
    
    # Drop all tables (WARNING: Only use in development!)
    # Base.metadata.drop_all(bind=engine)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    print("✅ Database initialized successfully!")
    print("\n📊 Tables created:")
    print("   - users")
    print("   - stocks")
    print("   - stock_prices")
    print("   - watchlists")

if __name__ == "__main__":
    init_database()
