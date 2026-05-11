from app.ai.schemas import AIReportOutput


def _valid_report(**overrides):
    report = {
        "action_label": "watchlist",
        "swing_bias": "neutral",
        "setup_type": "base_breakout",
        "confidence_score": 50,
        "setup_quality_score": 50,
        "entry_timing_score": 50,
        "technical_score": 50,
        "fundamental_score": 50,
        "sentiment_score": 50,
        "valuation_score": 50,
        "risk_score": 50,
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


def test_ai_report_output_normalizes_verbose_swing_bias() -> None:
    report = AIReportOutput.model_validate(
        _valid_report(swing_bias="Bullish (trend continuation)")
    )

    assert report.swing_bias == "bullish"


def test_ai_report_output_shortens_verbose_setup_type() -> None:
    report = AIReportOutput.model_validate(
        _valid_report(setup_type="Breakout-retest / momentum continuation near resistance")
    )

    assert report.setup_type == "Breakout retest"


def test_ai_report_output_normalizes_legacy_action_label() -> None:
    report = AIReportOutput.model_validate(_valid_report(action_label="wait"))

    assert report.action_label == "watchlist"


def test_ai_report_output_allows_mixed_swing_bias() -> None:
    report = AIReportOutput.model_validate(_valid_report(swing_bias="mixed signals"))

    assert report.swing_bias == "mixed"
