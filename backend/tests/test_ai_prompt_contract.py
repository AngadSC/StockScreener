from app.ai.prompt_builder import (
    ACTIONABLE_OUTPUT_INSTRUCTIONS,
    DECISION_RULES,
    OUTPUT_FIELDS,
    OUTPUT_FORMAT_INSTRUCTIONS,
    OUTPUT_RESPONSE_SCHEMA,
    SYSTEM_PROMPT,
    SYSTEM_ROLE,
)
from app.ai.schemas import AIReportOutput


def test_output_response_schema_requires_ui_report_fields() -> None:
    assert OUTPUT_RESPONSE_SCHEMA["additionalProperties"] is False
    assert OUTPUT_RESPONSE_SCHEMA["required"] == list(OUTPUT_FIELDS)
    assert set(OUTPUT_RESPONSE_SCHEMA["properties"]) == set(AIReportOutput.model_fields)
    assert OUTPUT_RESPONSE_SCHEMA["properties"]["confirmation_signals"] == {
        "type": "array",
        "items": {"type": "string", "minLength": 1},
        "minItems": 1,
    }
    assert OUTPUT_RESPONSE_SCHEMA["properties"]["technical_score"] == {
        "type": "number",
        "minimum": 0,
        "maximum": 100,
    }
    assert OUTPUT_RESPONSE_SCHEMA["properties"]["confidence_score"] == {
        "type": "number",
        "minimum": 0,
        "maximum": 100,
    }
    assert OUTPUT_RESPONSE_SCHEMA["properties"]["action_label"]["enum"] == [
        "actionable_long",
        "long_watchlist",
        "neutral_wait",
        "short_watchlist",
        "actionable_short",
        "avoid",
        "high_risk",
    ]
    assert OUTPUT_RESPONSE_SCHEMA["properties"]["directional_bias"]["enum"] == [
        "bullish",
        "bearish",
        "neutral",
        "mixed_bullish_lean",
        "mixed_bearish_lean",
    ]
    assert OUTPUT_RESPONSE_SCHEMA["properties"]["timeframe_ratings"]["additionalProperties"] is False
    assert OUTPUT_RESPONSE_SCHEMA["properties"]["timeframe_ratings"]["required"] == [
        "short_term",
        "swing",
        "long_term",
    ]
    assert OUTPUT_RESPONSE_SCHEMA["properties"]["timeframe_ratings"]["properties"]["short_term"]["properties"]["rating"]["enum"] == [
        "buy",
        "watch",
        "avoid",
    ]
    assert OUTPUT_RESPONSE_SCHEMA["properties"]["timeframe_ratings"]["properties"]["long_term"]["properties"]["rating"]["enum"] == [
        "accumulate",
        "hold",
        "avoid",
        "unknown",
    ]
    assert OUTPUT_RESPONSE_SCHEMA["properties"]["price_action_structure"]["additionalProperties"] is False
    assert "breakout_label" in OUTPUT_RESPONSE_SCHEMA["properties"]["price_action_structure"]["properties"]
    assert "confidence_score" in OUTPUT_RESPONSE_SCHEMA["properties"]["timeframe_ratings"]["properties"]["swing"]["properties"]
    assert OUTPUT_RESPONSE_SCHEMA["properties"]["setup_type"]["maxLength"] == 50


def test_output_instructions_warn_against_input_payload_shape() -> None:
    assert "top-level keys only" in OUTPUT_FORMAT_INSTRUCTIONS
    assert "directional_bias" in OUTPUT_FORMAT_INSTRUCTIONS
    assert "action_label" in OUTPUT_FORMAT_INSTRUCTIONS
    assert "entry_zone" in OUTPUT_FORMAT_INSTRUCTIONS
    assert "watchlist_action" in OUTPUT_FORMAT_INSTRUCTIONS
    assert "timeframe_ratings" in OUTPUT_FORMAT_INSTRUCTIONS
    assert "price_action_structure" in OUTPUT_FORMAT_INSTRUCTIONS
    assert "setup_quality_score" in OUTPUT_FORMAT_INSTRUCTIONS
    assert "deterministic_scores" in OUTPUT_FORMAT_INSTRUCTIONS
    assert "copied exactly from deterministic_scores" in OUTPUT_FORMAT_INSTRUCTIONS
    assert "Do not return the input payload" in OUTPUT_FORMAT_INSTRUCTIONS
    assert "max 50 characters" in OUTPUT_FORMAT_INSTRUCTIONS
    assert "actionable_long, long_watchlist, neutral_wait, short_watchlist, actionable_short, avoid, high_risk" in OUTPUT_FORMAT_INSTRUCTIONS
    assert "bullish, bearish, neutral, mixed_bullish_lean, mixed_bearish_lean" in OUTPUT_FORMAT_INSTRUCTIONS


def test_system_prompt_includes_decision_and_actionable_rubrics() -> None:
    assert SYSTEM_ROLE in SYSTEM_PROMPT
    assert DECISION_RULES in SYSTEM_PROMPT
    assert ACTIONABLE_OUTPUT_INSTRUCTIONS in SYSTEM_PROMPT
    assert "Do not force bullish or bearish output" in SYSTEM_PROMPT
    assert "final_verdict must clearly say" in SYSTEM_PROMPT
    assert "Treat volume_summary as primary evidence" in SYSTEM_PROMPT
    assert "technical_summary.price_action_structure" in SYSTEM_PROMPT
    assert "Every output score field must match" in SYSTEM_PROMPT
    assert "risk_score and risk_reward_score as quality scores" in SYSTEM_PROMPT
    assert "timeframe_ratings must separately evaluate" in SYSTEM_PROMPT
    assert "lagging indicators such as RSI, SMA" in SYSTEM_PROMPT
    assert "Distribution days, falling OBV" in SYSTEM_PROMPT
