from __future__ import annotations

from statistics import mean
from typing import Any


SCORE_FIELDS = (
    "confidence_score",
    "setup_quality_score",
    "entry_timing_score",
    "technical_score",
    "price_structure_score",
    "volume_score",
    "momentum_score",
    "trend_score",
    "risk_score",
    "risk_reward_score",
    "news_score",
    "sentiment_score",
    "fundamental_score",
    "revenue_earnings_quality_score",
    "valuation_score",
    "short_term_score",
    "swing_trade_score",
    "long_term_score",
)


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric != numeric:
        return None
    return numeric


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _score(value: float) -> int:
    return int(round(_clamp(value)))


def _weighted(scores: dict[str, int], weights: dict[str, float]) -> int:
    usable = [(scores[key], weight) for key, weight in weights.items() if key in scores]
    if not usable:
        return 50
    total_weight = sum(weight for _, weight in usable)
    if total_weight <= 0:
        return 50
    return _score(sum(score * weight for score, weight in usable) / total_weight)


def _score_growth(value: Any) -> int | None:
    numeric = _number(value)
    if numeric is None:
        return None
    if numeric >= 0.30:
        return 90
    if numeric >= 0.15:
        return 78
    if numeric >= 0.05:
        return 64
    if numeric >= 0:
        return 52
    if numeric >= -0.10:
        return 38
    return 22


def _score_profitability(value: Any) -> int | None:
    numeric = _number(value)
    if numeric is None:
        return None
    if numeric >= 0.25:
        return 90
    if numeric >= 0.15:
        return 78
    if numeric >= 0.08:
        return 64
    if numeric >= 0:
        return 50
    return 25


def _average_or_neutral(values: list[int | None]) -> int:
    usable = [value for value in values if value is not None]
    if not usable:
        return 50
    return _score(mean(usable))


def _price_structure_score(technical_summary: dict[str, Any]) -> int:
    structure = technical_summary.get("price_action_structure") or {}
    if not isinstance(structure, dict):
        return 35

    value = 50.0
    setup_label = str(structure.get("setup_label") or "")
    breakout_label = str(structure.get("breakout_label") or "")
    pullback_label = str(structure.get("pullback_label") or "")

    if structure.get("higher_highs_higher_lows"):
        value += 16
    if structure.get("lower_highs_lower_lows"):
        value -= 24
    if structure.get("range_compression"):
        value += 7
    if structure.get("breakout_attempt"):
        value += 9
    if breakout_label == "confirmed_breakout" or setup_label == "confirmed_breakout":
        value += 18
    if structure.get("failed_breakout") or breakout_label == "failed_breakout":
        value -= 30
    if structure.get("pullback_to_sma20") or structure.get("pullback_to_sma50"):
        value += 8
    if "trend_pullback" in setup_label:
        value += 8
    if "base_compression" in setup_label:
        value += 5
    if "extended_above_sma20" in pullback_label:
        value -= 8
    if "below_key_sma" in pullback_label:
        value -= 12
    if structure.get("near_20d_high"):
        value += 4
    if structure.get("near_60d_high"):
        value += 4
    if structure.get("gap_up_recent"):
        value += 4
    if structure.get("gap_down_recent"):
        value -= 10

    support_distance = _number(structure.get("distance_to_support_pct"))
    resistance_distance = _number(structure.get("distance_to_resistance_pct"))
    if support_distance is not None:
        if 0 <= support_distance <= 5:
            value += 10
        elif support_distance > 12:
            value -= 12
    if resistance_distance is not None:
        if resistance_distance >= 8:
            value += 8
        elif 0 <= resistance_distance < 2:
            value -= 6

    return _score(value)


def _volume_score(volume_summary: dict[str, Any]) -> int:
    if not volume_summary:
        return 35

    value = 50.0
    relative_1d = _number(volume_summary.get("relative_volume_1d"))
    relative_5d = _number(volume_summary.get("relative_volume_5d"))
    up_down_ratio = _number(volume_summary.get("up_down_volume_ratio"))
    accumulation_days = _number(volume_summary.get("accumulation_days_20d"))
    distribution_days = _number(volume_summary.get("distribution_days_20d"))

    if relative_1d is not None:
        if relative_1d >= 1.5:
            value += 18
        elif relative_1d >= 1.1:
            value += 8
        elif relative_1d <= 0.7:
            value -= 8
    if relative_5d is not None:
        if relative_5d >= 1.2:
            value += 8
        elif relative_5d <= 0.7:
            value -= 5
    if up_down_ratio is not None:
        if up_down_ratio >= 1.5:
            value += 14
        elif up_down_ratio >= 1.1:
            value += 6
        elif up_down_ratio <= 0.8:
            value -= 12

    if accumulation_days is not None:
        value += min(12, accumulation_days * 1.5)
    if distribution_days is not None:
        value -= min(18, distribution_days * 2.5)

    obv_trend = volume_summary.get("obv_trend")
    if obv_trend == "up":
        value += 12
    elif obv_trend == "down":
        value -= 18

    confirmation = volume_summary.get("volume_price_confirmation")
    if confirmation == "confirmed":
        value += 12
    elif confirmation == "divergent":
        value -= 18

    if volume_summary.get("breakout_volume_confirmed"):
        value += 15
    if volume_summary.get("volume_dry_up_near_support"):
        value += 6

    return _score(value)


def _momentum_score(technical_summary: dict[str, Any]) -> int:
    trend = technical_summary.get("trend")
    value = {
        "strong_uptrend": 78,
        "uptrend": 68,
        "sideways": 48,
        "downtrend": 30,
        "strong_downtrend": 20,
        "insufficient_data": 35,
    }.get(str(trend), 45)

    for key, multiplier in (("return_5d", 160), ("return_20d", 95), ("return_60d", 55)):
        recent_return = _number(technical_summary.get("returns", {}).get(key) if isinstance(technical_summary.get("returns"), dict) else technical_summary.get(key))
        if recent_return is not None:
            value += _clamp(recent_return * multiplier, -12, 12)

    rsi = _number(technical_summary.get("rsi_14"))
    if rsi is not None:
        if 45 <= rsi <= 65:
            value += 8
        elif 65 < rsi <= 75:
            value += 3
        elif rsi > 80:
            value -= 10
        elif rsi < 35:
            value -= 8

    return _score(value)


def _risk_reward_score(
    technical_summary: dict[str, Any],
    volume_summary: dict[str, Any],
    fundamental_summary: dict[str, Any],
) -> int:
    structure = technical_summary.get("price_action_structure") or {}
    latest = technical_summary.get("latest_candle") or {}
    if not isinstance(structure, dict):
        structure = {}
    if not isinstance(latest, dict):
        latest = {}

    value = 50.0
    support_distance = _number(structure.get("distance_to_support_pct"))
    resistance_distance = _number(structure.get("distance_to_resistance_pct"))
    if support_distance is not None and resistance_distance is not None and support_distance > 0:
        reward_risk = resistance_distance / support_distance
        if reward_risk >= 2:
            value += 25
        elif reward_risk >= 1.5:
            value += 15
        elif reward_risk < 1:
            value -= 15
    if support_distance is not None:
        if 0 <= support_distance <= 4:
            value += 10
        elif support_distance > 12:
            value -= 14

    close = _number(latest.get("close"))
    atr = _number(technical_summary.get("atr_14"))
    if close not in (None, 0) and atr is not None:
        atr_pct = atr / close
        if atr_pct > 0.08:
            value -= 16
        elif atr_pct > 0.04:
            value -= 7
        elif 0.01 <= atr_pct <= 0.04:
            value += 5

    if structure.get("failed_breakout"):
        value -= 18
    if structure.get("gap_down_recent"):
        value -= 8
    if volume_summary.get("volume_price_confirmation") == "divergent":
        value -= 10
    if volume_summary.get("obv_trend") == "down":
        value -= 8

    metrics = fundamental_summary.get("metrics") if isinstance(fundamental_summary, dict) else {}
    beta = _number(metrics.get("beta") if isinstance(metrics, dict) else None)
    debt_to_equity = _number(metrics.get("debt_to_equity") if isinstance(metrics, dict) else None)
    if beta is not None:
        if beta > 1.8:
            value -= 10
        elif beta <= 1.1:
            value += 4
    if debt_to_equity is not None:
        if debt_to_equity > 200:
            value -= 8
        elif debt_to_equity <= 80:
            value += 4

    return _score(value)


def _news_score(news: dict[str, Any]) -> int:
    articles = news.get("articles") if isinstance(news, dict) else []
    if not isinstance(articles, list) or not articles:
        return 50

    value = 50.0 + min(8, len(articles) * 1.5)
    for article in articles[:10]:
        if not isinstance(article, dict):
            continue
        sentiment = article.get("sentiment")
        if sentiment == "positive":
            value += 8
        elif sentiment == "negative":
            value -= 10

    return _score(value)


def _fundamental_score(fundamental_summary: dict[str, Any]) -> int:
    if not fundamental_summary.get("available"):
        return 50
    metrics = fundamental_summary.get("metrics") or {}
    if not isinstance(metrics, dict):
        return 50

    profitability = _average_or_neutral(
        [
            _score_profitability(metrics.get("profit_margin")),
            _score_profitability(metrics.get("operating_margin")),
            _score_profitability(metrics.get("roe")),
            _score_profitability(metrics.get("roa")),
        ]
    )
    liquidity = _average_or_neutral(
        [
            80 if (current := _number(metrics.get("current_ratio"))) is not None and current >= 1.5 else 55 if current is not None and current >= 1 else 35 if current is not None else None,
            80 if (quick := _number(metrics.get("quick_ratio"))) is not None and quick >= 1 else 50 if quick is not None and quick >= 0.7 else 35 if quick is not None else None,
        ]
    )
    debt = _number(metrics.get("debt_to_equity"))
    debt_score = None
    if debt is not None:
        debt_score = 85 if debt <= 50 else 70 if debt <= 100 else 45 if debt <= 200 else 25

    return _average_or_neutral([profitability, liquidity, debt_score])


def _revenue_earnings_quality_score(fundamental_summary: dict[str, Any]) -> int:
    if not fundamental_summary.get("available"):
        return 50
    metrics = fundamental_summary.get("metrics") or {}
    if not isinstance(metrics, dict):
        return 50
    return _average_or_neutral(
        [
            _score_growth(metrics.get("revenue_growth")),
            _score_growth(metrics.get("earnings_growth")),
        ]
    )


def _valuation_score(valuation_summary: dict[str, Any]) -> int:
    if not valuation_summary.get("available"):
        return 50
    metrics = valuation_summary.get("metrics") or {}
    if not isinstance(metrics, dict):
        return 50

    pe = _number(metrics.get("forward_pe") or metrics.get("pe_ratio"))
    peg = _number(metrics.get("peg_ratio"))
    ps = _number(metrics.get("price_to_sales"))
    ev_ebitda = _number(metrics.get("ev_to_ebitda"))
    scores: list[int | None] = []

    if pe is not None:
        scores.append(85 if 0 < pe <= 15 else 70 if pe <= 25 else 50 if pe <= 40 else 30)
    if peg is not None:
        scores.append(85 if 0 < peg <= 1 else 70 if peg <= 1.8 else 45 if peg <= 3 else 25)
    if ps is not None:
        scores.append(80 if 0 < ps <= 3 else 65 if ps <= 7 else 45 if ps <= 12 else 25)
    if ev_ebitda is not None:
        scores.append(80 if 0 < ev_ebitda <= 10 else 65 if ev_ebitda <= 16 else 45 if ev_ebitda <= 25 else 25)

    return _average_or_neutral(scores)


def build_deterministic_scores(
    *,
    technical_summary: dict[str, Any],
    volume_summary: dict[str, Any],
    fundamental_summary: dict[str, Any],
    valuation_summary: dict[str, Any],
    news: dict[str, Any],
    data_quality: dict[str, Any],
) -> dict[str, int | dict[str, dict[str, float]]]:
    price_structure = _price_structure_score(technical_summary)
    volume = _volume_score(volume_summary)
    momentum = _momentum_score(technical_summary)
    trend = momentum
    risk_reward = _risk_reward_score(technical_summary, volume_summary, fundamental_summary)
    news_score = _news_score(news)
    fundamental = _fundamental_score(fundamental_summary)
    revenue_earnings = _revenue_earnings_quality_score(fundamental_summary)
    valuation = _valuation_score(valuation_summary)
    risk = risk_reward
    technical = _weighted(
        {
            "price_structure": price_structure,
            "volume": volume,
            "momentum": momentum,
        },
        {"price_structure": 0.40, "volume": 0.30, "momentum": 0.30},
    )
    short_term = _weighted(
        {
            "volume": volume,
            "price_action": price_structure,
            "catalyst_news": news_score,
            "momentum": momentum,
            "risk_reward": risk_reward,
        },
        {"volume": 0.30, "price_action": 0.30, "catalyst_news": 0.20, "momentum": 0.10, "risk_reward": 0.10},
    )
    swing_trade = _weighted(
        {
            "price_structure": price_structure,
            "volume_confirmation": volume,
            "trend_momentum": momentum,
            "risk_reward": risk_reward,
            "news_catalyst": news_score,
        },
        {"price_structure": 0.30, "volume_confirmation": 0.25, "trend_momentum": 0.20, "risk_reward": 0.15, "news_catalyst": 0.10},
    )
    long_term = _weighted(
        {
            "fundamentals": fundamental,
            "revenue_earnings_quality": revenue_earnings,
            "valuation": valuation,
            "trend": trend,
            "news_catalyst": news_score,
            "risk": risk,
        },
        {"fundamentals": 0.35, "revenue_earnings_quality": 0.25, "valuation": 0.15, "trend": 0.10, "news_catalyst": 0.10, "risk": 0.05},
    )

    warnings = data_quality.get("warnings") if isinstance(data_quality, dict) else []
    errors = data_quality.get("errors") if isinstance(data_quality, dict) else []
    quality_penalty = min(15, len(warnings or []) * 3 + len(errors or []) * 5)
    confidence = _score((swing_trade * 0.70) + (technical * 0.30) - quality_penalty)

    return {
        "confidence_score": confidence,
        "setup_quality_score": swing_trade,
        "entry_timing_score": short_term,
        "technical_score": technical,
        "price_structure_score": price_structure,
        "volume_score": volume,
        "momentum_score": momentum,
        "trend_score": trend,
        "risk_score": risk,
        "risk_reward_score": risk_reward,
        "news_score": news_score,
        "sentiment_score": news_score,
        "fundamental_score": fundamental,
        "revenue_earnings_quality_score": revenue_earnings,
        "valuation_score": valuation,
        "short_term_score": short_term,
        "swing_trade_score": swing_trade,
        "long_term_score": long_term,
        "weighting_models": {
            "short_term": {
                "volume": 0.30,
                "price_action": 0.30,
                "catalyst_news": 0.20,
                "momentum": 0.10,
                "risk_reward": 0.10,
            },
            "swing_trade": {
                "price_structure": 0.30,
                "volume_confirmation": 0.25,
                "trend_momentum": 0.20,
                "risk_reward": 0.15,
                "news_catalyst": 0.10,
            },
            "long_term": {
                "fundamentals": 0.35,
                "revenue_earnings_quality": 0.25,
                "valuation": 0.15,
                "trend": 0.10,
                "news_catalyst": 0.10,
                "risk": 0.05,
            },
        },
    }
