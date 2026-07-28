"""
Background job: sync SEC EDGAR Form 4 (insider) activity.

Scheduled weekdays at 22:45 ET (see registration in ``stock_loader.py``), after
EDGAR publishes the full daily index around 22:00 ET. Each run re-pulls the
last ``SYNC_TRAILING_TRADING_DAYS`` trading days rather than just today, so a
skipped or failed run heals itself on the next one; re-pulling is idempotent
(``insider_transactions`` has the unique ``uq_insider_accession_txn`` index on
(accession_no, txn_index) and ingestion uses ON CONFLICT DO NOTHING). On the
very first run (empty table) it performs a ``settings.EDGAR_BACKFILL_DAYS``-day
backfill instead.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import List

from app.config import settings
from app.database.connection import SessionLocal
from app.database.models import InsiderTransaction
from app.services import edgar
from app.utils.market_calendar import is_trading_day, today_et

# How many trailing trading days each run re-ingests. 3 covers a long weekend
# plus one missed night without meaningfully increasing EDGAR traffic (already
# ingested filings are skipped by the unique index).
SYNC_TRAILING_TRADING_DAYS = 3


def _recent_trading_days(anchor: date, count: int) -> List[date]:
    """The ``count`` most recent trading days at or before ``anchor``, newest first."""
    days: List[date] = []
    cursor = anchor
    while len(days) < count:
        if is_trading_day(cursor):
            days.append(cursor)
        cursor -= timedelta(days=1)
    return days


def run_insider_sync(catch_up: bool = True) -> dict:
    """
    Entry point for the scheduled job.

    - Empty table -> backfill the last N days.
    - Otherwise   -> re-sync the last ``SYNC_TRAILING_TRADING_DAYS`` trading
      days (or just the latest one when ``catch_up`` is False).
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

        today = today_et()
        client = edgar.EdgarClient()
        try:
            totals = {
                "matched_filings": 0,
                "transactions_inserted": 0,
                "filings_failed": 0,
            }
            targets = _recent_trading_days(
                today, SYNC_TRAILING_TRADING_DAYS if catch_up else 1
            )

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
