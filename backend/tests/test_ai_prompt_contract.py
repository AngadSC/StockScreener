from app.ai.prompt_builder import OUTPUT_FIELDS, OUTPUT_FORMAT_INSTRUCTIONS, OUTPUT_RESPONSE_SCHEMA
from app.ai.schemas import AIReportOutput


def test_output_response_schema_requires_ui_report_fields() -> None:
    assert OUTPUT_RESPONSE_SCHEMA["additionalProperties"] is False
    assert OUTPUT_RESPONSE_SCHEMA["required"] == list(OUTPUT_FIELDS)
    assert set(OUTPUT_RESPONSE_SCHEMA["properties"]) == set(AIReportOutput.model_fields)
    assert OUTPUT_RESPONSE_SCHEMA["properties"]["confirmation_signals"] == {
        "type": "array",
        "items": {"type": "string"},
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
    assert OUTPUT_RESPONSE_SCHEMA["properties"]["swing_bias"]["maxLength"] == 20
    assert OUTPUT_RESPONSE_SCHEMA["properties"]["setup_type"]["maxLength"] == 50


def test_output_instructions_warn_against_input_payload_shape() -> None:
    assert "top-level keys only" in OUTPUT_FORMAT_INSTRUCTIONS
    assert "swing_bias" in OUTPUT_FORMAT_INSTRUCTIONS
    assert "action_label" in OUTPUT_FORMAT_INSTRUCTIONS
    assert "entry_zone" in OUTPUT_FORMAT_INSTRUCTIONS
    assert "watchlist_action" in OUTPUT_FORMAT_INSTRUCTIONS
    assert "setup_quality_score" in OUTPUT_FORMAT_INSTRUCTIONS
    assert "Do not return the input payload" in OUTPUT_FORMAT_INSTRUCTIONS
    assert "max 20 characters" in OUTPUT_FORMAT_INSTRUCTIONS
    assert "max 50 characters" in OUTPUT_FORMAT_INSTRUCTIONS
