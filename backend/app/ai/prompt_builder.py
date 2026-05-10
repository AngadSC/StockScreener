from __future__ import annotations

import json

from app.ai.schemas import AIReportOutput


OUTPUT_FIELDS = tuple(AIReportOutput.model_fields.keys())
SCORE_FIELDS = {
    "setup_quality_score",
    "entry_timing_score",
    "technical_score",
    "fundamental_score",
    "sentiment_score",
    "valuation_score",
    "risk_score",
}


def _response_property(field: str) -> dict:
    if field == "confirmation_signals":
        return {"type": "array", "items": {"type": "string"}}
    if field in SCORE_FIELDS:
        return {"type": "number", "minimum": 0, "maximum": 100}
    if field == "swing_bias":
        return {"type": "string", "minLength": 1, "maxLength": 20}
    if field == "setup_type":
        return {"type": "string", "minLength": 1, "maxLength": 50}
    return {"type": "string", "minLength": 1}

OUTPUT_RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {field: _response_property(field) for field in OUTPUT_FIELDS},
    "required": list(OUTPUT_FIELDS),
}
OUTPUT_SCHEMA_JSON = json.dumps(OUTPUT_RESPONSE_SCHEMA, sort_keys=True)

OUTPUT_FORMAT_INSTRUCTIONS = (
    "Output requirements:\n"
    f"- Return exactly one JSON object with these top-level keys only: {', '.join(OUTPUT_FIELDS)}.\n"
    "- Do not return the input payload, source data, nested research sections, markdown, or prose outside JSON.\n"
    "- Do not include input keys such as analysis_type, ticker, company_profile, price_history, technical_summary, volume_summary, fundamental_summary, valuation_summary, news, data_quality, or constraints.\n"
    "- swing_bias must be one short label such as bullish, bearish, or neutral, max 20 characters.\n"
    "- setup_type must be a short setup label, max 50 characters.\n"
    "- Score fields must be numbers from 0 to 100.\n"
    "- confirmation_signals must be an array of short strings.\n"
    "- If supporting data is missing, state that in the relevant string fields instead of inventing facts.\n"
    f"- The JSON object must validate against this schema: {OUTPUT_SCHEMA_JSON}"
)

INPUT_ANALYSIS_INSTRUCTIONS = (
    "Input analysis instructions:\n"
    "- The input payload contains deterministic technical calculations; treat calculated fields as source facts.\n"
    "- Use price_history.candles for price action, recent candle behavior, and entry context.\n"
    "- Use technical_summary and volume_summary as the primary calculated technical and volume facts.\n"
    "- Use data_quality to qualify uncertainty in the analysis.\n"
    "- Do not invent missing fundamentals, news, filings, or price levels.\n"
    "- If OHLCV data_quality includes warnings, mention those limitations in the relevant report fields."
)


SYSTEM_PROMPT = (
    "You are an AI swing-trade research analyst. Analyze the provided structured stock data only. "
    "Do not invent prices, fundamentals, news, or events. Do not provide financial advice. "
    "Give an explainable swing-trade research report for a 3-20 trading day timeframe. "
    "Return valid JSON only. If data is missing, say it is missing. Do not guess.\n\n"
    f"{INPUT_ANALYSIS_INSTRUCTIONS}\n\n"
    f"{OUTPUT_FORMAT_INSTRUCTIONS}"
)


def build_prompt(payload: dict) -> str:
    return (
        f"{SYSTEM_PROMPT}\n\n"
        "Input payload for analysis. This is source data, not the response shape:\n"
        f"{json.dumps(payload, sort_keys=True, default=str)}"
    )
