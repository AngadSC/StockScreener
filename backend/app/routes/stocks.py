import hashlib
import json
from datetime import datetime, timedelta

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.backtests.data import load_backtest_market_data, load_backtest_market_data_batch_db_only
from app.backtests.indicator_lab import run_indicator_backtest
from app.backtests.portfolio import _resample_market_data, estimate_strategy_min_bars, run_portfolio_backtest
from app.database.connection import get_db
from app.database.models import StockFundamental, Ticker
from app.models.stock import (
    BacktestDataResponse,
    IndicatorBacktestRunRequest,
    IndicatorBacktestRunResponse,
    BacktestRunRequest,
    BacktestRunResponse,
    MLFeaturesResponse,
    StockDetail,
)
from app.providers.factory import ProviderFactory
from app.services.cache import cache_service
from app.services.stock_service import get_price_history, get_stock_with_fundamentals
from app.utils.data_fetcher import add_technical_indicators
from app.utils.ticker_list import get_sp500_tickers


router = APIRouter(prefix="/stocks", tags=["stocks"])
backtests_router = APIRouter(prefix="/backtests", tags=["backtests"])

SECTOR_ETF_UNIVERSE = [
    "XLB",
    "XLC",
    "XLE",
    "XLF",
    "XLI",
    "XLK",
    "XLP",
    "XLRE",
    "XLU",
    "XLV",
    "XLY",
]

DB_ONLY_BACKTEST_UNIVERSES = {"sp500", "sector_etfs"}
LARGE_UNIVERSE_PLOT_SYMBOL_LIMIT = 50
SP500_MAX_BACKTEST_DAYS = 1830


def _parse_and_validate_date_range(start_date: str, end_date: str, max_days: int) -> tuple:
    """Parse YYYY-MM-DD date strings and enforce sane request bounds."""
    try:
        from datetime import datetime as dt

        start = dt.strptime(start_date, "%Y-%m-%d").date()
        end = dt.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    if start > end:
        raise HTTPException(status_code=400, detail="start_date must be before or equal to end_date.")

    if (end - start).days > max_days:
        raise HTTPException(status_code=400, detail=f"Date range too large. Maximum is {max_days} days.")

    today = datetime.now().date()
    if end > today:
        raise HTTPException(status_code=400, detail="end_date cannot be in the future.")

    return start, end


def _normalize_backtest_tickers(
    primary_ticker: str | None,
    extra_tickers: list[str],
    *,
    enforce_limit: bool = True,
) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for raw in ([primary_ticker] if primary_ticker else []) + list(extra_tickers or []):
        ticker = str(raw).strip().upper()
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        ordered.append(ticker)

    if not ordered:
        raise HTTPException(status_code=400, detail="Provide at least one ticker for the backtest.")

    if enforce_limit and len(ordered) > 25:
        raise HTTPException(status_code=400, detail="Backtest basket is limited to 25 tickers per run.")

    return ordered


def _resolve_automated_universe(primary_ticker: str | None, request: BacktestRunRequest) -> tuple[str, list[str], list[str]]:
    warnings: list[str] = []
    universe = request.universe
    if request.strategy.family == "sector_rotation_momentum" and universe == "custom" and not request.tickers:
        universe = "sector_etfs"

    if universe == "sp500":
        cached = cache_service.get("backtest_universe:sp500:v1")
        tickers = cached if isinstance(cached, list) else None
        if not tickers:
            tickers = get_sp500_tickers()
            if tickers:
                cache_service.set("backtest_universe:sp500:v1", tickers, ttl=24 * 3600)
        tickers = _normalize_backtest_tickers(None, tickers or [], enforce_limit=False)
        if "SPY" in tickers and len(tickers) == 1:
            raise HTTPException(status_code=400, detail="S&P 500 universe resolved only to SPY, which is not valid.")
        return "sp500", tickers, warnings

    if universe == "sector_etfs":
        return "sector_etfs", _normalize_backtest_tickers(None, SECTOR_ETF_UNIVERSE, enforce_limit=False), warnings

    return "custom", _normalize_backtest_tickers(primary_ticker, request.tickers, enforce_limit=True), warnings


def _load_rank_metadata(db: Session, tickers: list[str], warnings: list[str]) -> dict[str, dict[str, float | None]]:
    rows = (
        db.query(Ticker.symbol, StockFundamental.market_cap, StockFundamental.avg_volume, StockFundamental.volume)
        .join(StockFundamental, Ticker.id == StockFundamental.ticker_id)
        .filter(Ticker.symbol.in_(tickers))
        .all()
    )
    metadata = {
        symbol.upper(): {
            "market_cap": market_cap,
            "avg_volume": avg_volume,
            "volume": volume,
        }
        for symbol, market_cap, avg_volume, volume in rows
    }
    if tickers and not any((item.get("market_cap") or 0) > 0 for item in metadata.values()):
        warnings.append("Leaders ranking used dollar volume fallback because market-cap fundamentals were unavailable.")
    return metadata


def _normalize_backtest_weights(tickers: list[str], allocation_weights: dict[str, float]) -> dict[str, float]:
    if not allocation_weights:
        return {}

    normalized: dict[str, float] = {}
    ticker_set = set(tickers)
    for raw_ticker, raw_weight in allocation_weights.items():
        ticker = str(raw_ticker).strip().upper()
        if ticker not in ticker_set:
            raise HTTPException(status_code=400, detail=f"Allocation weight provided for unknown ticker '{ticker}'.")
        try:
            weight = float(raw_weight)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail=f"Allocation weight for '{ticker}' must be numeric.")
        normalized[ticker] = weight
    return normalized


def _params_for_min_history(request: BacktestRunRequest) -> dict[str, object]:
    params: dict[str, object] = dict(request.strategy.params or {})
    if not request.tuning or not request.tuning.enabled:
        return params

    for key, config in request.tuning.parameter_ranges.items():
        candidates = list(config.values or [])
        if config.max is not None:
            candidates.append(config.max)
        if candidates:
            params[key] = max(candidates)
    return params


def _run_backtest_request(
    primary_ticker: str | None,
    request: BacktestRunRequest,
    db: Session,
):
    if request.mode != "automated":
        raise HTTPException(status_code=400, detail="Use /backtests/indicator/run for indicator strategy backtests.")

    resolved_universe, tickers, warnings = _resolve_automated_universe(primary_ticker, request)
    anchor_ticker = (primary_ticker or tickers[0]).upper()
    allocation_weights = _normalize_backtest_weights(tickers, request.allocation_weights if resolved_universe == "custom" else {})

    max_days = SP500_MAX_BACKTEST_DAYS if resolved_universe == "sp500" else 3650
    start, end = _parse_and_validate_date_range(request.start_date, request.end_date, max_days=max_days)
    min_required_bars = estimate_strategy_min_bars(
        request.strategy.family,
        _params_for_min_history(request),
        request.timeframe,
    )
    generate_plots = request.generate_plots
    if generate_plots and (resolved_universe == "sp500" or len(tickers) > LARGE_UNIVERSE_PLOT_SYMBOL_LIMIT):
        generate_plots = False
        warnings.append("Server-side plot image disabled for large universe run; frontend chart uses equity curve data.")

    request_dump = request.model_dump(mode="json")
    request_dump["universe"] = resolved_universe
    request_dump["tickers"] = tickers
    request_dump["allocation_weights"] = allocation_weights
    request_dump["effective_generate_plots"] = generate_plots
    request_dump["min_required_bars"] = min_required_bars
    cache_suffix = hashlib.sha256(json.dumps(request_dump, sort_keys=True).encode("utf-8")).hexdigest()
    cache_key = f"backtest_run:v5:{anchor_ticker}:{cache_suffix}"

    cached = cache_service.get(cache_key)
    if cached:
        return {
            **cached,
            "cached": True,
        }

    try:
        market_data: dict[str, pd.DataFrame] = {}
        data_sources: dict[str, str] = {}
        if resolved_universe in DB_ONLY_BACKTEST_UNIVERSES:
            market_data, data_sources, loader_warnings = load_backtest_market_data_batch_db_only(
                db,
                tickers,
                start,
                end,
                min_required_bars=min_required_bars,
            )
            warnings.extend(loader_warnings)
        else:
            for symbol in tickers:
                try:
                    symbol_data, source, symbol_warnings = load_backtest_market_data(
                        db,
                        symbol,
                        start,
                        end,
                        min_required_bars=min_required_bars,
                    )
                    market_data[symbol] = symbol_data
                    data_sources[symbol] = source
                    warnings.extend([f"{symbol}: {warning}" for warning in symbol_warnings])
                except ValueError as exc:
                    warnings.append(f"{symbol}: {exc}")
                    continue

        if not market_data:
            raise ValueError("No historical data was available for any ticker in the selected universe.")

        available_tickers = [symbol for symbol in tickers if symbol in market_data]
        if resolved_universe in DB_ONLY_BACKTEST_UNIVERSES:
            warnings.append(
                f"{resolved_universe} DB-only run used {len(available_tickers)} of {len(tickers)} resolved symbols."
            )
        if request.generate_plots and generate_plots and len(available_tickers) > LARGE_UNIVERSE_PLOT_SYMBOL_LIMIT:
            generate_plots = False
            warnings.append("Server-side plot image disabled for large universe run; frontend chart uses equity curve data.")
        rank_metadata = (
            _load_rank_metadata(db, available_tickers, warnings)
            if request.strategy.family == "leaders_carry_everything"
            else None
        )

        result = run_portfolio_backtest(
            market_data,
            tickers=available_tickers,
            allocation_weights=allocation_weights,
            timeframe=request.timeframe,
            initial_capital=request.initial_capital,
            tc_bps=request.tc_bps,
            allow_fractional_shares=request.allow_fractional_shares,
            family=request.strategy.family,
            strategy_params=request.strategy.params,
            risk_controls=request.risk_controls.model_dump(exclude_none=True) if request.risk_controls else None,
            tuning=request.tuning.model_dump(mode="json") if request.tuning else None,
            include_buy_and_hold=request.include_buy_and_hold,
            generate_plots=generate_plots,
            rank_metadata=rank_metadata,
        )
        overall_source = next(iter(data_sources.values())) if len(set(data_sources.values())) == 1 else "mixed"
        response = {
            "ticker": anchor_ticker,
            "tickers": available_tickers,
            "mode": "automated",
            "universe": resolved_universe,
            "allocation_weights": result["allocation_weights"],
            "cash_reserve_pct": result["cash_reserve_pct"],
            "source": overall_source,
            "data_sources": data_sources,
            "cached": False,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "timeframe": request.timeframe,
            "strategy_family": request.strategy.family,
            "strategy_params": result["strategy_params"],
            "risk_controls": request.risk_controls.model_dump(exclude_none=True) if request.risk_controls else {},
            "warnings": warnings,
            "stats": result["stats"],
            "equity_curve": result["equity_curve"],
            "buy_and_hold": result["buy_and_hold"],
            "trade_log": result["trade_log"],
            "selected_holdings": result["selected_holdings"],
            "current_holdings": result["current_holdings"],
            "tuning_summary": result["tuning_summary"],
            "equity_curve_image": result["equity_curve_image"],
        }
        cache_service.set(cache_key, response, ttl=3600)
        return response
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        anchor = anchor_ticker if primary_ticker else ",".join(tickers)
        print(f"Backtest run error for {anchor}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to run backtest")


@router.get("/{ticker}", response_model=StockDetail)
def get_stock_detail(ticker: str, db: Session = Depends(get_db)):
    """Get detailed stock information including fundamentals."""
    ticker = ticker.upper()
    stock_data = get_stock_with_fundamentals(db, ticker, use_cache=True)

    if not stock_data:
        raise HTTPException(
            status_code=404,
            detail=f"Stock {ticker} not found. Try the screener to find valid tickers.",
        )

    return StockDetail(**stock_data)


@router.get("/{ticker}/prices")
def get_stock_prices(
    ticker: str,
    period: str = Query("1y", regex="^(1mo|3mo|6mo|1y)$", description="Time period"),
    db: Session = Depends(get_db),
):
    """Get historical price data for a stock."""
    ticker = ticker.upper()
    cache_key = f"prices:{ticker}:{period}"

    cached = cache_service.get(cache_key)
    if cached:
        return cached

    period_map = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365}
    days = period_map[period]
    start_date = datetime.now().date() - timedelta(days=days)
    end_date = datetime.now().date()

    df = get_price_history(db, ticker, start_date, end_date, use_cache=False)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No price data found for {ticker}")

    df_reset = df.reset_index()
    result = {
        "ticker": ticker,
        "period": period,
        "data_points": len(df_reset),
        "data": [
            {
                "date": row["date"].isoformat() if hasattr(row["date"], "isoformat") else str(row["date"]),
                "open": row["Open"],
                "high": row["High"],
                "low": row["Low"],
                "close": row["Close"],
                "volume": row["Volume"],
            }
            for _, row in df_reset.iterrows()
        ],
    }

    cache_service.set(cache_key, result, ttl=3600)
    return result


@router.post("/{ticker}/backtest-data", response_model=BacktestDataResponse)
def get_backtest_data(
    ticker: str,
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)", regex=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)", regex=r"^\d{4}-\d{2}-\d{2}$"),
    include_indicators: bool = Query(True, description="Include technical indicators"),
    db: Session = Depends(get_db),
):
    """
    Fetch extended historical data for backtesting.

    Reads PostgreSQL first and falls back to yfinance when needed.
    """
    ticker = ticker.upper()
    cache_key = f"backtest:{ticker}:{start_date}:{end_date}:{include_indicators}"

    cached = cache_service.get(cache_key)
    if cached:
        return {
            "ticker": ticker,
            "cached": True,
            **cached,
        }

    ticker_obj = db.query(Ticker).filter(Ticker.symbol == ticker).first()
    if not ticker_obj:
        raise HTTPException(status_code=404, detail=f"Stock {ticker} not found in database")

    try:
        start, end = _parse_and_validate_date_range(start_date, end_date, max_days=3650)
        df, source, _warnings = load_backtest_market_data(db, ticker, start, end)

        if include_indicators:
            df = add_technical_indicators(df)

        df_reset = df.reset_index()
        if "Date" not in df_reset.columns:
            df_reset = df_reset.rename(columns={df_reset.columns[0]: "Date"})
        df_reset["Date"] = df_reset["Date"].astype(str)

        result = {
            "source": source,
            "start_date": start_date,
            "end_date": end_date,
            "data_points": len(df_reset),
            "indicators_included": include_indicators,
            "columns": list(df.columns),
            "data": df_reset.to_dict(orient="records"),
        }
        cache_service.set(cache_key, result, ttl=7200)
        return {"ticker": ticker, "cached": False, **result}
    except HTTPException:
        raise
    except Exception as exc:
        print(f"Backtest data fetch error for {ticker}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to fetch backtest data")


@router.post("/{ticker}/backtest", response_model=BacktestRunResponse)
def run_backtest(
    ticker: str,
    request: BacktestRunRequest,
    db: Session = Depends(get_db),
):
    """Run a portfolio backtest across one or more tickers."""
    return _run_backtest_request(ticker.upper(), request, db)


@backtests_router.post("/run", response_model=BacktestRunResponse)
def run_global_backtest(
    request: BacktestRunRequest,
    db: Session = Depends(get_db),
):
    """Run a ticker-agnostic portfolio backtest."""
    return _run_backtest_request(None, request, db)


@backtests_router.post("/indicator/run", response_model=IndicatorBacktestRunResponse)
def run_global_indicator_backtest(
    request: IndicatorBacktestRunRequest,
    db: Session = Depends(get_db),
):
    """Run a single-symbol indicator-lab backtest."""
    ticker = request.ticker.strip().upper()
    if not ticker:
        raise HTTPException(status_code=400, detail="Provide one ticker for the indicator backtest.")

    start, end = _parse_and_validate_date_range(request.start_date, request.end_date, max_days=3650)
    request_dump = request.model_dump(mode="json")
    request_dump["ticker"] = ticker
    cache_suffix = hashlib.sha256(json.dumps(request_dump, sort_keys=True).encode("utf-8")).hexdigest()
    cache_key = f"backtest_indicator:v1:{ticker}:{cache_suffix}"

    cached = cache_service.get(cache_key)
    if cached:
        return {**cached, "cached": True}

    try:
        market_data, source, warnings = load_backtest_market_data(db, ticker, start, end)
        market_data = _resample_market_data(market_data, request.timeframe)
        result = run_indicator_backtest(
            market_data,
            request.indicators,
            request.atr_gate,
            long_threshold=request.long_threshold,
            short_threshold=request.short_threshold,
            exec_lag=request.exec_lag,
            tc_bps=request.tc_bps,
            allow_position_hold=request.allow_position_hold,
            generate_plots=request.generate_plots,
            generate_roc=request.generate_roc,
        )
        response = {
            "ticker": ticker,
            "mode": "indicator",
            "source": source,
            "cached": False,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "timeframe": request.timeframe,
            "warnings": warnings,
            **result,
        }
        cache_service.set(cache_key, response, ttl=3600)
        return response
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        print(f"Indicator backtest run error for {ticker}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to run indicator backtest")


@router.post("/{ticker}/ml-features")
def get_ml_features(
    ticker: str,
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)", regex=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)", regex=r"^\d{4}-\d{2}-\d{2}$"),
    db: Session = Depends(get_db),
):
    """
    Generate ML-ready feature set for a stock.

    Returns OHLCV data plus technical, volatility, and momentum features.
    """
    ticker = ticker.upper()
    cache_key = f"ml:{ticker}:{start_date}:{end_date}"

    cached = cache_service.get(cache_key)
    if cached:
        return {
            "ticker": ticker,
            "source": "cache",
            "cached": True,
            **cached,
        }

    ticker_obj = db.query(Ticker).filter(Ticker.symbol == ticker).first()
    if not ticker_obj:
        raise HTTPException(status_code=404, detail=f"Stock {ticker} not found")

    try:
        provider = ProviderFactory.get_historical_provider()
        start, end = _parse_and_validate_date_range(start_date, end_date, max_days=1825)
        df = provider.get_historical_prices(ticker, start, end)

        if df is None or df.empty:
            raise HTTPException(status_code=404, detail=f"No data available for {ticker}")

        df = add_technical_indicators(df)
        df["Returns_1d"] = df["Close"].pct_change(1)
        df["Returns_5d"] = df["Close"].pct_change(5)
        df["Returns_20d"] = df["Close"].pct_change(20)
        df["Volatility_20d"] = df["Returns_1d"].rolling(20).std()
        df["Volatility_50d"] = df["Returns_1d"].rolling(50).std()
        df["Momentum_10d"] = df["Close"] - df["Close"].shift(10)
        df["Momentum_20d"] = df["Close"] - df["Close"].shift(20)
        df["Volume_Ratio"] = df["Volume"] / df["Volume_SMA_20"]

        df_clean = df.dropna()
        feature_columns = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
            "SMA_20",
            "SMA_50",
            "SMA_200",
            "EMA_12",
            "EMA_26",
            "MACD",
            "MACD_Signal",
            "RSI_14",
            "BB_Upper",
            "BB_Lower",
            "Returns_1d",
            "Returns_5d",
            "Returns_20d",
            "Volatility_20d",
            "Volatility_50d",
            "Momentum_10d",
            "Momentum_20d",
            "Volume_Ratio",
        ]

        df_reset = df_clean[feature_columns].reset_index()
        if "Date" not in df_reset.columns:
            df_reset = df_reset.rename(columns={df_reset.columns[0]: "Date"})
        df_reset["Date"] = df_reset["Date"].astype(str)
        data = df_reset.to_dict(orient="records")

        result = {
            "data_points": len(data),
            "features": feature_columns,
            "data": data,
            "description": {
                "price_features": 5,
                "technical_indicators": 10,
                "momentum_features": 4,
                "volatility_features": 2,
                "volume_features": 2,
                "total_features": len(feature_columns),
            },
        }

        cache_service.set(cache_key, result, ttl=7200)
        return {
            "ticker": ticker,
            "source": "yfinance",
            "cached": False,
            **result,
        }
    except HTTPException:
        raise
    except Exception as exc:
        print(f"ML feature generation error for {ticker}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to generate ML features")


@router.get("/{ticker}/intraday")
def get_intraday_data(
    ticker: str,
    interval: str = Query("5m", regex="^(1m|5m|15m|30m|60m)$", description="Time interval"),
    days: int = Query(5, ge=1, le=30, description="Number of days (max 30)"),
    db: Session = Depends(get_db),
):
    """Get intraday minute-level data."""
    ticker = ticker.upper()
    cache_key = f"intraday:{ticker}:{interval}:{days}"

    cached = cache_service.get(cache_key)
    if cached:
        return {
            "ticker": ticker,
            "source": "cache",
            **cached,
        }

    ticker_obj = db.query(Ticker).filter(Ticker.symbol == ticker).first()
    if not ticker_obj:
        raise HTTPException(status_code=404, detail=f"Stock {ticker} not found")

    try:
        import yfinance as yf

        stock = yf.Ticker(ticker)
        df = stock.history(period=f"{days}d", interval=interval, auto_adjust=True)
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail=f"No intraday data available for {ticker}")

        df_reset = df.reset_index()
        if "Date" not in df_reset.columns:
            df_reset = df_reset.rename(columns={df_reset.columns[0]: "Date"})
        df_reset["Date"] = df_reset["Date"].astype(str)
        result = {
            "interval": interval,
            "days": days,
            "data_points": len(df_reset),
            "data": df_reset.to_dict(orient="records"),
        }
        cache_service.set(cache_key, result, ttl=1800)
        return {"ticker": ticker, "source": "yfinance", **result}
    except HTTPException:
        raise
    except Exception as exc:
        print(f"Intraday data fetch error for {ticker}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to fetch intraday data")
