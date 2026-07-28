"""
Nightly earnings calendar sync job.

Fetches upcoming earnings dates (via yahooquery, batched) for the scoped
ticker universe (watchlisted + top-500 by market cap), upserts them into
`earnings_events`, and removes stale future-dated rows whose estimate moved.

Registered as a cron job in app.jobs.stock_loader (23:15 ET nightly).
"""
from datetime import datetime

from sqlalchemy.dialects.postgresql import insert

from app.database.connection import SessionLocal
from app.database.models import EarningsEvent, Ticker
from app.services.cache import cache_service
from app.services.earnings import (
    chunk_symbols,
    fetch_calendar_events_batch,
    get_earnings_scope_tickers,
    parse_calendar_event,
)
from app.utils.market_calendar import today_et


def sync_earnings_events(manual_trigger: bool = False) -> None:
    db = SessionLocal()
    start_time = datetime.now()

    try:
        print("\n" + "=" * 70)
        print(f" {'MANUAL' if manual_trigger else 'NIGHTLY'} EARNINGS CALENDAR SYNC STARTED")
        print("=" * 70 + "\n")

        symbols = get_earnings_scope_tickers(db)
        if not symbols:
            print("No tickers in earnings scope (no watchlists yet, no fundamentals yet). Skipping.")
            return

        print(f"Scope: {len(symbols)} tickers (watchlisted + top market cap)")

        ticker_map = {
            t.symbol: t.id
            for t in db.query(Ticker).filter(Ticker.symbol.in_(symbols)).all()
        }

        # ET date, not the host date: this job runs at 23:15 ET, which is
        # already the next day in UTC — a naive date would spare stale rows
        # dated "today" from the cleanup below.
        today = today_et()
        stats = {"upserted": 0, "no_data": 0, "failed_batches": 0}

        batches = chunk_symbols(symbols)
        for batch_num, batch in enumerate(batches, start=1):
            print(f"Batch {batch_num}/{len(batches)} ({len(batch)} tickers)...")
            try:
                events_by_symbol = fetch_calendar_events_batch(batch)
            except Exception as e:
                print(f"   Batch {batch_num} failed: {e}")
                stats["failed_batches"] += 1
                continue

            for symbol in batch:
                ticker_id = ticker_map.get(symbol)
                if not ticker_id:
                    continue

                parsed = parse_calendar_event(events_by_symbol.get(symbol))
                if not parsed:
                    stats["no_data"] += 1
                    continue

                try:
                    stmt = insert(EarningsEvent).values(
                        ticker_id=ticker_id,
                        earnings_date=parsed["earnings_date"],
                        time_hint=parsed["time_hint"],
                        eps_estimate=parsed["eps_estimate"],
                        fetched_at=datetime.utcnow(),
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["ticker_id", "earnings_date"],
                        set_={
                            "time_hint": stmt.excluded.time_hint,
                            "eps_estimate": stmt.excluded.eps_estimate,
                            "fetched_at": stmt.excluded.fetched_at,
                        },
                    )
                    db.execute(stmt)

                    # Remove stale future estimates for this ticker whose date moved.
                    db.query(EarningsEvent).filter(
                        EarningsEvent.ticker_id == ticker_id,
                        EarningsEvent.earnings_date >= today,
                        EarningsEvent.earnings_date != parsed["earnings_date"],
                    ).delete(synchronize_session=False)

                    stats["upserted"] += 1
                except Exception as e:
                    print(f"   Error upserting {symbol}: {e}")
                    db.rollback()
                    continue

            db.commit()

        cache_service.clear_pattern("market:earnings:*")

        duration = (datetime.now() - start_time).total_seconds() / 60
        print(f"\nEARNINGS SYNC COMPLETE in {duration:.1f} mins — {stats}")

    except Exception as e:
        print(f"\nCRITICAL ERROR in earnings sync job: {e}")
        db.rollback()
    finally:
        db.close()
