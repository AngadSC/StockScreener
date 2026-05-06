from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AIReportInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str = Field(..., min_length=1, max_length=10)
    analysis_type: str = Field(..., min_length=1, max_length=50)
    timeframe: str = Field(..., min_length=1, max_length=20)
    market_data: Dict[str, Any] = Field(default_factory=dict)
    technical_data: Dict[str, Any] = Field(default_factory=dict)
    fundamental_data: Dict[str, Any] = Field(default_factory=dict)
    valuation_data: Dict[str, Any] = Field(default_factory=dict)
    news_data: List[Dict[str, Any]] = Field(default_factory=list)
    constraints: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class AIReportOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    swing_bias: str = Field(..., min_length=1, max_length=20)
    setup_type: str = Field(..., min_length=1, max_length=50)
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
    entry_commentary: str = Field(..., min_length=1)
    invalidation: str = Field(..., min_length=1)
    confirmation_signals: List[str] = Field(default_factory=list)
    news_summary: str = Field(..., min_length=1)
    final_verdict: str = Field(..., min_length=1)


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
