import sys
import os

# Ensure the backend directory is in the path
sys.path.insert(0, os.path.dirname(__file__))

from app.database.connection import SessionLocal
from app.database.models import (
    Ticker, DailyOHLCV, StockFundamental, 
    StockSplit, Dividend, PopulationProgress, FailedTicker
)

def clear_all_data():
    db = SessionLocal()
    try:
        print("🧹 Clearing data from tables (keeping schema)...")
        
        # Order matters because of Foreign Key constraints
        # Delete from child tables first
        db.query(DailyOHLCV).delete()
        db.query(StockFundamental).delete()
        db.query(StockSplit).delete()
        db.query(Dividend).delete()
        db.query(PopulationProgress).delete()
        db.query(FailedTicker).delete()
        
        # Finally delete from parent table
        db.query(Ticker).delete()
        
        db.commit()
        print("✅ All data cleared successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error clearing data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    clear_all_data()