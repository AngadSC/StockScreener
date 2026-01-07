#!/usr/bin/env python3
"""
Startup script: Run bulk population if needed, then start API server

This script:
1. Checks if database has been populated (< 100 tickers = empty)
2. Runs bulk population if database is empty (~2-3 hours)
3. Starts the FastAPI server

Usage:
    python3 run_once_then_serve.py

For Railway deployment, set start command to:
    cd backend && python3 run_once_then_serve.py
"""
import os
import sys
import subprocess

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from app.database.connection import SessionLocal
from app.database.models import Ticker

def should_populate():
    """
    Check if database needs population

    Returns:
        True if database has fewer than 100 tickers (empty/incomplete)
        False if database already has stocks
    """
    try:
        print("🔍 Checking database status...")
        db = SessionLocal()
        ticker_count = db.query(Ticker).count()
        db.close()

        print(f"   Database currently has {ticker_count} tickers")

        # If less than 100 tickers, database is empty or incomplete
        if ticker_count < 1000:
            print("   ⚠️  Database is empty or incomplete (< 100 tickers)")
            return True
        else:
            print(f"   ✓ Database already populated with {ticker_count} tickers")
            return False

    except Exception as e:
        print(f"   ⚠️  Error checking database: {e}")
        print(f"   Assuming database is empty, will attempt population")
        return True

def run_bulk_population():
    """Run the bulk population job"""
    print("\n" + "="*80)
    print("🚀 STARTING BULK POPULATION")
    print("   This will take approximately 2-3 hours")
    print("   Progress will be shown below")
    print("="*80 + "\n")

    try:
        from app.jobs.bulk_population import populate_all_stocks
        stats = populate_all_stocks(resume=True)

        print("\n" + "="*80)
        print("✅ BULK POPULATION COMPLETE")
        print(f"   Total tickers: {stats.get('total_tickers', 'N/A')}")
        print(f"   Completed batches: {stats.get('completed_batches', 'N/A')}")
        print(f"   Failed batches: {stats.get('failed_batches', 'N/A')}")
        print(f"   Records inserted: {stats.get('records_inserted', 'N/A'):,}")
        print(f"   Duration: {stats.get('duration_minutes', 0):.1f} minutes")
        print("="*80 + "\n")

        return True

    except Exception as e:
        print("\n" + "="*80)
        print("❌ BULK POPULATION FAILED")
        print(f"   Error: {e}")
        print("="*80 + "\n")
        print("⚠️  Starting API server anyway...")
        print("   You can manually run bulk population later")
        return False

def start_api_server():
    """Start the FastAPI server"""
    print("\n" + "="*80)
    print("🌐 STARTING API SERVER")
    print("="*80 + "\n")

    # Get port from environment or default to 8000
    port = os.getenv("PORT", "8000")

    # Start uvicorn
    # Using os.execvp to replace current process (no subprocess)
    os.execvp("uvicorn", [
        "uvicorn",
        "app.main:app",
        "--host", "0.0.0.0",
        "--port", port
    ])

if __name__ == "__main__":
    print("\n" + "="*80)
    print("🎯 STOCKSCREENER STARTUP SEQUENCE")
    print("="*80 + "\n")

    # Step 1: Check if we need to populate
    if should_populate():
        # Step 2: Run bulk population
        run_bulk_population()
    else:
        print("✓ Skipping bulk population (database already has data)\n")

    # Step 3: Start API server (this never returns)
    start_api_server()
