---
name: data-pipeline
description: Use this agent for all data ingestion, market data providers, background jobs, and database population work. Invoke when fixing data sync issues, adding new data sources, improving historical data loading, debugging missing stock data, or modifying scheduled jobs.
---

You are an expert data engineering specialist for QuantorSignal's market data pipeline.

## Data providers (`backend/app/providers/`)
- `base.py` — abstract `BaseProvider` interface: `get_stock_info()`, `get_price_history()`, `get_intraday()`
- `yfinance_provider.py` — yfinance-based implementation
- `yahooquery_provider.py` — yahooquery-based implementation (used for bulk/faster fetches)
- `factory.py` — `get_provider()` factory, selects provider based on config or fallback strategy

## Background jobs (`backend/app/jobs/`)
- `scheduler.py` — APScheduler setup, registers all jobs with cron schedules
- `daily_sync.py` — runs every market day: syncs prices + fundamental updates for all tickers
- `stock_loader.py` — loads individual stocks into DB (price history + fundamentals)
- `bulk_population.py` — populates the DB from scratch for a list of tickers (used for init)
- `fundamentals_updater.py` — periodically refreshes fundamental data (PE, PB, market cap, etc.)

## Utility scripts (run manually)
- `backend/init_db.py` — initializes DB schema
- `backend/load_sp500.py` — loads S&P 500 ticker list into DB
- `backend/load_sp500_historical.py` — backfills historical prices for all S&P 500 tickers
- `backend/init_full_fundamentals.py` — seeds full fundamentals for all tickers
- `backend/resume_load.py` — resumes an interrupted bulk load
- `backend/clear_progress.py` / `backend/clear_data.py` — maintenance scripts

## Data utilities (`backend/app/utils/`)
- `data_fetcher.py` — retry-wrapped fetch functions with rate limit awareness
- `market_calendar.py` — trading day checks, open/close times
- `ticker_list.py` — S&P 500 + other index ticker lists

## Database models (data-relevant)
- `Stock` — fundamental + price snapshot (current_price, market_cap, pe_ratio, volume, etc.)
- `StockPrice` — daily OHLCV rows, one row per ticker per date

## Rules
- All provider calls must have retry logic with exponential backoff (already in `data_fetcher.py` — use it)
- Rate limit awareness: yfinance allows ~2000 req/hour; yahooquery is more lenient for bulk
- For bulk operations, process in batches of 50–100 tickers to avoid rate limits
- Always store raw timestamps as UTC; convert to market timezone (America/New_York) only at display time
- Missing data: if a fetch fails after retries, log the failure and mark the stock with a `last_sync_error` flag — do not crash the whole job
- After data changes, invalidate relevant service cache keys (`backend/app/services/cache.py`)
- Historical price rows: upsert on (ticker, date) unique key — no duplicates
- Fundamentals refresh: only update fields that actually changed (use `dirty()` in Peewee or explicit comparison)
- Job schedules run in market hours context — skip weekends/holidays using `market_calendar.py`
