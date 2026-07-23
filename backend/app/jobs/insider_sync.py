"""
Background job: sync SEC EDGAR Form 4 (insider) activity.

Scheduled weekdays at 18:45 ET (see registration in ``stock_loader.py``). Each
run ingests the current ET day's filings plus a catch-up re-pull of the previous
business day (EDGAR's daily index for the current day may still be filling in at
18:45, and re-pulling is idempotent). On the very first run (empty table) it
performs a ``settings.EDGAR_BACKFILL_DAYS``-day backfill instead.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from app.config import settings
from app.database.connection import SessionLocal
from app.database.models import InsiderTransaction
from app.services import edgar
from app.utils.market_calendar import get_previous_trading_day


def _et_today() -> date:
    """Current calendar date in US market time (America/New_York)."""
    return pd.Timestamp.now(tz="America/New_York").date()


def run_insider_sync(catch_up: bool = True) -> dict:
    """
    Entry point for the scheduled job.

    - Empty table -> backfill the last N days.
    - Otherwise   -> sync today (ET) and, if ``catch_up``, the previous
      business day.
    """
    db = SessionLocal()
    try:
        existing = db.query(InsiderTransaction.id).first()
        if existing is None:
            print(
                f"[insider_sync] empty table -> backfilling "
                f"{settings.EDGAR_BACKFILL_DAYS} days"
            )
            return edgar.backfill(days=settings.EDGAR_BACKFILL_DAYS, db=db)

        today = _et_today()
        client = edgar.EdgarClient()
        try:
            totals = {
                "matched_filings": 0,
                "transactions_inserted": 0,
                "filings_failed": 0,
            }
            targets = [today]
            if catch_up:
                targets.append(get_previous_trading_day(today))

            for target in targets:
                stats = edgar.sync_form4_for_date(target, db, client=client)
                totals["matched_filings"] += stats["matched_filings"]
                totals["transactions_inserted"] += stats["transactions_inserted"]
                totals["filings_failed"] += stats["filings_failed"]

            print(
                f"[insider_sync] done: {totals['transactions_inserted']} txns "
                f"inserted across {len(targets)} day(s)"
            )
            return totals
        finally:
            client.close()
    except Exception as exc:  # keep scheduler alive even on hard failure
        print(f"[insider_sync] CRITICAL error: {exc}")
        db.rollback()
        return {"error": str(exc)}
    finally:
        db.close()
