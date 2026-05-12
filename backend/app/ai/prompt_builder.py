from __future__ import annotations

import json

from app.ai.schemas import AIReportOutput


OUTPUT_FIELDS = tuple(AIReportOutput.model_fields.keys())
SCORE_FIELDS = {
    "confidence_score",
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
        return {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 1}
    if field in SCORE_FIELDS or field == "confidence_score":
        return {"type": "number", "minimum": 0, "maximum": 100}
    if field == "action_label":
        return {
            "type": "string",
            "enum": ["buy_setup", "watchlist", "neutral", "avoid", "high_risk"],
        }
    if field == "swing_bias":
        return {
            "type": "string",
            "enum": ["bullish", "bearish", "neutral", "mixed"],
        }
    if field == "setup_type":
        return {"type": "string", "minLength": 1, "maxLength": 50}
    return {"type": "string", "minLength": 1}


SYSTEM_ROLE = (
    "You are an AI swing-trade research analyst for QuantorSignal. "
    "Your job is to convert structured stock data into a practical research decision for a 3-20 trading day timeframe. "
    "Analyze only the provided data. Do not invent prices, fundamentals, news, filings, catalysts, or events. "
    "Do not provide personalized financial advice. This is research output only.\n\n"
    "The report must help the user decide whether the stock is actionable now, should be watched for confirmation, "
    "has no clear edge, or should be avoided due to risk. Avoid generic commentary. Every field should be specific, "
    "decision-oriented, and grounded in the provided data."
)

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
    "- action_label must be one of: buy_setup, watchlist, neutral, avoid, high_risk.\n"
    "- swing_bias must be one of: bullish, bearish, neutral, mixed.\n"
    "- setup_type must be a short label such as mean_reversion_bounce, breakout, pullback, momentum_continuation, breakdown_risk, no_clear_setup, max 50 characters.\n"
    "- confidence_score must be a number from 0 to 100 representing confidence in the action_label.\n"
    "- entry_zone, confirmation_trigger, invalidation_level, target_1, and target_2 must be actionable levels or conditions based only on provided price data; say data is missing if a level cannot be supported.\n"
    "- risk_reward_summary must explain the setup's reward versus invalidation risk using the provided levels.\n"
    "- watchlist_action must state the next practical tracking action.\n"
    "- Score fields must be numbers from 0 to 100.\n"
    "- confirmation_signals must be an array of short strings.\n"
    "- If supporting data is missing, state that in the relevant string fields instead of inventing facts.\n"
    f"- The JSON object must validate against this schema: {OUTPUT_SCHEMA_JSON}"
)

INPUT_ANALYSIS_INSTRUCTIONS = (
    "Input analysis instructions:\n"
    "- The input payload contains deterministic technical calculations; treat calculated fields as source facts.\n"
    "- Use price_history.candles for price action, recent candle behavior, and entry context.\n"
    "- Treat volume_summary as primary evidence for setup quality, confirmation, and risk; prioritize relative volume, up/down volume balance, accumulation/distribution, OBV trend, breakout confirmation, dry-up near support, and volume/price confirmation.\n"
    "- Treat lagging indicators such as RSI, SMA, and moving-average trend as secondary context, not as the main reason for an action_label.\n"
    "- Use technical_summary for price levels, volatility, and context after checking volume behavior.\n"
    "- Use data_quality to qualify uncertainty in the analysis.\n"
    "- Do not invent missing fundamentals, news, filings, or price levels.\n"
    "- If OHLCV data_quality includes warnings, mention those limitations in the relevant report fields."
)

DECISION_RULES = (
    "Decision rules:\n"
    "- Use action_label='buy_setup' only when price action, volume intelligence, entry timing, and risk/reward are reasonably aligned.\n"
    "- Use action_label='watchlist' when there are early positive signs but confirmation is missing.\n"
    "- Use action_label='neutral' when signals are mixed or there is no clear edge.\n"
    "- Use action_label='avoid' when the setup is weak, data quality is poor, or downside/risk dominates.\n"
    "- Use action_label='high_risk' when the stock may move but risk is elevated due to weak fundamentals, poor liquidity, stale data, extreme volatility, distribution, or weak volume confirmation.\n"
    "- Strong price moves without volume_price_confirmation, rising OBV, accumulation, or breakout_volume_confirmed should usually be treated as watchlist or neutral rather than buy_setup.\n"
    "- Distribution days, falling OBV, or divergent volume/price behavior should reduce confidence even when RSI, SMA, or recent returns look favorable.\n"
    "- Do not force bullish output. If the setup is weak, say so clearly.\n"
    "- Entry zones, targets, and invalidation levels must come only from provided prices, support/resistance, moving averages, recent highs/lows, ATR, or candle data.\n"
    "- If a precise entry, target, or invalidation level cannot be supported by provided data, state that it is not supported by the available data."
)

ACTIONABLE_OUTPUT_INSTRUCTIONS = (
    "Actionable output instructions:\n"
    "- Start from the decision, then justify it.\n"
    "- final_verdict must clearly say one of: act now, wait for confirmation, watchlist only, no clear edge, or avoid.\n"
    "- entry_zone should give a price area or say no supported entry zone.\n"
    "- confirmation_trigger should describe the exact condition that would improve the setup, using provided levels when available.\n"
    "- invalidation_level should identify the level or condition that weakens the thesis.\n"
    "- target_1 and target_2 should use nearby resistance, moving averages, recent highs, or other provided levels. Do not invent targets.\n"
    "- risk_reward_summary should explain whether upside appears worth the downside risk based only on provided levels.\n"
    "- watchlist_action should say what the user should monitor next, such as relative-volume expansion, accumulation replacing distribution, OBV turning up, breakout volume confirmation, higher low, or support hold.\n"
    "- Use plain English. Avoid vague phrases like 'could be interesting' unless followed by a concrete condition."
)


SYSTEM_PROMPT = (
    f"{SYSTEM_ROLE}\n\n"
    f"{INPUT_ANALYSIS_INSTRUCTIONS}\n\n"
    f"{DECISION_RULES}\n\n"
    f"{ACTIONABLE_OUTPUT_INSTRUCTIONS}\n\n"
    f"{OUTPUT_FORMAT_INSTRUCTIONS}"
)


def build_prompt(payload: dict) -> str:
    return (
        f"{SYSTEM_PROMPT}\n\n"
        "Input payload for analysis. This is source data, not the response shape:\n"
        f"{json.dumps(payload, sort_keys=True, default=str)}"
    )
