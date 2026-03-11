"""
Generic backtest utilities (strategy-agnostic).

Adapted from the existing standalone backtester so the API can reuse the same
signal-to-position execution logic.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def find_close_col(df: pd.DataFrame) -> str:
    """Auto-detect the Close column (works with suffixed names)."""
    cols = [c for c in df.columns if str(c).startswith("Close")]
    if not cols:
        raise ValueError("No Close* column found in DataFrame.")
    return sorted(cols, key=len)[0]


def _max_drawdown(equity: pd.Series) -> float:
    """Return max drawdown as a fraction (e.g., 0.25 = 25%)."""
    roll_max = equity.cummax()
    dd = (roll_max - equity) / roll_max
    return float(dd.max()) if len(dd) else 0.0


def prepare_returns(df: pd.DataFrame, close_col: str | None = None) -> pd.DataFrame:
    """Ensure a clean daily return series from Close."""
    out = df.copy()
    if close_col is None:
        close_col = find_close_col(out)
    out["Ret_1d"] = out[close_col].pct_change()
    return out


def apply_signals(
    df: pd.DataFrame,
    signal_col: str,
    *,
    close_col: str | None = None,
    exec_lag: int = 1,
    tc_bps: float = 0.0,
    clip_signal: bool = True,
    allow_position_hold: bool = True,
) -> pd.DataFrame:
    """
    Turn point-in-time signals into a tradable PnL stream.
    """
    out = df.copy()

    if "Ret_1d" not in out.columns:
        if close_col is None:
            close_col = find_close_col(out)
        out["Ret_1d"] = out[close_col].pct_change()

    sig = pd.to_numeric(out[signal_col], errors="coerce").fillna(0.0)
    if clip_signal:
        sig = sig.clip(-1, 1)
    out["Sig_raw"] = sig

    sig_lag = sig.shift(exec_lag).fillna(0.0)

    if allow_position_hold:
        pos = sig_lag.replace(0, np.nan).ffill().fillna(0.0)
    else:
        pos = sig_lag

    pos = pos.clip(-1, 1)
    out["Sig_lag"] = sig_lag
    out["Position"] = pos

    turnover = pos.diff().abs().fillna(abs(pos.fillna(0.0)))
    cost_per_unit = tc_bps / 10_000.0
    out["Turnover"] = turnover
    out["Cost"] = -turnover * cost_per_unit

    out["StratRet"] = (pos * out["Ret_1d"].fillna(0.0)) + out["Cost"].fillna(0.0)
    out["Equity"] = (1.0 + out["StratRet"]).cumprod()

    return out


def summarize(out: pd.DataFrame) -> dict:
    """Compute key metrics from apply_signals() output."""
    sr = out["StratRet"].dropna()
    eq = out["Equity"].dropna()

    total_return = float(eq.iloc[-1] - 1.0) if len(eq) else 0.0
    n_days = len(sr)
    cagr = (eq.iloc[-1] ** (252 / n_days) - 1.0) if (len(eq) > 1 and n_days > 0) else 0.0

    mu = sr.mean()
    sigma = sr.std(ddof=0)
    vol_ann = sigma * np.sqrt(252) if sigma > 0 else 0.0
    sharpe = (mu / sigma * np.sqrt(252)) if sigma > 0 else 0.0

    maxdd = _max_drawdown(eq)

    turnover = out.get("Turnover", pd.Series(index=out.index, dtype=float)).fillna(0.0)
    trades = int((turnover > 0).sum())

    in_pos = out.get("Position", pd.Series(index=out.index, dtype=float)).abs() > 0
    trade_days = sr[in_pos.fillna(False)]
    wins = int((trade_days > 0).sum())
    used_days = len(trade_days)
    win_rate = (wins / used_days * 100.0) if used_days else 0.0
    avg_trade_ret_bp = trade_days.mean() * 10_000 if used_days else 0.0

    return {
        "total_return_%": round(total_return * 100, 2),
        "cagr_%": round(cagr * 100, 2),
        "vol_%": round(vol_ann * 100, 2),
        "sharpe_252": round(sharpe, 3),
        "max_drawdown_%": round(maxdd * 100, 2),
        "trades": trades,
        "win_rate_%": round(win_rate, 2),
        "avg_trade_ret_bp": round(float(avg_trade_ret_bp), 2),
        "bars": int(n_days),
    }
