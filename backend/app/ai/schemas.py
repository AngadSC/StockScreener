from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    constraints: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class AIReportOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    swing_bias: str = Field(..., min_length=1, max_length=20)
    setup_type: str = Field(..., min_length=1, max_length=50)
    action_label: str = Field(..., min_length=1)
    confidence_score: float = Field(..., ge=0.0, le=100.0)
    setup_quality_score: float = Field(..., ge=0.0, le=100.0)
    entry_timing_score: float = Field(..., ge=0.0, le=100.0)
    technical_score: float = Field(..., ge=0.0, le=100.0)
    fundamental_score: float = Field(..., ge=0.0, le=100.0)
    sentiment_score: float = Field(..., ge=0.0, le=100.0)
    valuation_score: float = Field(..., ge=0.0, le=100.0)
    risk_score: float = Field(..., ge=0.0, le=100.0)
    main_thesis: str = Field(..., min_length=1)
    why_it_could_move: str = Field(..., min_length=1)
    why_it_could_fail: str = Field(..., min_length=1)
    entry_zone: str = Field(..., min_length=1)
    confirmation_trigger: str = Field(..., min_length=1)
    entry_commentary: str = Field(..., min_length=1)
    invalidation_level: str = Field(..., min_length=1)
    invalidation: str = Field(..., min_length=1)
    target_1: str = Field(..., min_length=1)
    target_2: str = Field(..., min_length=1)
    risk_reward_summary: str = Field(..., min_length=1)
    watchlist_action: str = Field(..., min_length=1)
    confirmation_signals: List[str] = Field(default_factory=list)
    news_summary: str = Field(..., min_length=1)
    final_verdict: str = Field(..., min_length=1)

    @field_validator("swing_bias", mode="before")
    @classmethod
    def normalize_swing_bias(cls, value: Any) -> str:
        cleaned = _clean_short_text(value)
        lower_value = cleaned.lower()
        if "bullish" in lower_value:
            return "bullish"
        if "bearish" in lower_value:
            return "bearish"
        if any(label in lower_value for label in ("neutral", "mixed", "sideways", "range-bound")):
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
