#!/usr/bin/env python3
"""
Clear bulk population progress records to allow fresh start

Run this if you get "duplicate key value violates unique constraint" errors
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.database.connection import SessionLocal
from app.database.models import PopulationProgress, FailedTicker

if __name__ == "__main__":
    db = SessionLocal()

    try:
        # Count existing records
        progress_count = db.query(PopulationProgress).count()
        failed_count = db.query(FailedTicker).count()

        print(f"Found {progress_count} progress records")
        print(f"Found {failed_count} failed ticker records")

        if progress_count == 0 and failed_count == 0:
            print("✓ No progress records to clear")
        else:
            # Delete all progress records
            db.query(PopulationProgress).delete()
            db.query(FailedTicker).delete()
            db.commit()

            print(f"✓ Cleared {progress_count} progress records")
            print(f"✓ Cleared {failed_count} failed ticker records")
            print("\nYou can now run bulk population again")

    except Exception as e:
        print(f"✗ Error: {e}")
        db.rollback()
    finally:
        db.close()
