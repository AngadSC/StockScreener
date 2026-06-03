from __future__ import annotations

import math

import numpy as np
import pandas as pd

from app.backtests.portfolio import run_portfolio_backtest
from app.models.stock import BacktestRunRequest
from app.routes import stocks as stocks_route


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
    monkeypatch.setattr(
        stocks_route,
        "load_backtest_market_data",
        lambda _db, symbol, _start, _end: (market_data[symbol], "database", []),
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
        lambda _db, symbol, _start, _end: (market_data[symbol], "database", []),
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
