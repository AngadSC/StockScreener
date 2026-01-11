import sys
import os
from sqlalchemy import text

# Ensure the backend directory is in the path
sys.path.insert(0, os.path.dirname(__file__))

from app.database.connection import SessionLocal

def clear_all_data():
    db = SessionLocal()
    try:
        print("🧹 Truncating tables (instant wipe, keeping schema)...")
        
        # Use TRUNCATE with CASCADE to handle foreign keys and reset IDs
        # This is much faster than DELETE and won't time out
        truncate_query = text("""
            TRUNCATE TABLE 
                daily_ohlcv, 
                stock_fundamentals, 
                stock_splits, 
                dividends, 
                population_progress, 
                failed_tickers, 
                tickers 
            RESTART IDENTITY CASCADE;
        """)
        
        db.execute(truncate_query)
        db.commit()
        print("✅ Database cleared successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error clearing data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    clear_all_data()