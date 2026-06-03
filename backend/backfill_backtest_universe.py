from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from typing import Iterable

import pandas as pd
from sqlalchemy.dialects.postgresql import insert

from app.database.connection import SessionLocal
from app.database.models import DailyOHLCV, Ticker
from app.providers.factory import ProviderFactory
from app.routes.stocks import SECTOR_ETF_UNIVERSE
from app.services.cache import cache_service
from app.utils.market_calendar import get_trading_days_between
from app.utils.ticker_list import get_sp500_tickers


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _chunks(values: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]


def _resolve_symbols(universe: str, symbols_arg: str | None) -> list[str]:
    if symbols_arg:
        raw_symbols = symbols_arg.split(",")
    elif universe == "sp500":
        raw_symbols = get_sp500_tickers()
    elif universe == "sector_etfs":
        raw_symbols = SECTOR_ETF_UNIVERSE
    else:
        raise ValueError(f"Unsupported universe '{universe}'.")

    symbols: list[str] = []
    seen: set[str] = set()
    for raw_symbol in raw_symbols:
        symbol = str(raw_symbol).strip().upper()
        if symbol and symbol not in seen:
            symbols.append(symbol)
            seen.add(symbol)
    return symbols


def _coverage_by_symbol(db, symbols: list[str], start_date: date, end_date: date) -> dict[str, int]:
    rows = (
        db.query(Ticker.symbol, DailyOHLCV.date)
        .join(DailyOHLCV, DailyOHLCV.ticker_id == Ticker.id)
        .filter(
            Ticker.symbol.in_(symbols),
            DailyOHLCV.date >= start_date,
            DailyOHLCV.date <= end_date,
        )
        .all()
    )
    expected = set(get_trading_days_between(start_date, end_date))
    covered: dict[str, set[date]] = {symbol: set() for symbol in symbols}
    for symbol, row_date in rows:
        normalized = str(symbol).upper()
        if normalized in covered and row_date in expected:
            covered[normalized].add(row_date)
    return {symbol: len(days) for symbol, days in covered.items()}


def _symbols_needing_backfill(
    db,
    symbols: list[str],
    start_date: date,
    end_date: date,
    *,
    min_bars: int,
    min_coverage_ratio: float,
) -> tuple[list[str], int]:
    expected_count = len(get_trading_days_between(start_date, end_date))
    coverage = _coverage_by_symbol(db, symbols, start_date, end_date)
    minimum_covered_days = int(expected_count * min_coverage_ratio)
    required_rows = max(min_bars, minimum_covered_days)
    needed = [symbol for symbol in symbols if coverage.get(symbol, 0) < required_rows]
    return needed, expected_count


def _ensure_tickers(db, symbols: list[str]) -> None:
    existing = {
        symbol
        for (symbol,) in db.query(Ticker.symbol).filter(Ticker.symbol.in_(symbols)).all()
    }
    missing = [symbol for symbol in symbols if symbol not in existing]
    for symbol in missing:
        db.add(Ticker(symbol=symbol))
    if missing:
        db.commit()


def _upsert_prices(db, prices: pd.DataFrame) -> int:
    if prices is None or prices.empty:
        return 0

    symbols = sorted({str(symbol).upper() for symbol in prices["ticker"].dropna().unique().tolist()})
    ticker_map = {
        symbol: ticker_id
        for symbol, ticker_id in db.query(Ticker.symbol, Ticker.id).filter(Ticker.symbol.in_(symbols)).all()
    }
    rows_to_upsert: list[dict[str, object]] = []
    for _, row in prices.iterrows():
        symbol = str(row["ticker"]).upper()
        ticker_id = ticker_map.get(symbol)
        if not ticker_id or pd.isna(row.get("Close")):
            continue
        row_date = row["date"]
        if hasattr(row_date, "date"):
            row_date = row_date.date()
        rows_to_upsert.append(
            {
                "ticker_id": ticker_id,
                "date": row_date,
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row.get("Volume") or 0),
            }
        )

    if not rows_to_upsert:
        return 0

    stmt = insert(DailyOHLCV).values(rows_to_upsert)
    stmt = stmt.on_conflict_do_update(
        index_elements=["ticker_id", "date"],
        set_={col: getattr(stmt.excluded, col) for col in ["open", "high", "low", "close", "volume"]},
    )
    db.execute(stmt)
    db.commit()
    return len(rows_to_upsert)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill DB OHLCV for DB-only backtest universes.")
    parser.add_argument("--universe", choices=["sp500", "sector_etfs"], default="sp500")
    parser.add_argument("--symbols", help="Comma-separated symbols to backfill instead of resolving a universe.")
    parser.add_argument("--start", required=True, help="Inclusive start date, YYYY-MM-DD.")
    parser.add_argument("--end", required=True, help="Inclusive end date, YYYY-MM-DD.")
    parser.add_argument("--min-bars", type=int, default=272)
    parser.add_argument("--coverage", type=float, default=0.90)
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    start_date = _parse_date(args.start)
    end_date = _parse_date(args.end)
    symbols = _resolve_symbols(args.universe, args.symbols)
    if not symbols:
        raise SystemExit("No symbols resolved for backfill.")

    db = SessionLocal()
    try:
        _ensure_tickers(db, symbols)
        needed, expected_count = _symbols_needing_backfill(
            db,
            symbols,
            start_date,
            end_date,
            min_bars=args.min_bars,
            min_coverage_ratio=args.coverage,
        )
        print(
            f"{args.universe}: {len(needed)}/{len(symbols)} symbols need backfill "
            f"for {expected_count} requested trading days."
        )
        if needed:
            print("Symbols:", ", ".join(needed))
        if args.dry_run or not needed:
            return

        provider = ProviderFactory.get_historical_provider()
        fetch_end = end_date + timedelta(days=1)
        total_rows = 0
        for batch_number, batch in enumerate(_chunks(needed, max(1, args.batch_size)), start=1):
            print(f"Fetching batch {batch_number}: {', '.join(batch)}")
            prices = provider.get_batch_historical_prices(batch, start_date, fetch_end, is_bulk_load=True)
            inserted = _upsert_prices(db, prices)
            total_rows += inserted
            print(f"Upserted {inserted} OHLCV rows.")

        cache_service.clear_pattern("backtest_run:v5:*")
        for symbol in needed:
            cache_service.delete(f"prices:{symbol}:detailed")
        print(f"Done. Upserted {total_rows} OHLCV rows and cleared backtest caches.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
