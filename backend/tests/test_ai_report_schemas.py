from app.ai.schemas import AIReportOutput


def _valid_report(**overrides):
    report = {
        "swing_bias": "neutral",
        "setup_type": "Base breakout",
        "action_label": "wait",
        "confidence_score": 50,
        "setup_quality_score": 50,
        "entry_timing_score": 50,
        "technical_score": 50,
        "fundamental_score": 50,
        "sentiment_score": 50,
        "valuation_score": 50,
        "risk_score": 50,
        "main_thesis": "Thesis.",
        "why_it_could_move": "Move reason.",
        "why_it_could_fail": "Failure reason.",
        "entry_zone": "Near support.",
        "confirmation_trigger": "Close above resistance.",
        "entry_commentary": "Entry commentary.",
        "invalidation_level": "Below support.",
        "invalidation": "Invalidation.",
        "target_1": "First resistance.",
        "target_2": "Second resistance.",
        "risk_reward_summary": "Risk reward summary.",
        "watchlist_action": "Monitor for trigger.",
        "confirmation_signals": ["Volume confirmation"],
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
