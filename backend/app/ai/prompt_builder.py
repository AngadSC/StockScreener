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

OUTPUT_RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        field: (
            {"type": "array", "items": {"type": "string"}}
            if field == "confirmation_signals"
            else {"type": "number"}
            if field in SCORE_FIELDS
            else {"type": "string"}
        )
        for field in OUTPUT_FIELDS
    },
    "required": list(OUTPUT_FIELDS),
}
OUTPUT_SCHEMA_JSON = json.dumps(OUTPUT_RESPONSE_SCHEMA, sort_keys=True)

OUTPUT_FORMAT_INSTRUCTIONS = (
    "Output requirements:\n"
    f"- Return exactly one JSON object with these top-level keys only: {', '.join(OUTPUT_FIELDS)}.\n"
    "- Do not return the input payload, source data, nested research sections, markdown, or prose outside JSON.\n"
    "- Do not include input keys such as analysis_type, ticker, market_data, technical_data, fundamental_data, valuation_data, news_data, or constraints.\n"
    "- Score fields must be numbers from 0 to 100.\n"
    "- confirmation_signals must be an array of short strings.\n"
    "- If supporting data is missing, state that in the relevant string fields instead of inventing facts.\n"
    f"- The JSON object must validate against this schema: {OUTPUT_SCHEMA_JSON}"
)


SYSTEM_PROMPT = (
    "You are an AI swing-trade research analyst. Analyze the provided structured stock data only. "
    "Do not invent prices, fundamentals, news, or events. Do not provide financial advice. "
    "Give an explainable swing-trade research report for a 3-20 trading day timeframe. "
    "Return valid JSON only. If data is missing, say it is missing. Do not guess.\n\n"
    f"{OUTPUT_FORMAT_INSTRUCTIONS}"
)


def build_prompt(payload: dict) -> str:
    return (
        f"{SYSTEM_PROMPT}\n\n"
        "Input payload for analysis. This is source data, not the response shape:\n"
        f"{json.dumps(payload, sort_keys=True, default=str)}"
    )
