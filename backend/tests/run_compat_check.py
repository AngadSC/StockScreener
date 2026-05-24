"""Backward-compat check: old cached reports (no trade_card) still deserialize correctly."""
import sys
sys.path.insert(0, ".")

from app.ai.schemas import AIReportOutput

base = {
    "action_label": "neutral_wait",
    "directional_bias": "neutral",
    "timeframe_ratings": {
        "short_term": {"rating": "watch", "timeframe": "1-10 trading days", "confidence_score": 50, "reason": "test"},
        "swing": {"rating": "watch", "timeframe": "2-8 weeks", "confidence_score": 50, "reason": "test"},
        "long_term": {"rating": "hold", "timeframe": "6-24 months", "confidence_score": 50, "reason": "test"},
    },
    "price_action_structure": {
        "setup_label": "no_clear_setup", "structure_label": "insufficient_data",
        "breakout_label": "insufficient_data", "pullback_label": "insufficient_data",
        "range_label": "insufficient_data", "gap_label": "insufficient_data",
        "labels": ["no_clear_setup"], "near_20d_high": False, "near_60d_high": False,
        "distance_to_support_pct": None, "distance_to_resistance_pct": None,
        "range_compression": False, "higher_highs_higher_lows": False, "lower_highs_lower_lows": False,
        "gap_up_recent": False, "gap_down_recent": False, "failed_breakout": False, "breakout_attempt": False,
        "pullback_to_sma20": False, "pullback_to_sma50": False, "support_level": None,
        "resistance_level": None, "prior_20d_resistance": None, "sma_20": None, "sma_50": None, "sma_200": None,
    },
    "setup_type": "no_clear_setup",
    "confidence_score": 0, "setup_quality_score": 0, "entry_timing_score": 0,
    "technical_score": 0, "price_structure_score": 0, "volume_score": 0,
    "momentum_score": 0, "trend_score": 0, "fundamental_score": 0,
    "revenue_earnings_quality_score": 0, "sentiment_score": 0, "news_score": 0,
    "valuation_score": 0, "risk_score": 0, "risk_reward_score": 0,
    "short_term_score": 0, "swing_trade_score": 0, "long_term_score": 0,
    "trade_read": "test", "main_thesis": "test", "entry_zone": "test",
    "confirmation_trigger": "test", "invalidation_level": "test",
    "target_1": "test", "target_2": "test", "risk_reward_summary": "test",
    "why_it_could_move": "test", "why_it_could_fail": "test",
    "confirmation_signals": ["test"], "watchlist_action": "test",
    "news_summary": "test", "final_verdict": "test",
}

r1 = AIReportOutput.model_validate(base)
assert r1.trade_card is None, f"Expected None, got {r1.trade_card}"
print("Test 1 (no trade_card key): PASS — trade_card =", r1.trade_card)

base["trade_card"] = None
r2 = AIReportOutput.model_validate(base)
assert r2.trade_card is None, f"Expected None, got {r2.trade_card}"
print("Test 2 (trade_card=None explicit): PASS — trade_card =", r2.trade_card)

print("\nAll backward-compat checks PASSED")
