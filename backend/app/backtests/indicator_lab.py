from __future__ import annotations

import math
from typing import Dict, Iterable, Tuple

import numpy as np
import pandas as pd
from ta.momentum import (
    AwesomeOscillatorIndicator,
    ROCIndicator,
    RSIIndicator,
    StochasticOscillator,
    TSIIndicator,
    WilliamsRIndicator,
)
from ta.trend import ADXIndicator, AroonIndicator, EMAIndicator, MACD, SMAIndicator
from ta.volatility import AverageTrueRange, BollingerBands
from ta.volume import (
    ChaikinMoneyFlowIndicator,
    MFIIndicator,
    OnBalanceVolumeIndicator,
)

from app.backtests.core import apply_signals, find_close_col, prepare_returns, summarize
from app.backtests.plots import generate_equity_curve_plot, generate_roc_curve_plot

try:
    from sklearn.metrics import roc_auc_score, roc_curve
except ImportError:
    roc_auc_score = None
    roc_curve = None


INDICATOR_DEFAULTS: Dict[str, Dict[str, object]] = {
    "rsi": {"weight": 1.0, "params": {"period": 14, "buy_below": 30.0, "sell_above": 70.0}},
    "stoch": {"weight": 1.0, "params": {"k": 14, "d": 3}},
    "willr": {"weight": 1.0, "params": {"period": 14, "buy_below": -80.0, "sell_above": -20.0}},
    "roc": {"weight": 1.0, "params": {"period": 12, "buy_above": 0.0, "sell_below": 0.0}},
    "tsi": {"weight": 1.0, "params": {"slow": 25, "fast": 13, "buy_above": 0.0, "sell_below": 0.0}},
    "ao": {"weight": 1.0, "params": {"fast": 5, "slow": 34, "buy_above": 0.0, "sell_below": 0.0}},
    "sma_xo": {"weight": 1.0, "params": {"fast": 10, "slow": 50}},
    "ema_xo": {"weight": 1.0, "params": {"fast": 12, "slow": 26}},
    "macd": {"weight": 1.0, "params": {"fast": 12, "slow": 26, "signal": 9}},
    "adx": {"weight": 1.0, "params": {"period": 14, "adx_min": 20.0}},
    "aroon": {"weight": 1.0, "params": {"period": 14}},
    "bbands": {"weight": 1.0, "params": {"window": 20, "n_std": 2.0}},
    "obv": {"weight": 1.0, "params": {"window": 5}},
    "mfi": {"weight": 1.0, "params": {"period": 14, "buy_below": 20.0, "sell_above": 80.0}},
    "cmf": {"weight": 1.0, "params": {"period": 20, "threshold": 0.0}},
}

ATR_GATE_DEFAULTS = {"enabled": False, "params": {"period": 14, "close_pct": 0.02}}


def _find_col(df: pd.DataFrame, prefix: str) -> str:
    matches = [c for c in df.columns if str(c).startswith(prefix)]
    if not matches:
        raise ValueError(f"No {prefix}* column found in DataFrame.")
    return sorted(matches, key=len)[0]


def _high_low_volume_cols(df: pd.DataFrame) -> Tuple[str, str, str]:
    return _find_col(df, "High"), _find_col(df, "Low"), _find_col(df, "Volume")


def _coerce_float(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _coerce_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _enabled_config(indicators: Dict[str, Dict[str, object]], key: str) -> Dict[str, object] | None:
    config = indicators.get(key)
    if not config or not bool(config.get("enabled")):
        return None
    merged = {
        "enabled": True,
        "weight": _coerce_float(config.get("weight"), INDICATOR_DEFAULTS[key]["weight"]),
        "params": dict(INDICATOR_DEFAULTS[key]["params"]),  # type: ignore[arg-type]
    }
    merged["params"].update(config.get("params") or {})
    return merged


def _merge_gate_config(gate: Dict[str, object] | None) -> Dict[str, object]:
    merged = {"enabled": ATR_GATE_DEFAULTS["enabled"], "params": dict(ATR_GATE_DEFAULTS["params"])}
    if gate:
        merged["enabled"] = bool(gate.get("enabled", False))
        merged["params"].update(gate.get("params") or {})
    return merged


def _add_forward_return(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    close_col = find_close_col(out)
    out["Forward_Return_1d"] = (out[close_col].shift(-1) / out[close_col]) - 1.0
    return out


def sig_threshold(
    series: pd.Series,
    *,
    buy_below=None,
    sell_above=None,
    buy_above=None,
    sell_below=None,
    name=None,
) -> pd.Series:
    s = pd.Series(0.0, index=series.index, name=name or f"Sig_{series.name}")
    if buy_below is not None:
        s[series < buy_below] = 1.0
    if sell_above is not None:
        s[series > sell_above] = -1.0
    if buy_above is not None:
        s[series > buy_above] = 1.0
    if sell_below is not None:
        s[series < sell_below] = -1.0
    return s


def sig_crossover(fast: pd.Series, slow: pd.Series, name: str) -> pd.Series:
    prev = fast.shift(1) - slow.shift(1)
    curr = fast - slow
    up = (prev <= 0) & (curr > 0)
    dn = (prev >= 0) & (curr < 0)
    s = pd.Series(0.0, index=fast.index, name=name)
    s[up] = 1.0
    s[dn] = -1.0
    return s


def combine_signals(signals: Dict[str, pd.Series], weights: Dict[str, float]) -> pd.Series:
    df = pd.DataFrame(signals).fillna(0.0)
    w = np.array([weights.get(k, 1.0) for k in df.columns], dtype=float)
    score = df.to_numpy() @ w
    denom = np.abs(w).sum() or 1.0
    score = score / denom
    return pd.Series(score, index=df.index, name="Score_weighted")


def apply_gate(score: pd.Series, gate: pd.Series | None) -> pd.Series:
    if gate is None:
        return score
    g = gate.reindex(score.index).fillna(0.0)
    return (score * g).rename(score.name)


def score_to_signal(score: pd.Series, *, long_thr: float = 0.5, short_thr: float = -0.5) -> pd.Series:
    s = pd.Series(0.0, index=score.index, name="Signal")
    s[score >= long_thr] = 1.0
    s[score <= short_thr] = -1.0
    return s


def _compute_roc_auc(df: pd.DataFrame, score: pd.Series) -> Tuple[float | None, str | None]:
    if roc_auc_score is None or roc_curve is None:
        return None, None

    if "Forward_Return_1d" not in df.columns:
        return None, None

    y_true = (df["Forward_Return_1d"] > 0).astype(int)
    mask = (~score.isna()) & (~y_true.isna())
    y_true = y_true[mask]
    y_score = score[mask]

    if len(y_true) < 10 or len(set(y_true.tolist())) < 2:
        return None, None

    auc = float(roc_auc_score(y_true, y_score))
    fpr, tpr, _ = roc_curve(y_true, y_score)
    return auc, generate_roc_curve_plot(fpr, tpr, auc)


def _serialize_frame(df: pd.DataFrame, columns: Iterable[str]) -> list[dict]:
    out = df.loc[:, list(columns)].copy()
    out = out.replace([np.inf, -np.inf], np.nan)
    out = out.reset_index().rename(columns={"index": "Date"})
    if "Date" not in out.columns:
        out = out.rename(columns={out.columns[0]: "Date"})
    out["Date"] = out["Date"].astype(str)
    records = []
    for row in out.to_dict(orient="records"):
        records.append(
            {
                key: (
                    None
                    if (isinstance(value, float) and math.isnan(value))
                    else round(float(value), 6)
                    if isinstance(value, (float, np.floating))
                    else int(value)
                    if isinstance(value, (np.integer,))
                    else value
                )
                for key, value in row.items()
            }
        )
    return records


def run_indicator_backtest(
    market_data: pd.DataFrame,
    indicators: Dict[str, Dict[str, object]],
    atr_gate: Dict[str, object] | None,
    *,
    long_threshold: float,
    short_threshold: float,
    exec_lag: int,
    tc_bps: float,
    allow_position_hold: bool,
    generate_plots: bool,
    generate_roc: bool,
) -> dict:
    df = prepare_returns(_add_forward_return(market_data))
    close_col = find_close_col(df)
    high_col, low_col, volume_col = _high_low_volume_cols(df)

    signals: Dict[str, pd.Series] = {}
    weights: Dict[str, float] = {}
    selected_indicators: list[str] = []

    rsi_cfg = _enabled_config(indicators, "rsi")
    if rsi_cfg:
        period = _coerce_int(rsi_cfg["params"].get("period"), 14)
        rsi_col = f"RSI_{period}"
        df[rsi_col] = RSIIndicator(df[close_col], window=period).rsi()
        signals["RSI"] = sig_threshold(
            df[rsi_col],
            buy_below=_coerce_float(rsi_cfg["params"].get("buy_below"), 30.0),
            sell_above=_coerce_float(rsi_cfg["params"].get("sell_above"), 70.0),
            name=f"Sig_{rsi_col}",
        )
        weights["RSI"] = _coerce_float(rsi_cfg.get("weight"), 1.0)
        selected_indicators.append("RSI")

    stoch_cfg = _enabled_config(indicators, "stoch")
    if stoch_cfg:
        k = _coerce_int(stoch_cfg["params"].get("k"), 14)
        d = _coerce_int(stoch_cfg["params"].get("d"), 3)
        so = StochasticOscillator(high=df[high_col], low=df[low_col], close=df[close_col], window=k, smooth_window=d)
        kcol, dcol = f"STOCHK_{k}", f"STOCHD_{k}_{d}"
        df[kcol] = so.stoch()
        df[dcol] = so.stoch_signal()
        signals["STOCH"] = sig_crossover(df[kcol], df[dcol], name=f"Sig_XO_{kcol}_{dcol}")
        weights["STOCH"] = _coerce_float(stoch_cfg.get("weight"), 1.0)
        selected_indicators.append("Stochastic")

    willr_cfg = _enabled_config(indicators, "willr")
    if willr_cfg:
        period = _coerce_int(willr_cfg["params"].get("period"), 14)
        col = f"WILLR_{period}"
        df[col] = WilliamsRIndicator(high=df[high_col], low=df[low_col], close=df[close_col], lbp=period).williams_r()
        signals["WILLR"] = sig_threshold(
            df[col],
            buy_below=_coerce_float(willr_cfg["params"].get("buy_below"), -80.0),
            sell_above=_coerce_float(willr_cfg["params"].get("sell_above"), -20.0),
            name=f"Sig_{col}",
        )
        weights["WILLR"] = _coerce_float(willr_cfg.get("weight"), 1.0)
        selected_indicators.append("Williams %R")

    roc_cfg = _enabled_config(indicators, "roc")
    if roc_cfg:
        period = _coerce_int(roc_cfg["params"].get("period"), 12)
        col = f"ROC_{period}"
        df[col] = ROCIndicator(df[close_col], window=period).roc()
        signals["ROC"] = sig_threshold(
            df[col],
            buy_above=_coerce_float(roc_cfg["params"].get("buy_above"), 0.0),
            sell_below=_coerce_float(roc_cfg["params"].get("sell_below"), 0.0),
            name=f"Sig_{col}",
        )
        weights["ROC"] = _coerce_float(roc_cfg.get("weight"), 1.0)
        selected_indicators.append("ROC")

    tsi_cfg = _enabled_config(indicators, "tsi")
    if tsi_cfg:
        slow = _coerce_int(tsi_cfg["params"].get("slow"), 25)
        fast = _coerce_int(tsi_cfg["params"].get("fast"), 13)
        col = f"TSI_{slow}_{fast}"
        df[col] = TSIIndicator(df[close_col], window_slow=slow, window_fast=fast).tsi()
        signals["TSI"] = sig_threshold(
            df[col],
            buy_above=_coerce_float(tsi_cfg["params"].get("buy_above"), 0.0),
            sell_below=_coerce_float(tsi_cfg["params"].get("sell_below"), 0.0),
            name=f"Sig_{col}",
        )
        weights["TSI"] = _coerce_float(tsi_cfg.get("weight"), 1.0)
        selected_indicators.append("TSI")

    ao_cfg = _enabled_config(indicators, "ao")
    if ao_cfg:
        fast = _coerce_int(ao_cfg["params"].get("fast"), 5)
        slow = _coerce_int(ao_cfg["params"].get("slow"), 34)
        col = f"AO_{fast}_{slow}"
        df[col] = AwesomeOscillatorIndicator(df[high_col], df[low_col], window1=fast, window2=slow).awesome_oscillator()
        signals["AO"] = sig_threshold(
            df[col],
            buy_above=_coerce_float(ao_cfg["params"].get("buy_above"), 0.0),
            sell_below=_coerce_float(ao_cfg["params"].get("sell_below"), 0.0),
            name=f"Sig_{col}",
        )
        weights["AO"] = _coerce_float(ao_cfg.get("weight"), 1.0)
        selected_indicators.append("Awesome Oscillator")

    sma_cfg = _enabled_config(indicators, "sma_xo")
    if sma_cfg:
        fast = _coerce_int(sma_cfg["params"].get("fast"), 10)
        slow = _coerce_int(sma_cfg["params"].get("slow"), 50)
        fcol, scol = f"SMA_{fast}", f"SMA_{slow}"
        df[fcol] = SMAIndicator(df[close_col], window=fast).sma_indicator()
        df[scol] = SMAIndicator(df[close_col], window=slow).sma_indicator()
        signals["SMA_XO"] = sig_crossover(df[fcol], df[scol], name=f"Sig_XO_{fcol}_{scol}")
        weights["SMA_XO"] = _coerce_float(sma_cfg.get("weight"), 1.0)
        selected_indicators.append("SMA Crossover")

    ema_cfg = _enabled_config(indicators, "ema_xo")
    if ema_cfg:
        fast = _coerce_int(ema_cfg["params"].get("fast"), 12)
        slow = _coerce_int(ema_cfg["params"].get("slow"), 26)
        fcol, scol = f"EMA_{fast}", f"EMA_{slow}"
        df[fcol] = EMAIndicator(df[close_col], window=fast).ema_indicator()
        df[scol] = EMAIndicator(df[close_col], window=slow).ema_indicator()
        signals["EMA_XO"] = sig_crossover(df[fcol], df[scol], name=f"Sig_XO_{fcol}_{scol}")
        weights["EMA_XO"] = _coerce_float(ema_cfg.get("weight"), 1.0)
        selected_indicators.append("EMA Crossover")

    macd_cfg = _enabled_config(indicators, "macd")
    if macd_cfg:
        fast = _coerce_int(macd_cfg["params"].get("fast"), 12)
        slow = _coerce_int(macd_cfg["params"].get("slow"), 26)
        signal = _coerce_int(macd_cfg["params"].get("signal"), 9)
        macd = MACD(df[close_col], window_fast=fast, window_slow=slow, window_sign=signal)
        mcol, scol = f"MACD_{fast}_{slow}_{signal}", f"MACDsig_{fast}_{slow}_{signal}"
        df[mcol] = macd.macd()
        df[scol] = macd.macd_signal()
        signals["MACD"] = sig_crossover(df[mcol], df[scol], name="Sig_MACD")
        weights["MACD"] = _coerce_float(macd_cfg.get("weight"), 1.0)
        selected_indicators.append("MACD")

    adx_cfg = _enabled_config(indicators, "adx")
    if adx_cfg:
        period = _coerce_int(adx_cfg["params"].get("period"), 14)
        adx_min = _coerce_float(adx_cfg["params"].get("adx_min"), 20.0)
        adx = ADXIndicator(high=df[high_col], low=df[low_col], close=df[close_col], window=period)
        adx_col, pdi_col, ndi_col = f"ADX_{period}", f"PDI_{period}", f"NDI_{period}"
        df[adx_col] = adx.adx()
        df[pdi_col] = adx.adx_pos()
        df[ndi_col] = adx.adx_neg()
        prev = df[pdi_col].shift(1) - df[ndi_col].shift(1)
        curr = df[pdi_col] - df[ndi_col]
        sig = pd.Series(0.0, index=df.index, name="Sig_ADX_DI")
        sig[(prev <= 0) & (curr > 0) & (df[adx_col] >= adx_min)] = 1.0
        sig[(prev >= 0) & (curr < 0) & (df[adx_col] >= adx_min)] = -1.0
        signals["ADX"] = sig
        weights["ADX"] = _coerce_float(adx_cfg.get("weight"), 1.0)
        selected_indicators.append("ADX")

    aroon_cfg = _enabled_config(indicators, "aroon")
    if aroon_cfg:
        period = _coerce_int(aroon_cfg["params"].get("period"), 14)
        aroon = AroonIndicator(high=df[high_col], low=df[low_col], window=period)
        up_col, dn_col = f"AROONUP_{period}", f"AROONDN_{period}"
        df[up_col] = aroon.aroon_up()
        df[dn_col] = aroon.aroon_down()
        signals["AROON"] = sig_crossover(df[up_col], df[dn_col], name=f"Sig_XO_{up_col}_{dn_col}")
        weights["AROON"] = _coerce_float(aroon_cfg.get("weight"), 1.0)
        selected_indicators.append("Aroon")

    bbands_cfg = _enabled_config(indicators, "bbands")
    if bbands_cfg:
        window = _coerce_int(bbands_cfg["params"].get("window"), 20)
        n_std = _coerce_float(bbands_cfg["params"].get("n_std"), 2.0)
        bb = BollingerBands(df[close_col], window=window, window_dev=n_std)
        up, mid, low = f"BB_UP_{window}_{n_std}", f"BB_MID_{window}", f"BB_LOW_{window}_{n_std}"
        df[up] = bb.bollinger_hband()
        df[mid] = bb.bollinger_mavg()
        df[low] = bb.bollinger_lband()
        sig = pd.Series(0.0, index=df.index, name="Sig_BBands")
        sig[df[close_col] < df[low]] = 1.0
        sig[df[close_col] > df[up]] = -1.0
        signals["BBANDS"] = sig
        weights["BBANDS"] = _coerce_float(bbands_cfg.get("weight"), 1.0)
        selected_indicators.append("Bollinger Bands")

    obv_cfg = _enabled_config(indicators, "obv")
    if obv_cfg:
        window = _coerce_int(obv_cfg["params"].get("window"), 5)
        obv_col = "OBV"
        df[obv_col] = OnBalanceVolumeIndicator(close=df[close_col], volume=df[volume_col]).on_balance_volume()
        slope = df[obv_col].diff(window)
        signals["OBV"] = sig_threshold(slope, buy_above=0.0, sell_below=0.0, name=f"Sig_OBVsl_{window}")
        weights["OBV"] = _coerce_float(obv_cfg.get("weight"), 1.0)
        selected_indicators.append("OBV")

    mfi_cfg = _enabled_config(indicators, "mfi")
    if mfi_cfg:
        period = _coerce_int(mfi_cfg["params"].get("period"), 14)
        col = f"MFI_{period}"
        df[col] = MFIIndicator(
            high=df[high_col],
            low=df[low_col],
            close=df[close_col],
            volume=df[volume_col],
            window=period,
        ).money_flow_index()
        signals["MFI"] = sig_threshold(
            df[col],
            buy_below=_coerce_float(mfi_cfg["params"].get("buy_below"), 20.0),
            sell_above=_coerce_float(mfi_cfg["params"].get("sell_above"), 80.0),
            name=f"Sig_{col}",
        )
        weights["MFI"] = _coerce_float(mfi_cfg.get("weight"), 1.0)
        selected_indicators.append("MFI")

    cmf_cfg = _enabled_config(indicators, "cmf")
    if cmf_cfg:
        period = _coerce_int(cmf_cfg["params"].get("period"), 20)
        threshold = _coerce_float(cmf_cfg["params"].get("threshold"), 0.0)
        col = f"CMF_{period}"
        df[col] = ChaikinMoneyFlowIndicator(
            high=df[high_col],
            low=df[low_col],
            close=df[close_col],
            volume=df[volume_col],
            window=period,
        ).chaikin_money_flow()
        signals["CMF"] = sig_threshold(
            df[col],
            buy_above=threshold,
            sell_below=(-threshold if threshold > 0 else 0.0),
            name=f"Sig_{col}",
        )
        weights["CMF"] = _coerce_float(cmf_cfg.get("weight"), 1.0)
        selected_indicators.append("CMF")

    gate_cfg = _merge_gate_config(atr_gate)
    gate_series = None
    if gate_cfg.get("enabled"):
        period = _coerce_int(gate_cfg["params"].get("period"), 14)
        close_pct = _coerce_float(gate_cfg["params"].get("close_pct"), 0.02)
        atr_col = f"ATR_{period}"
        df[atr_col] = AverageTrueRange(
            high=df[high_col],
            low=df[low_col],
            close=df[close_col],
            window=period,
        ).average_true_range()
        gate_series = ((df[atr_col] / df[close_col]) >= close_pct).astype(float).rename("Gate_ATR")

    if not signals:
        raise ValueError("Select at least one indicator before running the backtest.")

    score = combine_signals(signals, weights)
    score = apply_gate(score, gate_series)
    signal = score_to_signal(score, long_thr=long_threshold, short_thr=short_threshold)

    out = df.copy()
    out["Score"] = score
    out["Signal"] = signal
    out = apply_signals(
        out,
        "Signal",
        exec_lag=exec_lag,
        tc_bps=tc_bps,
        allow_position_hold=allow_position_hold,
    )

    stats = summarize(out)
    roc_auc = None
    roc_plot = None
    if generate_roc:
        roc_auc, roc_plot = _compute_roc_auc(df, score)

    equity_plot = generate_equity_curve_plot(out.index, out["Equity"]) if generate_plots else None
    results_columns = [
        close_col,
        "Ret_1d",
        "Forward_Return_1d",
        "Score",
        "Signal",
        "Position",
        "Turnover",
        "Cost",
        "StratRet",
        "Equity",
    ]

    return {
        "stats": stats,
        "selected_indicators": selected_indicators,
        "equity_curve": _serialize_frame(out, ["Equity", close_col, "Score", "Signal", "Position", "StratRet"]),
        "results": _serialize_frame(out, results_columns),
        "equity_curve_image": equity_plot,
        "roc_auc": round(roc_auc, 4) if roc_auc is not None else None,
        "roc_curve_image": roc_plot,
    }
