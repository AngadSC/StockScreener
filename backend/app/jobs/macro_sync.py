"""
Daily FRED macro observations sync job.

Upserts the last ~2 years of each configured FRED series into
`macro_observations`. Skips gracefully (logging once) if FRED_API_KEY is
not configured — this feature is fully optional/free-tier.

Registered as a cron job in app.jobs.stock_loader (06:00 ET daily).
"""
from datetime import date, datetime

from sqlalchemy.dialects.postgresql import insert

from app.config import settings
from app.database.connection import SessionLocal
from app.database.models import MacroObservation
from app.services.cache import cache_service
from app.services.fred import FRED_SERIES, build_series_for_storage

_warned_missing_key = False


def sync_macro_observations(manual_trigger: bool = False) -> None:
    global _warned_missing_key

    if not settings.FRED_API_KEY:
        if not _warned_missing_key:
            print("[macro_sync] FRED_API_KEY not configured — skipping macro sync (set it in .env to enable).")
            _warned_missing_key = True
        return

    db = SessionLocal()
    start_time = datetime.now()

    try:
        print("\n" + "=" * 70)
        print(f" {'MANUAL' if manual_trigger else 'DAILY'} FRED MACRO SYNC STARTED")
        print("=" * 70 + "\n")

        today = date.today()
        stats = {"series_updated": 0, "series_empty": 0, "series_failed": 0}

        for series_def in FRED_SERIES:
            series_id = series_def["id"]
            try:
                observations = build_series_for_storage(series_def, end_date=today)
            except Exception as e:
                print(f"   Error fetching {series_id}: {e}")
                stats["series_failed"] += 1
                continue

            if not observations:
                stats["series_empty"] += 1
                continue

            rows = [{"series_id": series_id, "date": d, "value": v} for d, v in observations]

            try:
                stmt = insert(MacroObservation).values(rows)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["series_id", "date"],
                    set_={"value": stmt.excluded.value},
                )
                db.execute(stmt)
                db.commit()
                stats["series_updated"] += 1
                print(f"   {series_id}: upserted {len(rows)} observations")
            except Exception as e:
                print(f"   Error upserting {series_id}: {e}")
                db.rollback()
                stats["series_failed"] += 1

        cache_service.delete("market:macro:v1")

        duration = (datetime.now() - start_time).total_seconds() / 60
        print(f"\nMACRO SYNC COMPLETE in {duration:.1f} mins — {stats}")

    except Exception as e:
        print(f"\nCRITICAL ERROR in macro sync job: {e}")
        db.rollback()
    finally:
        db.close()
