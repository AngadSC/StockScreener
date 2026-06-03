from __future__ import annotations

import math
from datetime import date

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.backtests.data import load_backtest_market_data_batch_db_only
from app.backtests.portfolio import run_portfolio_backtest
from app.database.models import DailyOHLCV, Ticker
from app.models.stock import BacktestRunRequest
from app.routes import stocks as stocks_route
from app.utils.market_calendar import get_trading_days_between


def _sample_market_data(seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    periods = 260
    dates = pd.date_range("2021-01-01", periods=periods, freq="B")
    trend = np.linspace(100, 160, periods)
    seasonal = 4 * np.sin(np.linspace(0, 8 * np.pi, periods))
    noise = rng.normal(0, 0.8, periods)
    close = trend + seasonal + noise
    open_ = close * (1 + rng.normal(0, 0.002, periods))
    high = np.maximum(open_, close) * (1 + 0.01)
    low = np.minimum(open_, close) * (1 - 0.01)
    volume = 1_000_000 + rng.integers(0, 100_000, periods)
    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume,
        },
        index=dates,
    )


@pytest.fixture
def sqlite_db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Ticker.__table__.create(engine)
    DailyOHLCV.__table__.create(engine)
    TestingSessionLocal = sessionmaker(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def _seed_ticker(db: Session, symbol: str, ticker_id: int) -> Ticker:
    ticker = Ticker(id=ticker_id, symbol=symbol, name=symbol, exchange="NASDAQ")
    db.add(ticker)
    db.commit()
    return ticker


def _seed_candles(db: Session, ticker: Ticker, days: list[date]) -> None:
    for index, candle_date in enumerate(days):
        close = 100.0 + index
        db.add(
            DailyOHLCV(
                ticker_id=ticker.id,
                date=candle_date,
                open=close - 1.0,
                high=close + 1.0,
                low=close - 2.0,
                close=close,
                volume=1_000_000 + index,
            )
        )
    db.commit()


def test_allocation_weights_fill_missing_and_add_benchmark_curve():
    market_data = {
        "AAPL": _sample_market_data(1),
        "MSFT": _sample_market_data(2),
        "NVDA": _sample_market_data(3),
    }

    result = run_portfolio_backtest(
        market_data,
        tickers=["AAPL", "MSFT", "NVDA"],
        allocation_weights={"AAPL": 50},
        timeframe="1d",
        initial_capital=10_000,
        tc_bps=5,
        allow_fractional_shares=True,
        family="trend_following",
        strategy_params={"fast_ema": 20, "slow_ema": 50},
        risk_controls=None,
        tuning=None,
        include_buy_and_hold=True,
        generate_plots=False,
    )

    assert math.isclose(result["allocation_weights"]["AAPL"], 50.0, rel_tol=0, abs_tol=1e-6)
    assert math.isclose(result["allocation_weights"]["MSFT"], 25.0, rel_tol=0, abs_tol=1e-6)
    assert math.isclose(result["allocation_weights"]["NVDA"], 25.0, rel_tol=0, abs_tol=1e-6)
    assert math.isclose(result["cash_reserve_pct"], 0.0, rel_tol=0, abs_tol=1e-6)
    assert result["buy_and_hold"] is not None
    assert result["equity_curve"]
    assert "BuyHoldEquity" in result["equity_curve"][0]
    benchmark_values = [float(row["BuyHoldEquity"]) for row in result["equity_curve"] if row["BuyHoldEquity"] is not None]
    assert benchmark_values[0] != benchmark_values[-1]


def test_new_strategy_families_execute():
    market_data = {"AAPL": _sample_market_data(11)}
    families = [
        ("golden_cross", {"fast_sma": 20, "slow_sma": 80}),
        ("macd_trend", {"fast_ema": 12, "slow_ema": 26, "signal_period": 9}),
        ("rsi_trend_filter", {"trend_ma": 100, "rsi_period": 14, "entry_rsi": 52, "exit_rsi": 45}),
    ]

    for family, strategy_params in families:
        result = run_portfolio_backtest(
            market_data,
            tickers=["AAPL"],
            allocation_weights={"AAPL": 100},
            timeframe="1d",
            initial_capital=10_000,
            tc_bps=5,
            allow_fractional_shares=True,
            family=family,
            strategy_params=strategy_params,
            risk_controls=None,
            tuning=None,
            include_buy_and_hold=False,
            generate_plots=False,
        )

        assert result["stats"]["initial_capital"] == 10_000
        assert result["equity_curve"]


def test_public_portfolio_strategy_modes_execute(monkeypatch):
    monkeypatch.setattr("app.backtests.portfolio.yf.download", lambda *args, **kwargs: pd.DataFrame())
    market_data = {
        "AAPL": _sample_market_data(21),
        "MSFT": _sample_market_data(22),
        "NVDA": _sample_market_data(23),
        "XLE": _sample_market_data(24),
    }
    families = [
        ("leaders_carry_everything", {"momentum_window": 40, "top_n": 2, "rebalance_days": 10}),
        ("sector_rotation_momentum", {"rotation_window": 40, "top_n": 2, "rebalance_days": 10}),
        ("earnings_momentum", {"momentum_window": 20, "volume_window": 10, "top_n": 2, "rebalance_days": 10}),
        ("mean_reversion_extremes", {"peak_lookback": 10, "drop_pct": 0.02, "recovery_pct": 0.01}),
        ("gap_fill_reflex", {"gap_threshold": 0.001, "fill_ratio": 0.25}),
        ("losers_keep_losing", {"momentum_window": 30, "trend_window": 10, "top_n": 2, "rebalance_days": 10}),
        ("volatility_regimes", {"vix_entry": 20, "vix_exit": 25, "trend_ma": 20}),
        ("overnight_intraday_edge", {"lookback": 10}),
        ("index_drag_problem", {"lookback": 20, "rs_threshold": -1.0, "top_n": 2, "rebalance_days": 10}),
        ("crowding_risk", {"momentum_window": 20, "volume_window": 10, "volatility_window": 10, "top_n": 2, "rebalance_days": 10}),
    ]

    for family, strategy_params in families:
        result = run_portfolio_backtest(
            market_data,
            tickers=list(market_data.keys()),
            allocation_weights={},
            timeframe="1d",
            initial_capital=10_000,
            tc_bps=5,
            allow_fractional_shares=True,
            family=family,
            strategy_params=strategy_params,
            risk_controls=None,
            tuning=None,
            include_buy_and_hold=False,
            generate_plots=False,
        )

        assert result["stats"]["initial_capital"] == 10_000
        assert result["equity_curve"]
        assert result["strategy_params"]


def test_automated_sp500_universe_expands_server_side_and_does_not_buy_spy_only(monkeypatch):
    universe = ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "JPM", "XOM", "LLY", "AVGO", "UNH", "HD"]
    market_data = {symbol: _sample_market_data(index + 40) for index, symbol in enumerate(universe)}

    monkeypatch.setattr(stocks_route.cache_service, "get", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(stocks_route.cache_service, "set", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(stocks_route, "get_sp500_tickers", lambda: universe)

    batch_calls = []

    def fake_batch_loader(_db, symbols, _start, _end, *, min_required_bars):
        batch_calls.append((symbols, min_required_bars))
        return market_data, {symbol: "database" for symbol in symbols}, []

    monkeypatch.setattr(
        stocks_route,
        "load_backtest_market_data_batch_db_only",
        fake_batch_loader,
    )
    monkeypatch.setattr(
        stocks_route,
        "load_backtest_market_data",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("single-symbol fallback should not run")),
    )
    monkeypatch.setattr(
        stocks_route,
        "_load_rank_metadata",
        lambda _db, tickers, _warnings: {
            symbol: {"market_cap": (len(tickers) - index) * 1_000_000_000, "avg_volume": None, "volume": None}
            for index, symbol in enumerate(tickers)
        },
    )

    result = stocks_route._run_backtest_request(
        None,
        BacktestRunRequest(
            start_date="2021-01-01",
            end_date="2021-12-31",
            universe="sp500",
            tickers=["SPY"],
            strategy={
                "family": "leaders_carry_everything",
                "params": {"momentum_window": 20, "top_n": 10, "rebalance_days": 10, "min_momentum": -1.0},
            },
            include_buy_and_hold=False,
            generate_plots=False,
        ),
        db=None,
    )

    assert result["universe"] == "sp500"
    assert result["tickers"] == universe
    assert result["tickers"] != ["SPY"]
    assert result["current_holdings"]
    assert {holding["ticker"] for holding in result["current_holdings"]} <= set(universe)
    assert batch_calls and batch_calls[0][0] == universe


def test_leaders_strategy_top_n_caps_active_holdings_per_rebalance():
    tickers = [f"T{i:02d}" for i in range(15)]
    market_data = {symbol: _sample_market_data(index + 70) for index, symbol in enumerate(tickers)}

    result = run_portfolio_backtest(
        market_data,
        tickers=tickers,
        allocation_weights={},
        timeframe="1d",
        initial_capital=10_000,
        tc_bps=5,
        allow_fractional_shares=True,
        family="leaders_carry_everything",
        strategy_params={"momentum_window": 20, "top_n": 10, "rebalance_days": 10, "min_momentum": -1.0},
        risk_controls=None,
        tuning=None,
        include_buy_and_hold=False,
        generate_plots=False,
    )

    active_counts = [int(row["ActivePositions"]) for row in result["equity_curve"]]
    assert max(active_counts) <= 10
    assert all(len(snapshot["holdings"]) <= 10 for snapshot in result["selected_holdings"])


def test_custom_basket_request_still_uses_user_supplied_tickers(monkeypatch):
    market_data = {symbol: _sample_market_data(index + 90) for index, symbol in enumerate(["AAPL", "MSFT"])}

    monkeypatch.setattr(stocks_route.cache_service, "get", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(stocks_route.cache_service, "set", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        stocks_route,
        "load_backtest_market_data",
        lambda _db, symbol, _start, _end, **_kwargs: (market_data[symbol], "database", []),
    )
    monkeypatch.setattr(
        stocks_route,
        "load_backtest_market_data_batch_db_only",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("custom baskets should use DB-first fallback loader")),
    )

    result = stocks_route._run_backtest_request(
        None,
        BacktestRunRequest(
            start_date="2021-01-01",
            end_date="2021-12-31",
            universe="custom",
            tickers=["AAPL", "MSFT"],
            strategy={"family": "trend_following", "params": {"fast_ema": 20, "slow_ema": 50}},
            include_buy_and_hold=False,
            generate_plots=False,
        ),
        db=None,
    )

    assert result["universe"] == "custom"
    assert result["tickers"] == ["AAPL", "MSFT"]


def test_large_sp500_run_disables_plot_image_but_keeps_equity_curve(monkeypatch):
    universe = [f"T{i:02d}" for i in range(51)]
    market_data = {symbol: _sample_market_data(index + 130) for index, symbol in enumerate(universe)}

    monkeypatch.setattr(stocks_route.cache_service, "get", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(stocks_route.cache_service, "set", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(stocks_route, "get_sp500_tickers", lambda: universe)
    monkeypatch.setattr(
        stocks_route,
        "load_backtest_market_data_batch_db_only",
        lambda _db, symbols, _start, _end, **_kwargs: (
            {symbol: market_data[symbol] for symbol in symbols},
            {symbol: "database" for symbol in symbols},
            [],
        ),
    )

    result = stocks_route._run_backtest_request(
        None,
        BacktestRunRequest(
            start_date="2021-01-01",
            end_date="2021-12-31",
            universe="sp500",
            strategy={"family": "trend_following", "params": {"fast_ema": 5, "slow_ema": 10}},
            include_buy_and_hold=False,
            generate_plots=True,
        ),
        db=None,
    )

    assert result["equity_curve"]
    assert result["equity_curve_image"] is None
    assert "Server-side plot image disabled for large universe run; frontend chart uses equity curve data." in result["warnings"]


def test_batch_db_loader_includes_ticker_with_small_missing_day_count(sqlite_db: Session):
    ticker = _seed_ticker(sqlite_db, "AAPL", 1)
    days = get_trading_days_between(date(2021, 1, 4), date(2021, 12, 31))
    missing_days = set(days[20:25])
    _seed_candles(sqlite_db, ticker, [day for day in days if day not in missing_days])

    market_data, data_sources, warnings = load_backtest_market_data_batch_db_only(
        sqlite_db,
        ["AAPL"],
        date(2021, 1, 4),
        date(2021, 12, 31),
        min_required_bars=50,
    )

    assert "AAPL" in market_data
    assert data_sources["AAPL"] == "database"
    assert len(market_data["AAPL"]) == len(days) - len(missing_days)
    assert warnings == []


def test_batch_db_loader_skips_ticker_with_too_little_history(sqlite_db: Session):
    good = _seed_ticker(sqlite_db, "GOOD", 1)
    short = _seed_ticker(sqlite_db, "SHORT", 2)
    days = get_trading_days_between(date(2021, 1, 4), date(2021, 12, 31))
    _seed_candles(sqlite_db, good, days)
    _seed_candles(sqlite_db, short, days[:10])

    market_data, data_sources, warnings = load_backtest_market_data_batch_db_only(
        sqlite_db,
        ["GOOD", "SHORT"],
        date(2021, 1, 4),
        date(2021, 12, 31),
        min_required_bars=50,
    )

    assert set(market_data) == {"GOOD"}
    assert data_sources == {"GOOD": "database"}
    assert "Skipped 1 symbols with insufficient DB history." in warnings
    assert any("SHORT" in warning for warning in warnings)


def test_indicator_strategy_endpoint_executes(monkeypatch):
    monkeypatch.setattr(stocks_route.cache_service, "get", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(stocks_route.cache_service, "set", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        stocks_route,
        "load_backtest_market_data",
        lambda _db, _symbol, _start, _end: (_sample_market_data(120), "database", []),
    )

    result = stocks_route.run_global_indicator_backtest(
        stocks_route.IndicatorBacktestRunRequest(
            ticker="AAPL",
            start_date="2021-01-01",
            end_date="2021-12-31",
            indicators={"rsi": {"enabled": True, "weight": 1.0, "params": {"period": 14}}},
            generate_plots=False,
        ),
        db=None,
    )

    assert result["mode"] == "indicator"
    assert result["ticker"] == "AAPL"
    assert "RSI" in result["selected_indicators"]
    assert result["equity_curve"]
