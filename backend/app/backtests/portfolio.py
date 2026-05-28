from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, MACD, SMAIndicator
from ta.volatility import BollingerBands

from app.backtests.plots import generate_equity_curve_plot


STRATEGY_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "trend_following": {"fast_ema": 50, "slow_ema": 200},
    "mean_reversion": {"window": 20, "std_dev": 2.0},
    "momentum_breakout": {"breakout_lookback": 50, "exit_lookback": 20},
    "oversold_reversal": {"rsi_period": 14, "entry_rsi": 30.0, "exit_rsi": 50.0},
    "moving_average_pullback": {"trend_ma": 200, "pullback_ma": 20, "entry_buffer_pct": 0.01},
    "volume_breakout": {
        "breakout_lookback": 20,
        "exit_lookback": 10,
        "volume_window": 20,
        "volume_multiplier": 2.0,
    },
    "golden_cross": {"fast_sma": 50, "slow_sma": 200},
    "macd_trend": {"fast_ema": 12, "slow_ema": 26, "signal_period": 9},
    "rsi_trend_filter": {"trend_ma": 200, "rsi_period": 14, "entry_rsi": 55.0, "exit_rsi": 45.0},
    "price_momentum": {"momentum_window": 252, "exit_ma": 50},
    "sector_momentum": {"rotation_window": 126, "rs_percentile": 0.8},
    "extreme_reversal": {"peak_lookback": 20, "drop_pct": 0.10, "recovery_pct": 0.03},
    "gap_fill": {"gap_threshold": 0.03, "fill_ratio": 0.5},
    "momentum_filter": {"momentum_window": 126, "trend_window": 20},
    "volatility_regime": {"vix_entry": 20.0, "vix_exit": 25.0, "trend_ma": 50},
    "overnight_edge": {"lookback": 20},
    "relative_strength": {"lookback": 63, "rs_threshold": 0.0},
}

PERIODS_PER_YEAR = {"1d": 252, "1wk": 52, "1mo": 12}
RESAMPLE_RULES = {"1d": None, "1wk": "W-FRI", "1mo": "M"}


@dataclass
class Position:
    ticker: str
    shares: float
    entry_date: pd.Timestamp
    entry_price: float
    entry_fee: float
    entry_bar: int
    highest_price: float


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _coerce_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _clean_numeric(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (np.floating, float)):
        if math.isnan(value) or math.isinf(value):
            return None
        return round(float(value), 6)
    if isinstance(value, (np.integer, int)):
        return int(value)
    return value


def _serialize_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    out = df.copy().replace([np.inf, -np.inf], np.nan).reset_index()
    if "index" in out.columns:
        out = out.rename(columns={"index": "Date"})
    if "Date" in out.columns:
        out["Date"] = pd.to_datetime(out["Date"]).dt.strftime("%Y-%m-%d")
    records: List[Dict[str, Any]] = []
    for row in out.to_dict(orient="records"):
        records.append({key: _clean_numeric(value) for key, value in row.items()})
    return records


def _resample_market_data(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    out = df.copy()
    out.index = pd.to_datetime(out.index)
    out = out.sort_index()

    if timeframe == "1d":
        return out

    rule = RESAMPLE_RULES[timeframe]
    agg = {
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum",
    }
    resampled = out.resample(rule).agg(agg).dropna(subset=["Open", "High", "Low", "Close"])
    return resampled


def _cross_above(fast: pd.Series, slow: pd.Series) -> pd.Series:
    prev = fast.shift(1) - slow.shift(1)
    curr = fast - slow
    return ((prev <= 0) & (curr > 0)).fillna(False)


def _cross_below(fast: pd.Series, slow: pd.Series) -> pd.Series:
    prev = fast.shift(1) - slow.shift(1)
    curr = fast - slow
    return ((prev >= 0) & (curr < 0)).fillna(False)


def _cross_value_above(series: pd.Series, threshold: float) -> pd.Series:
    return ((series.shift(1) <= threshold) & (series > threshold)).fillna(False)


def _cross_value_below(series: pd.Series, threshold: float) -> pd.Series:
    return ((series.shift(1) >= threshold) & (series < threshold)).fillna(False)


def _normalize_allocation_weights(
    tickers: List[str],
    allocation_weights: Dict[str, Any] | None,
) -> Tuple[Dict[str, float], float]:
    if not tickers:
        raise ValueError("At least one ticker is required to size the portfolio.")

    if not allocation_weights:
        equal_weight = round(100.0 / len(tickers), 6)
        normalized = {ticker: equal_weight for ticker in tickers}
        rounding_diff = round(100.0 - sum(normalized.values()), 6)
        normalized[tickers[-1]] = round(normalized[tickers[-1]] + rounding_diff, 6)
        return normalized, 0.0

    normalized_inputs: Dict[str, float] = {}
    for raw_ticker, raw_weight in allocation_weights.items():
        ticker = str(raw_ticker).strip().upper()
        if ticker not in tickers:
            raise ValueError(f"Allocation weight supplied for unknown ticker '{ticker}'.")
        weight = _coerce_float(raw_weight, 0.0)
        if weight < 0:
            raise ValueError("Allocation weights cannot be negative.")
        normalized_inputs[ticker] = round(weight, 6)

    specified_total = round(sum(normalized_inputs.values()), 6)
    if specified_total > 100.0 + 1e-6:
        raise ValueError("Allocation weights cannot sum to more than 100%.")

    missing = [ticker for ticker in tickers if ticker not in normalized_inputs]
    remaining_pct = max(0.0, round(100.0 - specified_total, 6))

    normalized = dict(normalized_inputs)
    if missing:
        fill = round(remaining_pct / len(missing), 6) if missing else 0.0
        for ticker in missing:
            normalized[ticker] = fill
        rounding_diff = round(100.0 - sum(normalized.values()), 6)
        if missing:
            normalized[missing[-1]] = round(normalized[missing[-1]] + rounding_diff, 6)
        remaining_pct = 0.0

    total_pct = round(sum(normalized.values()), 6)
    if total_pct > 100.0 + 1e-6:
        raise ValueError("Allocation weights cannot sum to more than 100%.")

    return normalized, round(max(0.0, 100.0 - total_pct), 6)


def _mark_to_market(
    active_positions: Dict[str, Position],
    last_prices: Dict[str, float],
) -> float:
    market_value = 0.0
    for ticker, position in active_positions.items():
        mark_price = last_prices.get(ticker, position.entry_price)
        market_value += position.shares * mark_price
    return market_value


def _prepare_strategy_frame(
    market_data: pd.DataFrame,
    family: str,
    params: Dict[str, Any],
    timeframe: str,
) -> pd.DataFrame:
    df = _resample_market_data(market_data, timeframe).copy()
    defaults = STRATEGY_DEFAULTS[family]
    merged = {**defaults, **params}

    df["entry_signal"] = False
    df["exit_signal"] = False

    if family == "trend_following":
        fast_ema = _coerce_int(merged.get("fast_ema"), defaults["fast_ema"])
        slow_ema = _coerce_int(merged.get("slow_ema"), defaults["slow_ema"])
        df["fast_ema"] = EMAIndicator(df["Close"], window=fast_ema).ema_indicator()
        df["slow_ema"] = EMAIndicator(df["Close"], window=slow_ema).ema_indicator()
        df["entry_signal"] = _cross_above(df["fast_ema"], df["slow_ema"])
        df["exit_signal"] = _cross_below(df["fast_ema"], df["slow_ema"])

    elif family == "mean_reversion":
        window = _coerce_int(merged.get("window"), defaults["window"])
        std_dev = _coerce_float(merged.get("std_dev"), defaults["std_dev"])
        bb = BollingerBands(df["Close"], window=window, window_dev=std_dev)
        df["bb_mid"] = bb.bollinger_mavg()
        df["bb_low"] = bb.bollinger_lband()
        df["entry_signal"] = (df["Close"] <= df["bb_low"]).fillna(False)
        df["exit_signal"] = (df["Close"] >= df["bb_mid"]).fillna(False)

    elif family == "momentum_breakout":
        breakout_lookback = _coerce_int(merged.get("breakout_lookback"), defaults["breakout_lookback"])
        exit_lookback = _coerce_int(merged.get("exit_lookback"), defaults["exit_lookback"])
        df["rolling_high"] = df["High"].rolling(breakout_lookback).max().shift(1)
        df["rolling_low"] = df["Low"].rolling(exit_lookback).min().shift(1)
        df["entry_signal"] = (df["Close"] > df["rolling_high"]).fillna(False)
        df["exit_signal"] = (df["Close"] < df["rolling_low"]).fillna(False)

    elif family == "oversold_reversal":
        rsi_period = _coerce_int(merged.get("rsi_period"), defaults["rsi_period"])
        entry_rsi = _coerce_float(merged.get("entry_rsi"), defaults["entry_rsi"])
        exit_rsi = _coerce_float(merged.get("exit_rsi"), defaults["exit_rsi"])
        df["rsi"] = RSIIndicator(df["Close"], window=rsi_period).rsi()
        df["entry_signal"] = (df["rsi"] < entry_rsi).fillna(False)
        df["exit_signal"] = (df["rsi"] > exit_rsi).fillna(False)

    elif family == "moving_average_pullback":
        trend_ma = _coerce_int(merged.get("trend_ma"), defaults["trend_ma"])
        pullback_ma = _coerce_int(merged.get("pullback_ma"), defaults["pullback_ma"])
        entry_buffer_pct = _coerce_float(merged.get("entry_buffer_pct"), defaults["entry_buffer_pct"])
        df["trend_ma"] = SMAIndicator(df["Close"], window=trend_ma).sma_indicator()
        df["pullback_ma"] = SMAIndicator(df["Close"], window=pullback_ma).sma_indicator()
        buffer_level = df["pullback_ma"] * (1.0 + entry_buffer_pct)
        df["entry_signal"] = ((df["Close"] > df["trend_ma"]) & (df["Close"] <= buffer_level)).fillna(False)
        df["exit_signal"] = ((df["Close"] >= df["pullback_ma"]) | (df["Close"] < df["trend_ma"])).fillna(False)

    elif family == "volume_breakout":
        breakout_lookback = _coerce_int(merged.get("breakout_lookback"), defaults["breakout_lookback"])
        exit_lookback = _coerce_int(merged.get("exit_lookback"), defaults["exit_lookback"])
        volume_window = _coerce_int(merged.get("volume_window"), defaults["volume_window"])
        volume_multiplier = _coerce_float(merged.get("volume_multiplier"), defaults["volume_multiplier"])
        df["rolling_high"] = df["High"].rolling(breakout_lookback).max().shift(1)
        df["rolling_low"] = df["Low"].rolling(exit_lookback).min().shift(1)
        df["avg_volume"] = df["Volume"].rolling(volume_window).mean().shift(1)
        df["entry_signal"] = (
            (df["Close"] > df["rolling_high"]) & (df["Volume"] >= df["avg_volume"] * volume_multiplier)
        ).fillna(False)
        df["exit_signal"] = (df["Close"] < df["rolling_low"]).fillna(False)

    elif family == "golden_cross":
        fast_sma = _coerce_int(merged.get("fast_sma"), defaults["fast_sma"])
        slow_sma = _coerce_int(merged.get("slow_sma"), defaults["slow_sma"])
        df["fast_sma"] = SMAIndicator(df["Close"], window=fast_sma).sma_indicator()
        df["slow_sma"] = SMAIndicator(df["Close"], window=slow_sma).sma_indicator()
        df["entry_signal"] = _cross_above(df["fast_sma"], df["slow_sma"])
        df["exit_signal"] = _cross_below(df["fast_sma"], df["slow_sma"])

    elif family == "macd_trend":
        fast_ema = _coerce_int(merged.get("fast_ema"), defaults["fast_ema"])
        slow_ema = _coerce_int(merged.get("slow_ema"), defaults["slow_ema"])
        signal_period = _coerce_int(merged.get("signal_period"), defaults["signal_period"])
        macd = MACD(df["Close"], window_fast=fast_ema, window_slow=slow_ema, window_sign=signal_period)
        df["macd_line"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        df["entry_signal"] = (_cross_above(df["macd_line"], df["macd_signal"]) & (df["macd_line"] > 0)).fillna(False)
        df["exit_signal"] = (
            _cross_below(df["macd_line"], df["macd_signal"]) | (df["macd_line"] < 0)
        ).fillna(False)

    elif family == "rsi_trend_filter":
        trend_ma = _coerce_int(merged.get("trend_ma"), defaults["trend_ma"])
        rsi_period = _coerce_int(merged.get("rsi_period"), defaults["rsi_period"])
        entry_rsi = _coerce_float(merged.get("entry_rsi"), defaults["entry_rsi"])
        exit_rsi = _coerce_float(merged.get("exit_rsi"), defaults["exit_rsi"])
        df["trend_ma"] = SMAIndicator(df["Close"], window=trend_ma).sma_indicator()
        df["rsi"] = RSIIndicator(df["Close"], window=rsi_period).rsi()
        df["entry_signal"] = (
            (df["Close"] > df["trend_ma"]) & _cross_value_above(df["rsi"], entry_rsi)
        ).fillna(False)
        df["exit_signal"] = (
            (df["Close"] < df["trend_ma"]) | _cross_value_below(df["rsi"], exit_rsi)
        ).fillna(False)

    elif family == "price_momentum":
        momentum_window = _coerce_int(merged.get("momentum_window"), defaults["momentum_window"])
        exit_ma = _coerce_int(merged.get("exit_ma"), defaults["exit_ma"])
        df["returns_nm"] = df["Close"].pct_change(momentum_window)
        df["exit_ma_line"] = SMAIndicator(df["Close"], window=exit_ma).sma_indicator()
        df["entry_signal"] = ((df["returns_nm"] > 0) & (df["Close"] > df["exit_ma_line"])).fillna(False)
        df["exit_signal"] = ((df["returns_nm"] <= 0) | (df["Close"] < df["exit_ma_line"])).fillna(False)

    elif family == "sector_momentum":
        rotation_window = _coerce_int(merged.get("rotation_window"), defaults["rotation_window"])
        rs_percentile = _coerce_float(merged.get("rs_percentile"), defaults["rs_percentile"])
        df["period_high"] = df["Close"].rolling(rotation_window).max()
        df["period_low"] = df["Close"].rolling(rotation_window).min()
        rng = (df["period_high"] - df["period_low"]).replace(0.0, np.nan)
        df["rs_score"] = (df["Close"] - df["period_low"]) / rng
        df["entry_signal"] = (df["rs_score"] >= rs_percentile).fillna(False)
        df["exit_signal"] = (df["rs_score"] < (1.0 - rs_percentile)).fillna(False)

    elif family == "extreme_reversal":
        peak_lookback = _coerce_int(merged.get("peak_lookback"), defaults["peak_lookback"])
        drop_pct = _coerce_float(merged.get("drop_pct"), defaults["drop_pct"])
        recovery_pct = _coerce_float(merged.get("recovery_pct"), defaults["recovery_pct"])
        df["rolling_peak"] = df["Close"].rolling(peak_lookback).max()
        df["drawdown_from_peak"] = (df["Close"] - df["rolling_peak"]) / df["rolling_peak"].replace(0.0, np.nan)
        df["entry_signal"] = (df["drawdown_from_peak"] <= -drop_pct).fillna(False)
        df["exit_signal"] = (df["drawdown_from_peak"] >= -recovery_pct).fillna(False)

    elif family == "gap_fill":
        gap_threshold = _coerce_float(merged.get("gap_threshold"), defaults["gap_threshold"])
        fill_ratio = _coerce_float(merged.get("fill_ratio"), defaults["fill_ratio"])
        prior_close = df["Close"].shift(1)
        df["overnight_gap"] = (df["Open"] - prior_close) / prior_close.replace(0.0, np.nan)
        gap_target = prior_close + (df["Open"] - prior_close) * (1.0 - fill_ratio)
        df["entry_signal"] = (df["overnight_gap"] <= -gap_threshold).fillna(False)
        df["exit_signal"] = (df["Close"] >= gap_target).fillna(False)

    elif family == "momentum_filter":
        momentum_window = _coerce_int(merged.get("momentum_window"), defaults["momentum_window"])
        trend_window = _coerce_int(merged.get("trend_window"), defaults["trend_window"])
        df["returns_nm"] = df["Close"].pct_change(momentum_window)
        df["trend_ma_line"] = SMAIndicator(df["Close"], window=trend_window).sma_indicator()
        df["entry_signal"] = ((df["returns_nm"] > 0) & (df["Close"] > df["trend_ma_line"])).fillna(False)
        df["exit_signal"] = ((df["returns_nm"] <= 0) | (df["Close"] < df["trend_ma_line"])).fillna(False)

    elif family == "volatility_regime":
        vix_entry = _coerce_float(merged.get("vix_entry"), defaults["vix_entry"])
        vix_exit = _coerce_float(merged.get("vix_exit"), defaults["vix_exit"])
        trend_ma = _coerce_int(merged.get("trend_ma"), defaults["trend_ma"])
        start_str = str(df.index.min().date())
        end_str = str(df.index.max().date())
        try:
            vix_raw = yf.download("^VIX", start=start_str, end=end_str, progress=False, auto_adjust=True)
            vix_close = vix_raw["Close"] if isinstance(vix_raw.columns, pd.Index) and "Close" in vix_raw.columns else vix_raw.iloc[:, 0]
            if isinstance(vix_close.columns if hasattr(vix_close, "columns") else None, pd.MultiIndex):
                vix_close = vix_close.iloc[:, 0]
            vix_close = pd.Series(vix_close.values, index=pd.to_datetime(vix_close.index))
            df["vix"] = vix_close.reindex(df.index, method="ffill").ffill().bfill()
        except Exception:
            df["vix"] = 15.0
        df["trend_ma_line"] = SMAIndicator(df["Close"], window=trend_ma).sma_indicator()
        df["entry_signal"] = ((df["Close"] > df["trend_ma_line"]) & (df["vix"] < vix_entry)).fillna(False)
        df["exit_signal"] = (df["vix"] > vix_exit).fillna(False)

    elif family == "overnight_edge":
        lookback = _coerce_int(merged.get("lookback"), defaults["lookback"])
        df["overnight_ret"] = (df["Open"] / df["Close"].shift(1)) - 1.0
        df["intraday_ret"] = (df["Close"] / df["Open"].replace(0.0, np.nan)) - 1.0
        df["overnight_avg"] = df["overnight_ret"].rolling(lookback).mean()
        df["intraday_avg"] = df["intraday_ret"].rolling(lookback).mean()
        df["entry_signal"] = ((df["overnight_avg"] > df["intraday_avg"]) & (df["overnight_avg"] > 0.0)).fillna(False)
        df["exit_signal"] = ((df["overnight_avg"] <= 0.0) | (df["overnight_avg"] < df["intraday_avg"])).fillna(False)

    elif family == "relative_strength":
        lookback = _coerce_int(merged.get("lookback"), defaults["lookback"])
        rs_threshold = _coerce_float(merged.get("rs_threshold"), defaults["rs_threshold"])
        start_str = str(df.index.min().date())
        end_str = str(df.index.max().date())
        try:
            spy_raw = yf.download("SPY", start=start_str, end=end_str, progress=False, auto_adjust=True)
            spy_close = spy_raw["Close"] if "Close" in spy_raw.columns else spy_raw.iloc[:, 0]
            if hasattr(spy_close, "columns"):
                spy_close = spy_close.iloc[:, 0]
            spy_close = pd.Series(spy_close.values, index=pd.to_datetime(spy_close.index))
            spy_ret = spy_close.pct_change(lookback).reindex(df.index, method="ffill")
        except Exception:
            spy_ret = pd.Series(0.0, index=df.index)
        df["stock_return"] = df["Close"].pct_change(lookback)
        df["spy_return"] = spy_ret
        df["rs"] = df["stock_return"] - df["spy_return"]
        df["entry_signal"] = (df["rs"] > rs_threshold).fillna(False)
        df["exit_signal"] = (df["rs"] < -rs_threshold).fillna(False)

    else:
        raise ValueError(f"Unsupported strategy family '{family}'.")

    return df


def _compute_exit_signal(
    position: Position,
    row: pd.Series,
    risk_controls: Dict[str, Any],
) -> Tuple[float | None, str | None, float]:
    highest_price = max(position.highest_price, float(row["High"]))
    stop_loss_pct = risk_controls.get("stop_loss_pct")
    trailing_stop_pct = risk_controls.get("trailing_stop_pct")
    take_profit_pct = risk_controls.get("take_profit_pct")

    if stop_loss_pct is not None:
        stop_price = position.entry_price * (1.0 - stop_loss_pct)
        if float(row["Low"]) <= stop_price:
            return stop_price, "stop_loss", highest_price

    if trailing_stop_pct is not None:
        trailing_stop = highest_price * (1.0 - trailing_stop_pct)
        if float(row["Low"]) <= trailing_stop:
            return trailing_stop, "trailing_stop", highest_price

    if take_profit_pct is not None:
        take_profit = position.entry_price * (1.0 + take_profit_pct)
        if float(row["High"]) >= take_profit:
            return take_profit, "take_profit", highest_price

    if bool(row.get("exit_signal", False)):
        return float(row["Close"]), "strategy_exit", highest_price

    return None, None, highest_price


def _build_parameter_grid(
    family: str,
    current_params: Dict[str, Any],
    parameter_ranges: Dict[str, Dict[str, Any]],
    max_combinations: int,
) -> List[Dict[str, Any]]:
    if not parameter_ranges:
        raise ValueError("Parameter tuning requires at least one parameter range.")

    defaults = {**STRATEGY_DEFAULTS[family], **current_params}
    grid_keys: List[str] = []
    grid_values: List[List[Any]] = []

    for key in sorted(parameter_ranges):
        config = parameter_ranges[key] or {}
        values = config.get("values") or []
        if values:
            candidates = list(values)
        else:
            min_value = config.get("min")
            max_value = config.get("max")
            step = config.get("step")
            if min_value is None or max_value is None or step is None:
                raise ValueError(f"Parameter range for '{key}' must include values or min/max/step.")
            raw_values = np.arange(float(min_value), float(max_value) + (float(step) / 2.0), float(step))
            candidates = raw_values.tolist()

        template = defaults.get(key)
        if isinstance(template, int):
            typed_values = sorted({int(round(value)) for value in candidates})
        else:
            typed_values = sorted({round(float(value), 6) for value in candidates})

        if not typed_values:
            raise ValueError(f"Parameter range for '{key}' did not produce any values.")

        grid_keys.append(key)
        grid_values.append(typed_values)

    total = math.prod(len(values) for values in grid_values)
    if total > max_combinations:
        raise ValueError(
            f"Parameter tuning produced {total} combinations which exceeds the limit of {max_combinations}."
        )

    combinations: List[Dict[str, Any]] = []
    for values in itertools.product(*grid_values):
        params = dict(current_params)
        params.update(dict(zip(grid_keys, values)))
        combinations.append(params)
    return combinations


def _objective_value(stats: Dict[str, Any], objective: str) -> float:
    value = stats.get(objective)
    if value is None:
        return float("-inf")
    if objective == "max_drawdown_pct":
        return -float(value)
    return float(value)


def _build_buy_and_hold_benchmark(
    prepared_frames: Dict[str, pd.DataFrame],
    tickers: List[str],
    allocation_weights: Dict[str, float],
    *,
    all_dates: List[pd.Timestamp],
    initial_capital: float,
    tc_bps: float,
    allow_fractional_shares: bool,
    periods_per_year: int,
    generate_plots: bool,
) -> Dict[str, Any]:
    fee_rate = tc_bps / 10_000.0
    benchmark_index = pd.DatetimeIndex(pd.to_datetime(all_dates), name="Date")
    benchmark_df = pd.DataFrame(index=benchmark_index)
    benchmark_df["Cash"] = float(initial_capital)
    benchmark_df["MarketValue"] = 0.0
    benchmark_df["ActivePositions"] = 0

    for ticker in tickers:
        frame = prepared_frames.get(ticker)
        if frame is None or frame.empty:
            continue

        close_series = frame["Close"].astype(float).sort_index()
        if close_series.empty:
            continue

        weight_pct = allocation_weights.get(ticker, 0.0)
        allocation = initial_capital * (weight_pct / 100.0)
        entry_date = pd.to_datetime(close_series.index[0])
        entry_price = float(close_series.iloc[0])
        if entry_price <= 0 or allocation <= 0:
            continue

        deployed_capital = allocation / (1.0 + fee_rate)
        position_values = (close_series / entry_price) * deployed_capital
        aligned_values = position_values.reindex(benchmark_df.index).ffill().fillna(0.0)
        aligned_values.loc[benchmark_df.index < entry_date] = 0.0

        benchmark_df["MarketValue"] += aligned_values
        benchmark_df.loc[benchmark_df.index >= entry_date, "Cash"] -= allocation
        benchmark_df.loc[benchmark_df.index >= entry_date, "ActivePositions"] += 1

    benchmark_df["Equity"] = benchmark_df["Cash"] + benchmark_df["MarketValue"]
    benchmark_df["DailyReturn"] = benchmark_df["Equity"].pct_change().fillna(0.0)
    benchmark_df["RollingMax"] = benchmark_df["Equity"].cummax()
    benchmark_df["DrawdownPct"] = (
        ((benchmark_df["RollingMax"] - benchmark_df["Equity"]) / benchmark_df["RollingMax"]).fillna(0.0) * 100.0
    )

    stats = _summarize_portfolio_stats(
        benchmark_df,
        [],
        initial_capital=initial_capital,
        periods_per_year=periods_per_year,
    )
    return {
        "stats": stats,
        "equity_curve": _serialize_records(
            benchmark_df[["Cash", "MarketValue", "Equity", "DailyReturn", "DrawdownPct", "ActivePositions"]]
        ),
        "equity_curve_image": (
            generate_equity_curve_plot(
                benchmark_df.index,
                benchmark_df["Equity"],
            )
            if generate_plots
            else None
        ),
    }


def _run_single_backtest(
    market_data: Dict[str, pd.DataFrame],
    *,
    tickers: List[str],
    allocation_weights: Dict[str, float],
    timeframe: str,
    initial_capital: float,
    tc_bps: float,
    allow_fractional_shares: bool,
    family: str,
    strategy_params: Dict[str, Any],
    risk_controls: Dict[str, Any] | None,
    include_buy_and_hold: bool,
    generate_plots: bool,
) -> Dict[str, Any]:
    prepared_frames: Dict[str, pd.DataFrame] = {}
    last_prices: Dict[str, float] = {}
    fee_rate = tc_bps / 10_000.0

    for ticker in tickers:
        frame = _prepare_strategy_frame(market_data[ticker], family, strategy_params, timeframe)
        if frame.empty:
            continue
        prepared_frames[ticker] = frame

    if not prepared_frames:
        raise ValueError("No market data was available after applying the selected timeframe.")

    all_dates = sorted(set().union(*[frame.index.tolist() for frame in prepared_frames.values()]))
    if not all_dates:
        raise ValueError("No bars were available for the requested timeframe.")

    active_positions: Dict[str, Position] = {}
    trade_log: List[Dict[str, Any]] = []
    equity_rows: List[Dict[str, Any]] = []
    cash = float(initial_capital)
    risk = risk_controls or {}
    buy_and_hold = (
        _build_buy_and_hold_benchmark(
            prepared_frames,
            tickers,
            allocation_weights,
            all_dates=all_dates,
            initial_capital=initial_capital,
            tc_bps=tc_bps,
            allow_fractional_shares=allow_fractional_shares,
            periods_per_year=PERIODS_PER_YEAR[timeframe],
            generate_plots=generate_plots,
        )
        if include_buy_and_hold
        else None
    )

    for bar_number, current_date in enumerate(all_dates):
        for ticker, frame in prepared_frames.items():
            if current_date in frame.index:
                last_prices[ticker] = float(frame.loc[current_date, "Close"])

        exit_tickers: List[str] = []
        for ticker, position in list(active_positions.items()):
            frame = prepared_frames[ticker]
            if current_date not in frame.index:
                continue

            row = frame.loc[current_date]
            exit_price, exit_reason, highest_price = _compute_exit_signal(position, row, risk)
            position.highest_price = highest_price
            if exit_price is None or exit_reason is None:
                continue

            gross_exit_value = position.shares * exit_price
            exit_fee = gross_exit_value * fee_rate
            cash += gross_exit_value - exit_fee

            gross_pnl = (exit_price - position.entry_price) * position.shares
            net_pnl = gross_pnl - position.entry_fee - exit_fee
            capital_committed = (position.entry_price * position.shares) + position.entry_fee
            net_return_pct = (net_pnl / capital_committed * 100.0) if capital_committed > 0 else 0.0

            trade_log.append(
                {
                    "ticker": ticker,
                    "entry_date": position.entry_date.strftime("%Y-%m-%d"),
                    "exit_date": pd.to_datetime(current_date).strftime("%Y-%m-%d"),
                    "entry_price": position.entry_price,
                    "exit_price": exit_price,
                    "shares": position.shares,
                    "gross_pnl": gross_pnl,
                    "net_pnl": net_pnl,
                    "net_return_pct": net_return_pct,
                    "holding_period_bars": max(1, bar_number - position.entry_bar),
                    "exit_reason": exit_reason,
                }
            )
            exit_tickers.append(ticker)

        for ticker in exit_tickers:
            active_positions.pop(ticker, None)

        entry_candidates: List[Tuple[str, pd.Series]] = []
        for ticker, frame in prepared_frames.items():
            if ticker in active_positions or current_date not in frame.index:
                continue
            row = frame.loc[current_date]
            if bool(row.get("entry_signal", False)):
                entry_candidates.append((ticker, row))

        equity_before_entries = cash + _mark_to_market(active_positions, last_prices)
        for ticker, row in entry_candidates:
            if cash <= 0:
                break

            target_weight_pct = allocation_weights.get(ticker, 0.0)
            target_allocation = equity_before_entries * (target_weight_pct / 100.0)
            if target_allocation <= 0:
                continue

            price = float(row["Close"])
            if price <= 0:
                continue

            allocation = min(target_allocation, cash)
            raw_shares = allocation / (price * (1.0 + fee_rate))
            shares = raw_shares if allow_fractional_shares else math.floor(raw_shares)

            if shares <= 0:
                continue

            gross_cost = shares * price
            entry_fee = gross_cost * fee_rate
            total_cost = gross_cost + entry_fee
            if total_cost > cash:
                if allow_fractional_shares:
                    shares = cash / (price * (1.0 + fee_rate))
                    gross_cost = shares * price
                    entry_fee = gross_cost * fee_rate
                    total_cost = gross_cost + entry_fee
                else:
                    max_shares = math.floor(cash / (price * (1.0 + fee_rate)))
                    if max_shares <= 0:
                        continue
                    shares = max_shares
                    gross_cost = shares * price
                    entry_fee = gross_cost * fee_rate
                    total_cost = gross_cost + entry_fee

            if total_cost <= 0 or total_cost > cash:
                continue

            cash -= total_cost
            active_positions[ticker] = Position(
                ticker=ticker,
                shares=shares,
                entry_date=pd.to_datetime(current_date),
                entry_price=price,
                entry_fee=entry_fee,
                entry_bar=bar_number,
                highest_price=float(row["High"]),
            )

        market_value = _mark_to_market(active_positions, last_prices)
        equity = cash + market_value
        benchmark_equity = None
        benchmark_drawdown_pct = None
        if buy_and_hold and bar_number < len(buy_and_hold["equity_curve"]):
            benchmark_row = buy_and_hold["equity_curve"][bar_number]
            benchmark_equity = benchmark_row.get("Equity")
            benchmark_drawdown_pct = benchmark_row.get("DrawdownPct")
        equity_rows.append(
            {
                "Date": pd.to_datetime(current_date),
                "Cash": cash,
                "MarketValue": market_value,
                "Equity": equity,
                "BuyHoldEquity": benchmark_equity,
                "BuyHoldDrawdownPct": benchmark_drawdown_pct,
                "ActivePositions": len(active_positions),
            }
        )

    if active_positions:
        final_date = pd.to_datetime(all_dates[-1])
        for ticker, position in list(active_positions.items()):
            exit_price = last_prices.get(ticker, position.entry_price)
            gross_exit_value = position.shares * exit_price
            exit_fee = gross_exit_value * fee_rate
            gross_pnl = (exit_price - position.entry_price) * position.shares
            net_pnl = gross_pnl - position.entry_fee - exit_fee
            capital_committed = (position.entry_price * position.shares) + position.entry_fee
            net_return_pct = (net_pnl / capital_committed * 100.0) if capital_committed > 0 else 0.0
            trade_log.append(
                {
                    "ticker": ticker,
                    "entry_date": position.entry_date.strftime("%Y-%m-%d"),
                    "exit_date": final_date.strftime("%Y-%m-%d"),
                    "entry_price": position.entry_price,
                    "exit_price": exit_price,
                    "shares": position.shares,
                    "gross_pnl": gross_pnl,
                    "net_pnl": net_pnl,
                    "net_return_pct": net_return_pct,
                    "holding_period_bars": max(1, len(all_dates) - 1 - position.entry_bar),
                    "exit_reason": "end_of_backtest",
                }
            )

    equity_df = pd.DataFrame(equity_rows).set_index("Date")
    equity_df["DailyReturn"] = equity_df["Equity"].pct_change().fillna(0.0)
    equity_df["RollingMax"] = equity_df["Equity"].cummax()
    equity_df["DrawdownPct"] = (
        ((equity_df["RollingMax"] - equity_df["Equity"]) / equity_df["RollingMax"]).fillna(0.0) * 100.0
    )

    stats = _summarize_portfolio_stats(
        equity_df,
        trade_log,
        initial_capital=initial_capital,
        periods_per_year=PERIODS_PER_YEAR[timeframe],
    )

    plot = (
        generate_equity_curve_plot(
            equity_df.index,
            equity_df["Equity"],
            benchmark=equity_df["BuyHoldEquity"] if include_buy_and_hold else None,
        )
        if generate_plots
        else None
    )
    return {
        "stats": stats,
        "equity_curve": _serialize_records(
            equity_df[
                [
                    "Cash",
                    "MarketValue",
                    "Equity",
                    "BuyHoldEquity",
                    "DailyReturn",
                    "DrawdownPct",
                    "BuyHoldDrawdownPct",
                    "ActivePositions",
                ]
            ]
        ),
        "buy_and_hold": buy_and_hold,
        "trade_log": [{key: _clean_numeric(value) for key, value in trade.items()} for trade in trade_log],
        "equity_curve_image": plot,
    }


def _summarize_portfolio_stats(
    equity_df: pd.DataFrame,
    trade_log: List[Dict[str, Any]],
    *,
    initial_capital: float,
    periods_per_year: int,
) -> Dict[str, Any]:
    if equity_df.empty:
        return {
            "initial_capital": round(initial_capital, 2),
            "final_equity": round(initial_capital, 2),
            "total_return_pct": 0.0,
            "cagr_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "win_rate_pct": 0.0,
            "average_trade_return_pct": 0.0,
            "profit_factor": 0.0,
            "sharpe_ratio": 0.0,
            "trade_count": 0,
            "average_holding_period_bars": 0.0,
            "expectancy_pct": 0.0,
        }

    final_equity = float(equity_df["Equity"].iloc[-1])
    total_return_pct = ((final_equity / initial_capital) - 1.0) * 100.0 if initial_capital > 0 else 0.0

    start_date = pd.to_datetime(equity_df.index.min()).date()
    end_date = pd.to_datetime(equity_df.index.max()).date()
    years = max((end_date - start_date).days / 365.25, 0.0)
    cagr_pct = (((final_equity / initial_capital) ** (1.0 / years)) - 1.0) * 100.0 if years > 0 else 0.0

    daily_returns = equity_df["DailyReturn"].dropna()
    volatility = float(daily_returns.std(ddof=0))
    sharpe_ratio = (
        float((daily_returns.mean() / volatility) * math.sqrt(periods_per_year))
        if volatility > 0
        else 0.0
    )
    max_drawdown_pct = float(equity_df["DrawdownPct"].max()) if not equity_df.empty else 0.0

    trade_count = len(trade_log)
    wins = [trade for trade in trade_log if float(trade["net_pnl"]) > 0]
    losses = [trade for trade in trade_log if float(trade["net_pnl"]) < 0]
    win_rate_pct = (len(wins) / trade_count * 100.0) if trade_count else 0.0
    average_trade_return_pct = (
        float(np.mean([float(trade["net_return_pct"]) for trade in trade_log])) if trade_log else 0.0
    )

    total_profit = float(sum(float(trade["net_pnl"]) for trade in wins))
    total_loss = float(sum(abs(float(trade["net_pnl"])) for trade in losses))
    profit_factor = (total_profit / total_loss) if total_loss > 0 else (999.0 if total_profit > 0 else 0.0)

    average_holding_period_bars = (
        float(np.mean([float(trade["holding_period_bars"]) for trade in trade_log])) if trade_log else 0.0
    )
    average_win_pct = float(np.mean([float(trade["net_return_pct"]) for trade in wins])) if wins else 0.0
    average_loss_pct = float(np.mean([abs(float(trade["net_return_pct"])) for trade in losses])) if losses else 0.0
    win_rate = len(wins) / trade_count if trade_count else 0.0
    expectancy_pct = (win_rate * average_win_pct) - ((1.0 - win_rate) * average_loss_pct)

    return {
        "initial_capital": round(initial_capital, 2),
        "final_equity": round(final_equity, 2),
        "total_return_pct": round(total_return_pct, 2),
        "cagr_pct": round(cagr_pct, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "win_rate_pct": round(win_rate_pct, 2),
        "average_trade_return_pct": round(average_trade_return_pct, 2),
        "profit_factor": round(profit_factor, 3),
        "sharpe_ratio": round(sharpe_ratio, 3),
        "trade_count": trade_count,
        "average_holding_period_bars": round(average_holding_period_bars, 2),
        "expectancy_pct": round(expectancy_pct, 2),
    }


def run_portfolio_backtest(
    market_data: Dict[str, pd.DataFrame],
    *,
    tickers: List[str],
    allocation_weights: Dict[str, Any] | None,
    timeframe: str,
    initial_capital: float,
    tc_bps: float,
    allow_fractional_shares: bool,
    family: str,
    strategy_params: Dict[str, Any],
    risk_controls: Dict[str, Any] | None,
    tuning: Dict[str, Any] | None,
    include_buy_and_hold: bool,
    generate_plots: bool,
) -> Dict[str, Any]:
    selected_params = dict(strategy_params)
    tuning_summary = None
    normalized_weights, cash_reserve_pct = _normalize_allocation_weights(tickers, allocation_weights)

    if tuning and tuning.get("enabled"):
        combinations = _build_parameter_grid(
            family,
            selected_params,
            tuning.get("parameter_ranges") or {},
            int(tuning.get("max_combinations") or 100),
        )
        objective = tuning.get("objective") or "sharpe_ratio"
        trials: List[Dict[str, Any]] = []

        for params in combinations:
            outcome = _run_single_backtest(
                market_data,
                tickers=tickers,
                allocation_weights=normalized_weights,
                timeframe=timeframe,
                initial_capital=initial_capital,
                tc_bps=tc_bps,
                allow_fractional_shares=allow_fractional_shares,
                family=family,
                strategy_params=params,
                risk_controls=risk_controls,
                include_buy_and_hold=False,
                generate_plots=False,
            )
            stats = outcome["stats"]
            trials.append(
                {
                    "params": params,
                    "stats": stats,
                    "objective_value": round(_objective_value(stats, objective), 6),
                }
            )

        ranked_trials = sorted(
            trials,
            key=lambda trial: _objective_value(trial["stats"], objective),
            reverse=True,
        )
        selected_params = dict(ranked_trials[0]["params"])
        tuning_summary = {
            "enabled": True,
            "objective": objective,
            "evaluated_combinations": len(ranked_trials),
            "best_params": {key: _clean_numeric(value) for key, value in selected_params.items()},
            "top_trials": [
                {
                    "params": {key: _clean_numeric(value) for key, value in trial["params"].items()},
                    "stats": trial["stats"],
                    "objective_value": trial["objective_value"],
                }
                for trial in ranked_trials[:10]
            ],
        }

    result = _run_single_backtest(
        market_data,
        tickers=tickers,
        allocation_weights=normalized_weights,
        timeframe=timeframe,
        initial_capital=initial_capital,
        tc_bps=tc_bps,
        allow_fractional_shares=allow_fractional_shares,
        family=family,
        strategy_params=selected_params,
        risk_controls=risk_controls,
        include_buy_and_hold=include_buy_and_hold,
        generate_plots=generate_plots,
    )
    result["strategy_params"] = {key: _clean_numeric(value) for key, value in selected_params.items()}
    result["allocation_weights"] = normalized_weights
    result["cash_reserve_pct"] = cash_reserve_pct
    result["tuning_summary"] = tuning_summary
    return result
