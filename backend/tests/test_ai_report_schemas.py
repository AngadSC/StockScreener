from app.ai.llm_client import _attach_deterministic_report_fields
from app.ai.schemas import AIEvidenceOutput, AIReportOutput


def _valid_report(**overrides):
    report = {
        "action_label": "long_watchlist",
        "directional_bias": "neutral",
        "timeframe_ratings": {
            "short_term": {
                "rating": "watch",
                "timeframe": "1-10 trading days",
                "confidence_score": 55,
                "reason": "Short-term confirmation is missing.",
            },
            "swing": {
                "rating": "watch",
                "timeframe": "2-8 weeks",
                "confidence_score": 60,
                "reason": "Swing setup needs a confirmed break above resistance.",
            },
            "long_term": {
                "rating": "unknown",
                "timeframe": "6-24 months",
                "confidence_score": 20,
                "reason": "Long-term evidence is incomplete.",
            },
        },
        "price_action_structure": {
            "setup_label": "breakout_attempt",
            "structure_label": "higher_highs_higher_lows",
            "breakout_label": "breakout_attempt",
            "pullback_label": "pullback_to_sma20",
            "range_label": "normal_range",
            "gap_label": "no_recent_gap",
            "labels": ["breakout_attempt", "pullback_to_sma20"],
            "near_20d_high": True,
            "near_60d_high": False,
            "distance_to_support_pct": 3.2,
            "distance_to_resistance_pct": 5.8,
            "range_compression": False,
            "higher_highs_higher_lows": True,
            "lower_highs_lower_lows": False,
            "gap_up_recent": False,
            "gap_down_recent": False,
            "failed_breakout": False,
            "breakout_attempt": True,
            "pullback_to_sma20": True,
            "pullback_to_sma50": False,
            "support_level": 100,
            "resistance_level": 110,
            "prior_20d_resistance": 110,
            "sma_20": 102,
            "sma_50": 98,
            "sma_200": 90,
        },
        "setup_type": "base_breakout",
        "confidence_score": 50,
        "setup_quality_score": 50,
        "entry_timing_score": 50,
        "technical_score": 50,
        "price_structure_score": 50,
        "volume_score": 50,
        "momentum_score": 50,
        "trend_score": 50,
        "fundamental_score": 50,
        "revenue_earnings_quality_score": 50,
        "sentiment_score": 50,
        "news_score": 50,
        "valuation_score": 50,
        "risk_score": 50,
        "risk_reward_score": 50,
        "short_term_score": 50,
        "swing_trade_score": 50,
        "long_term_score": 50,
        "trade_read": "Watch for confirmation.",
        "main_thesis": "Thesis.",
        "entry_zone": "Near support.",
        "confirmation_trigger": "Close above resistance.",
        "invalidation_level": "Below support.",
        "target_1": "First resistance.",
        "target_2": "Second resistance.",
        "risk_reward_summary": "Risk reward summary.",
        "why_it_could_move": "Move reason.",
        "why_it_could_fail": "Failure reason.",
        "confirmation_signals": ["Volume confirmation"],
        "watchlist_action": "Monitor for trigger.",
        "news_summary": "News summary.",
        "final_verdict": "Verdict.",
    }
    report.update(overrides)
    return report


def test_ai_evidence_output_normalizes_string_lists_and_setup_type() -> None:
    evidence = AIEvidenceOutput.model_validate(
        {
            "bull_case": "Breakout attempt with improving volume.",
            "bear_case": ["  Resistance is still nearby.  "],
            "setup_type": "Breakout-retest / momentum continuation near resistance",
            "missing_data": [],
        }
    )

    assert evidence.bull_case == ["Breakout attempt with improving volume."]
    assert evidence.bear_case == ["Resistance is still nearby."]
    assert evidence.setup_type == "Breakout-retest / momentum continuation near"
    assert evidence.missing_data == ["None identified from provided data."]


def test_ai_report_output_normalizes_verbose_directional_bias() -> None:
    report = AIReportOutput.model_validate(
        _valid_report(directional_bias="Bullish (trend continuation)")
    )

    assert report.directional_bias == "bullish"


def test_ai_report_output_shortens_verbose_setup_type() -> None:
    report = AIReportOutput.model_validate(
        _valid_report(setup_type="Breakout-retest / momentum continuation near resistance")
    )

    assert report.setup_type == "Breakout retest"


def test_ai_report_output_normalizes_legacy_action_label() -> None:
    report = AIReportOutput.model_validate(_valid_report(action_label="wait"))

    assert report.action_label == "long_watchlist"


def test_ai_report_output_allows_mixed_directional_bias() -> None:
    report = AIReportOutput.model_validate(_valid_report(directional_bias="mixed bearish lean"))

    assert report.directional_bias == "mixed_bearish_lean"


def test_ai_report_output_accepts_legacy_swing_bias_key() -> None:
    legacy_report = _valid_report()
    legacy_report["swing_bias"] = legacy_report.pop("directional_bias")

    report = AIReportOutput.model_validate(legacy_report)

    assert report.directional_bias == "neutral"


def test_ai_report_output_normalizes_timeframe_ratings() -> None:
    report = AIReportOutput.model_validate(
        _valid_report(
            timeframe_ratings={
                "short_term": {
                    "rating": "wait for confirmation",
                    "timeframe": "1-10 trading days",
                    "confidence_score": 45,
                    "reason": "Needs volume.",
                },
                "swing": {
                    "rating": "buy_setup",
                    "timeframe": "2-8 weeks",
                    "confidence_score": 70,
                    "reason": "Breakout path is clear.",
                },
                "long_term": {
                    "rating": "insufficient_data",
                    "timeframe": "6-24 months",
                    "confidence_score": 10,
                    "reason": "Fundamentals are missing.",
                },
            }
        )
    )

    assert report.timeframe_ratings.short_term.rating == "watch"
    assert report.timeframe_ratings.swing.rating == "buy"
    assert report.timeframe_ratings.long_term.rating == "unknown"


def test_deterministic_report_fields_override_llm_scores() -> None:
    candidate = _valid_report(
        technical_score=1,
        volume_score=2,
        news_score=3,
        risk_reward_score=4,
        swing_trade_score=5,
    )
    payload = {
        "technical_summary": {
            "price_action_structure": {
                **candidate["price_action_structure"],
                "setup_label": "confirmed_breakout",
            }
        },
        "deterministic_scores": {
            "technical_score": 71,
            "volume_score": 82,
            "news_score": 63,
            "sentiment_score": 63,
            "risk_reward_score": 57,
            "swing_trade_score": 74,
        },
    }

    report = AIReportOutput.model_validate(_attach_deterministic_report_fields(candidate, payload))

    assert report.technical_score == 71
    assert report.volume_score == 82
    assert report.news_score == 63
    assert report.sentiment_score == 63
    assert report.risk_reward_score == 57
    assert report.swing_trade_score == 74
    assert report.price_action_structure.setup_label == "confirmed_breakout"
