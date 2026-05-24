from datetime import datetime
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _clean_short_text(value: Any) -> str:
    return " ".join(str(value).strip().split())


def _truncate_at_word(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value

    truncated = value[:max_length].rstrip()
    if " " in truncated:
        truncated = truncated.rsplit(" ", 1)[0].rstrip(" -/,")
    return truncated or value[:max_length].rstrip()


class AIReportInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str = Field(..., min_length=1, max_length=10)
    analysis_type: str = Field(..., min_length=1, max_length=50)
    timeframe: str = Field(..., min_length=1, max_length=20)
    generated_at: str = Field(..., min_length=1)
    company_profile: Dict[str, Any] = Field(default_factory=dict)
    price_history: Dict[str, Any] = Field(default_factory=dict)
    technical_summary: Dict[str, Any] = Field(default_factory=dict)
    volume_summary: Dict[str, Any] = Field(default_factory=dict)
    fundamental_summary: Dict[str, Any] = Field(default_factory=dict)
    valuation_summary: Dict[str, Any] = Field(default_factory=dict)
    news: Dict[str, Any] = Field(default_factory=dict)
    data_quality: Dict[str, Any] = Field(default_factory=dict)
    deterministic_scores: Dict[str, Any] = Field(default_factory=dict)
    constraints: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class AIEvidenceOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bull_case: List[str] = Field(..., min_length=1)
    bear_case: List[str] = Field(..., min_length=1)
    setup_type: str = Field(..., min_length=1, max_length=50)
    missing_data: List[str] = Field(..., min_length=1)

    @field_validator("bull_case", "bear_case", "missing_data", mode="before")
    @classmethod
    def normalize_string_list(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            return value

        cleaned = [_clean_short_text(item) for item in value if _clean_short_text(item)]
        return cleaned or ["None identified from provided data."]

    @field_validator("setup_type", mode="before")
    @classmethod
    def normalize_setup_type(cls, value: Any) -> str:
        return _truncate_at_word(_clean_short_text(value), 50)


class TradeLevels(BaseModel):
    model_config = ConfigDict(extra="allow")

    current_price: float | None = None
    preferred_entry: float | None = None
    aggressive_entry_min: float | None = None
    aggressive_entry_max: float | None = None
    confirmation_trigger: float | None = None
    add_level: float | None = None
    invalidation_level: float | None = None
    target_1: float | None = None
    target_2: float | None = None
    chase_above: float | None = None
    method: str | None = None
    warnings: List[str] = []


TradeCardDecision = Literal[
    "Long Setup Active",
    "Conditional Long",
    "Bullish Watch",
    "No Trade",
    "Conditional Short",
    "Short Setup Active",
    "Avoid",
    "High Risk",
]

TradeCardBestAction = Literal[
    "buy_now",
    "wait_for_breakout",
    "wait_for_pullback",
    "hold_if_in",
    "avoid",
    "short_now",
    "wait_for_breakdown",
]

TradeCardConfidence = Literal["low", "moderate", "strong", "very_strong"]


class IfThenPlan(BaseModel):
    model_config = ConfigDict(extra="allow")

    if_trigger_hits: str
    if_rejects: str
    if_breaks_invalidation: str
    if_already_holding: str
    if_missed_entry: str


class AITradeCard(BaseModel):
    model_config = ConfigDict(extra="allow")

    decision: TradeCardDecision
    ai_lean: Literal["bullish", "bearish", "neutral"]
    best_action_now: TradeCardBestAction
    verdict: str = Field(..., min_length=1, max_length=300)
    setup_type: str = Field(..., min_length=1, max_length=60)
    confidence_label: TradeCardConfidence
    setup_score: float = Field(..., ge=0.0, le=100.0)
    trade_levels: TradeLevels
    main_reason: str = Field(..., min_length=1, max_length=400)
    main_risk: str = Field(..., min_length=1, max_length=400)
    bull_case: List[str] = Field(..., min_length=1)
    bear_case: List[str] = Field(..., min_length=1)
    if_then_plan: IfThenPlan


ActionLabel = Literal[
    "actionable_long",
    "long_watchlist",
    "neutral_wait",
    "short_watchlist",
    "actionable_short",
    "avoid",
    "high_risk",
]
DirectionalBias = Literal[
    "bullish",
    "bearish",
    "neutral",
    "mixed_bullish_lean",
    "mixed_bearish_lean",
]
TradeRating = Literal["buy", "watch", "avoid"]
LongTermRating = Literal["accumulate", "hold", "avoid", "unknown"]


class PriceActionStructure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    setup_label: str = Field(..., min_length=1, max_length=60)
    structure_label: str = Field(..., min_length=1, max_length=60)
    breakout_label: str = Field(..., min_length=1, max_length=60)
    pullback_label: str = Field(..., min_length=1, max_length=60)
    range_label: str = Field(..., min_length=1, max_length=60)
    gap_label: str = Field(..., min_length=1, max_length=60)
    labels: List[str] = Field(..., min_length=1)
    near_20d_high: bool
    near_60d_high: bool
    distance_to_support_pct: float | None = Field(...)
    distance_to_resistance_pct: float | None = Field(...)
    range_compression: bool
    higher_highs_higher_lows: bool
    lower_highs_lower_lows: bool
    gap_up_recent: bool
    gap_down_recent: bool
    failed_breakout: bool
    breakout_attempt: bool
    pullback_to_sma20: bool
    pullback_to_sma50: bool
    support_level: float | None = Field(...)
    resistance_level: float | None = Field(...)
    prior_20d_resistance: float | None = Field(...)
    sma_20: float | None = Field(...)
    sma_50: float | None = Field(...)
    sma_200: float | None = Field(...)


class TradeTimeframeRating(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rating: TradeRating
    timeframe: Literal["1-10 trading days", "2-8 weeks"]
    confidence_score: float = Field(..., ge=0.0, le=100.0)
    reason: str = Field(..., min_length=1)

    @field_validator("rating", mode="before")
    @classmethod
    def normalize_trade_rating(cls, value: Any) -> str:
        cleaned = _clean_short_text(value).lower().replace("-", "_").replace(" ", "_")
        if cleaned in {"buy", "buy_setup", "actionable", "act_now", "accumulate"}:
            return "buy"
        if cleaned in {"watch", "watchlist", "wait", "neutral", "hold", "monitor", "wait_for_confirmation"}:
            return "watch"
        if cleaned in {"avoid", "pass", "sell", "high_risk", "weak_setup"}:
            return "avoid"
        return cleaned


class LongTermTimeframeRating(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rating: LongTermRating
    timeframe: Literal["6-24 months"]
    confidence_score: float = Field(..., ge=0.0, le=100.0)
    reason: str = Field(..., min_length=1)

    @field_validator("rating", mode="before")
    @classmethod
    def normalize_long_term_rating(cls, value: Any) -> str:
        cleaned = _clean_short_text(value).lower().replace("-", "_").replace(" ", "_")
        if cleaned in {"buy", "buy_setup", "accumulate", "strong_buy"}:
            return "accumulate"
        if cleaned in {"watch", "watchlist", "neutral", "hold", "monitor"}:
            return "hold"
        if cleaned in {"avoid", "pass", "sell", "high_risk"}:
            return "avoid"
        if cleaned in {"unknown", "insufficient_data", "not_enough_data", "unclear"}:
            return "unknown"
        return cleaned


class TimeframeRatings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    short_term: TradeTimeframeRating
    swing: TradeTimeframeRating
    long_term: LongTermTimeframeRating

    @field_validator("short_term")
    @classmethod
    def require_short_term_timeframe(cls, value: TradeTimeframeRating) -> TradeTimeframeRating:
        if value.timeframe != "1-10 trading days":
            raise ValueError("short_term timeframe must be 1-10 trading days")
        return value

    @field_validator("swing")
    @classmethod
    def require_swing_timeframe(cls, value: TradeTimeframeRating) -> TradeTimeframeRating:
        if value.timeframe != "2-8 weeks":
            raise ValueError("swing timeframe must be 2-8 weeks")
        return value


class AIReportOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_label: ActionLabel
    directional_bias: DirectionalBias
    timeframe_ratings: TimeframeRatings
    price_action_structure: PriceActionStructure
    setup_type: str = Field(..., min_length=1, max_length=50)
    confidence_score: float = Field(..., ge=0.0, le=100.0)
    setup_quality_score: float = Field(..., ge=0.0, le=100.0)
    entry_timing_score: float = Field(..., ge=0.0, le=100.0)
    technical_score: float = Field(..., ge=0.0, le=100.0)
    price_structure_score: float = Field(..., ge=0.0, le=100.0)
    volume_score: float = Field(..., ge=0.0, le=100.0)
    momentum_score: float = Field(..., ge=0.0, le=100.0)
    trend_score: float = Field(..., ge=0.0, le=100.0)
    fundamental_score: float = Field(..., ge=0.0, le=100.0)
    revenue_earnings_quality_score: float = Field(..., ge=0.0, le=100.0)
    sentiment_score: float = Field(..., ge=0.0, le=100.0)
    news_score: float = Field(..., ge=0.0, le=100.0)
    valuation_score: float = Field(..., ge=0.0, le=100.0)
    risk_score: float = Field(..., ge=0.0, le=100.0)
    risk_reward_score: float = Field(..., ge=0.0, le=100.0)
    short_term_score: float = Field(..., ge=0.0, le=100.0)
    swing_trade_score: float = Field(..., ge=0.0, le=100.0)
    long_term_score: float = Field(..., ge=0.0, le=100.0)
    trade_read: str = Field(..., min_length=1)
    main_thesis: str = Field(..., min_length=1)
    entry_zone: str = Field(..., min_length=1)
    confirmation_trigger: str = Field(..., min_length=1)
    invalidation_level: str = Field(..., min_length=1)
    target_1: str = Field(..., min_length=1)
    target_2: str = Field(..., min_length=1)
    risk_reward_summary: str = Field(..., min_length=1)
    why_it_could_move: str = Field(..., min_length=1)
    why_it_could_fail: str = Field(..., min_length=1)
    confirmation_signals: List[str] = Field(default_factory=list, min_length=1)
    watchlist_action: str = Field(..., min_length=1)
    news_summary: str = Field(..., min_length=1)
    final_verdict: str = Field(..., min_length=1)
    trade_card: AITradeCard | None = None

    @field_validator("trade_card", mode="before")
    @classmethod
    def validate_trade_card(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, dict):
            return AITradeCard.model_validate(value)
        return value

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_bias_key(cls, value: Any) -> Any:
        if isinstance(value, dict) and "directional_bias" not in value and "swing_bias" in value:
            normalized = dict(value)
            normalized["directional_bias"] = normalized.pop("swing_bias")
            return normalized
        return value

    @field_validator("action_label", mode="before")
    @classmethod
    def normalize_action_label(cls, value: Any) -> str:
        cleaned = _clean_short_text(value).lower().replace("-", "_").replace(" ", "_")
        if cleaned in {
            "buy",
            "buy_setup",
            "act_now",
            "actionable",
            "actionable_bullish",
            "actionable_long",
            "long",
        }:
            return "actionable_long"
        if cleaned in {
            "buy_watch",
            "wait",
            "monitor",
            "watch",
            "watchlist",
            "bullish_watch",
            "long_watch",
            "long_watchlist",
            "wait_for_confirmation",
        }:
            return "long_watchlist"
        if cleaned in {
            "hold",
            "no_clear_edge",
            "no_clear_setup",
            "mixed",
            "neutral",
            "neutral_wait",
            "review_existing_report",
        }:
            return "neutral_wait"
        if cleaned in {"bearish_watch", "short_watch", "short_watchlist"}:
            return "short_watchlist"
        if cleaned in {"sell", "short", "actionable_bearish", "actionable_short"}:
            return "actionable_short"
        if cleaned in {"pass", "avoid", "weak_setup"}:
            return "avoid"
        if cleaned in {"high_risk", "risky", "speculative", "elevated_risk"}:
            return "high_risk"
        return cleaned

    @field_validator("directional_bias", mode="before")
    @classmethod
    def normalize_directional_bias(cls, value: Any) -> str:
        cleaned = _clean_short_text(value)
        lower_value = cleaned.lower()
        if any(label in lower_value for label in ("mixed_bearish", "bearish lean", "bearish_lean")):
            return "mixed_bearish_lean"
        if any(label in lower_value for label in ("mixed_bullish", "bullish lean", "bullish_lean")):
            return "mixed_bullish_lean"
        if "bullish" in lower_value:
            return "bullish"
        if "bearish" in lower_value:
            return "bearish"
        if any(label in lower_value for label in ("mixed", "conflicted", "two-sided")):
            return "mixed_bullish_lean"
        if any(label in lower_value for label in ("neutral", "sideways", "range-bound", "range bound")):
            return "neutral"
        return _truncate_at_word(cleaned, 20)

    @field_validator("setup_type", mode="before")
    @classmethod
    def normalize_setup_type(cls, value: Any) -> str:
        cleaned = _clean_short_text(value)
        lower_value = cleaned.lower()
        if "breakout" in lower_value and "retest" in lower_value:
            return "Breakout retest"
        if "momentum" in lower_value and "continuation" in lower_value:
            return "Momentum continuation"
        if "pullback" in lower_value:
            return "Pullback entry"
        if "breakout" in lower_value:
            return "Breakout"
        return _truncate_at_word(cleaned, 50)


class AIReportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str = Field(..., min_length=1, max_length=10)
    created_at: datetime
    cached: bool
    tier_used: str = Field(..., min_length=1, max_length=20)
    report: AIReportOutput

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()
