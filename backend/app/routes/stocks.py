import hashlib
import json
from datetime import datetime, timedelta

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.backtests.data import load_backtest_market_data
from app.backtests.portfolio import run_portfolio_backtest
from app.database.connection import get_db
from app.database.models import Ticker
from app.models.stock import (
    BacktestDataResponse,
    BacktestRunRequest,
    BacktestRunResponse,
    MLFeaturesResponse,
    StockDetail,
)
from app.providers.factory import ProviderFactory
from app.services.cache import cache_service
from app.services.stock_service import get_price_history, get_stock_with_fundamentals
from app.utils.data_fetcher import add_technical_indicators


router = APIRouter(prefix="/stocks", tags=["stocks"])


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


def _normalize_backtest_tickers(primary_ticker: str, extra_tickers: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for raw in [primary_ticker, *(extra_tickers or [])]:
        ticker = str(raw).strip().upper()
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        ordered.append(ticker)

    if not ordered:
        raise HTTPException(status_code=400, detail="Provide at least one ticker for the backtest.")

    if len(ordered) > 25:
        raise HTTPException(status_code=400, detail="Backtest basket is limited to 25 tickers per run.")

    return ordered


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
    ticker = ticker.upper()
    tickers = _normalize_backtest_tickers(ticker, request.tickers)
    allocation_weights = _normalize_backtest_weights(tickers, request.allocation_weights)

    start, end = _parse_and_validate_date_range(request.start_date, request.end_date, max_days=3650)
    request_dump = request.model_dump(mode="json")
    request_dump["tickers"] = tickers
    request_dump["allocation_weights"] = allocation_weights
    cache_suffix = hashlib.sha256(json.dumps(request_dump, sort_keys=True).encode("utf-8")).hexdigest()
    cache_key = f"backtest_run:v2:{ticker}:{cache_suffix}"

    cached = cache_service.get(cache_key)
    if cached:
        return {
            **cached,
            "cached": True,
        }

    try:
        market_data: dict[str, pd.DataFrame] = {}
        data_sources: dict[str, str] = {}
        warnings: list[str] = []
        for symbol in tickers:
            symbol_data, source, symbol_warnings = load_backtest_market_data(db, symbol, start, end)
            market_data[symbol] = symbol_data
            data_sources[symbol] = source
            warnings.extend([f"{symbol}: {warning}" for warning in symbol_warnings])

        result = run_portfolio_backtest(
            market_data,
            tickers=tickers,
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
            generate_plots=request.generate_plots,
        )
        overall_source = next(iter(data_sources.values())) if len(set(data_sources.values())) == 1 else "mixed"
        response = {
            "ticker": ticker,
            "tickers": tickers,
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
        print(f"Backtest run error for {ticker}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to run backtest")


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
