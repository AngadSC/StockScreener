from __future__ import annotations

import json

from app.ai.schemas import AIReportOutput


OUTPUT_FIELDS = tuple(AIReportOutput.model_fields.keys())
SCORE_FIELDS = {
    "confidence_score",
    "setup_quality_score",
    "entry_timing_score",
    "technical_score",
    "price_structure_score",
    "volume_score",
    "momentum_score",
    "trend_score",
    "fundamental_score",
    "revenue_earnings_quality_score",
    "sentiment_score",
    "news_score",
    "valuation_score",
    "risk_score",
    "risk_reward_score",
    "short_term_score",
    "swing_trade_score",
    "long_term_score",
}


TRADE_TIMEFRAME_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "rating": {"type": "string", "enum": ["buy", "watch", "avoid"]},
        "timeframe": {"type": "string", "enum": ["1-10 trading days", "2-8 weeks"]},
        "confidence_score": {"type": "number", "minimum": 0, "maximum": 100},
        "reason": {"type": "string", "minLength": 1},
    },
    "required": ["rating", "timeframe", "confidence_score", "reason"],
}


LONG_TERM_TIMEFRAME_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "rating": {"type": "string", "enum": ["accumulate", "hold", "avoid", "unknown"]},
        "timeframe": {"type": "string", "enum": ["6-24 months"]},
        "confidence_score": {"type": "number", "minimum": 0, "maximum": 100},
        "reason": {"type": "string", "minLength": 1},
    },
    "required": ["rating", "timeframe", "confidence_score", "reason"],
}


PRICE_ACTION_STRUCTURE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "setup_label": {"type": "string", "minLength": 1, "maxLength": 60},
        "structure_label": {"type": "string", "minLength": 1, "maxLength": 60},
        "breakout_label": {"type": "string", "minLength": 1, "maxLength": 60},
        "pullback_label": {"type": "string", "minLength": 1, "maxLength": 60},
        "range_label": {"type": "string", "minLength": 1, "maxLength": 60},
        "gap_label": {"type": "string", "minLength": 1, "maxLength": 60},
        "labels": {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 1},
        "near_20d_high": {"type": "boolean"},
        "near_60d_high": {"type": "boolean"},
        "distance_to_support_pct": {"type": ["number", "null"]},
        "distance_to_resistance_pct": {"type": ["number", "null"]},
        "range_compression": {"type": "boolean"},
        "higher_highs_higher_lows": {"type": "boolean"},
        "lower_highs_lower_lows": {"type": "boolean"},
        "gap_up_recent": {"type": "boolean"},
        "gap_down_recent": {"type": "boolean"},
        "failed_breakout": {"type": "boolean"},
        "breakout_attempt": {"type": "boolean"},
        "pullback_to_sma20": {"type": "boolean"},
        "pullback_to_sma50": {"type": "boolean"},
        "support_level": {"type": ["number", "null"]},
        "resistance_level": {"type": ["number", "null"]},
        "prior_20d_resistance": {"type": ["number", "null"]},
        "sma_20": {"type": ["number", "null"]},
        "sma_50": {"type": ["number", "null"]},
        "sma_200": {"type": ["number", "null"]},
    },
    "required": [
        "setup_label",
        "structure_label",
        "breakout_label",
        "pullback_label",
        "range_label",
        "gap_label",
        "labels",
        "near_20d_high",
        "near_60d_high",
        "distance_to_support_pct",
        "distance_to_resistance_pct",
        "range_compression",
        "higher_highs_higher_lows",
        "lower_highs_lower_lows",
        "gap_up_recent",
        "gap_down_recent",
        "failed_breakout",
        "breakout_attempt",
        "pullback_to_sma20",
        "pullback_to_sma50",
        "support_level",
        "resistance_level",
        "prior_20d_resistance",
        "sma_20",
        "sma_50",
        "sma_200",
    ],
}


def _response_property(field: str) -> dict:
    if field == "confirmation_signals":
        return {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 1}
    if field == "timeframe_ratings":
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "short_term": {
                    **TRADE_TIMEFRAME_SCHEMA,
                    "properties": {
                        **TRADE_TIMEFRAME_SCHEMA["properties"],
                        "timeframe": {"type": "string", "enum": ["1-10 trading days"]},
                    },
                },
                "swing": {
                    **TRADE_TIMEFRAME_SCHEMA,
                    "properties": {
                        **TRADE_TIMEFRAME_SCHEMA["properties"],
                        "timeframe": {"type": "string", "enum": ["2-8 weeks"]},
                    },
                },
                "long_term": LONG_TERM_TIMEFRAME_SCHEMA,
            },
            "required": ["short_term", "swing", "long_term"],
        }
    if field == "price_action_structure":
        return PRICE_ACTION_STRUCTURE_SCHEMA
    if field in SCORE_FIELDS or field == "confidence_score":
        return {"type": "number", "minimum": 0, "maximum": 100}
    if field == "action_label":
        return {
            "type": "string",
            "enum": [
                "actionable_long",
                "long_watchlist",
                "neutral_wait",
                "short_watchlist",
                "actionable_short",
                "avoid",
                "high_risk",
            ],
        }
    if field == "directional_bias":
        return {
            "type": "string",
            "enum": [
                "bullish",
                "bearish",
                "neutral",
                "mixed_bullish_lean",
                "mixed_bearish_lean",
            ],
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
    "- Do not include input keys such as analysis_type, ticker, company_profile, price_history, technical_summary, volume_summary, fundamental_summary, valuation_summary, news, data_quality, deterministic_scores, or constraints.\n"
    "- action_label must be one of: actionable_long, long_watchlist, neutral_wait, short_watchlist, actionable_short, avoid, high_risk.\n"
    "- directional_bias must be one of: bullish, bearish, neutral, mixed_bullish_lean, mixed_bearish_lean.\n"
    "- timeframe_ratings.short_term.rating must be one of: buy, watch, avoid, with timeframe exactly '1-10 trading days' and a 0-100 confidence_score.\n"
    "- timeframe_ratings.swing.rating must be one of: buy, watch, avoid, with timeframe exactly '2-8 weeks' and a 0-100 confidence_score.\n"
    "- timeframe_ratings.long_term.rating must be one of: accumulate, hold, avoid, unknown, with timeframe exactly '6-24 months' and a 0-100 confidence_score.\n"
    "- price_action_structure must copy technical_summary.price_action_structure exactly; do not reinterpret or change its deterministic flags, levels, labels, or distances.\n"
    "- setup_type must be a short label such as mean_reversion_bounce, breakout, pullback, momentum_continuation, breakdown_risk, no_clear_setup, max 50 characters.\n"
    "- confidence_score must copy deterministic_scores.confidence_score exactly.\n"
    "- entry_zone, confirmation_trigger, invalidation_level, target_1, and target_2 must be actionable levels or conditions based only on provided price data; say data is missing if a level cannot be supported.\n"
    "- risk_reward_summary must explain the setup's reward versus invalidation risk using the provided levels.\n"
    "- watchlist_action must state the next practical tracking action.\n"
    "- Score fields must be numbers from 0 to 100 copied exactly from deterministic_scores; explain the scores in prose fields, but do not invent or adjust score values.\n"
    "- confirmation_signals must be an array of short strings.\n"
    "- If supporting data is missing, state that in the relevant string fields instead of inventing facts.\n"
    f"- The JSON object must validate against this schema: {OUTPUT_SCHEMA_JSON}"
)

INPUT_ANALYSIS_INSTRUCTIONS = (
    "Input analysis instructions:\n"
    "- The input payload contains deterministic technical calculations; treat calculated fields as source facts.\n"
    "- The input payload contains deterministic_scores. Every output score field must match its same-named deterministic_scores value exactly.\n"
    "- Treat risk_score and risk_reward_score as quality scores where higher is better risk control / reward-to-risk, not higher danger.\n"
    "- Use price_history.candles for price action, recent candle behavior, and entry context.\n"
    "- Treat technical_summary.price_action_structure as deterministic source truth for setup labels, breakout state, range compression, trend structure, pullbacks, gaps, and support/resistance distances.\n"
    "- Treat volume_summary as primary evidence for setup quality, confirmation, and risk; prioritize relative volume, up/down volume balance, accumulation/distribution, OBV trend, breakout confirmation, dry-up near support, and volume/price confirmation.\n"
    "- Treat lagging indicators such as RSI, SMA, and moving-average trend as secondary context, not as the main reason for an action_label.\n"
    "- Use technical_summary for price levels, volatility, and context after checking volume behavior.\n"
    "- Use news.articles as classified catalyst inputs. Each article may include event_type, sentiment, materiality, time_horizon, summary, and why_it_matters; weigh high-materiality guidance, earnings, FDA, lawsuit, merger, macro, and analyst-rating events more than generic headlines.\n"
    "- Do not treat news naively. A positive headline with low materiality should not override weak technicals, and a high-materiality negative catalyst should weaken an otherwise bullish setup.\n"
    "- Use data_quality to qualify uncertainty in the analysis.\n"
    "- Do not invent missing fundamentals, news, filings, or price levels.\n"
    "- If OHLCV data_quality includes warnings, mention those limitations in the relevant report fields."
)

DECISION_RULES = (
    "Decision rules:\n"
    "- Use action_label='actionable_long' only when price action, volume intelligence, entry timing, risk/reward, and catalyst context are reasonably aligned for a long setup.\n"
    "- action_label should summarize the swing timeframe decision, while timeframe_ratings must separately evaluate short-term, swing, and long-term suitability.\n"
    "- Use action_label='long_watchlist' when bullish structure or a positive catalyst is forming, but trigger, timing, or confirmation is missing.\n"
    "- Use action_label='neutral_wait' when signals are mixed or there is no clear edge.\n"
    "- Use action_label='short_watchlist' when downside risk is forming, but a short trigger or risk/reward is not confirmed.\n"
    "- Use action_label='actionable_short' only when bearish price action, confirmation, and risk/reward are aligned.\n"
    "- Use action_label='avoid' when the setup is weak, data quality is poor, or downside/risk dominates.\n"
    "- Use action_label='high_risk' when the stock may move but risk is elevated due to weak fundamentals, poor liquidity, stale data, extreme volatility, distribution, or weak volume confirmation.\n"
    "- Strong price moves without volume_price_confirmation, rising OBV, accumulation, or breakout_volume_confirmed should usually be treated as long_watchlist or neutral_wait rather than actionable_long.\n"
    "- A breakout_attempt or compression_breakout_attempt can be a watch or buy setup only when the trigger, invalidation, and volume confirmation path are clear.\n"
    "- failed_breakout, lower_highs_lower_lows, or gap_down_recent should reduce short-term and swing confidence unless there is strong contrary evidence in the provided data.\n"
    "- Distribution days, falling OBV, or divergent volume/price behavior should reduce confidence even when RSI, SMA, or recent returns look favorable.\n"
    "- Do not force bullish or bearish output. If the setup is weak or unconfirmed, say so clearly with neutral_wait, long_watchlist, short_watchlist, avoid, or high_risk.\n"
    "- Set directional_bias separately from action_label. For example, use directional_bias='bullish' with action_label='long_watchlist' when bullish structure is forming but not actionable yet.\n"
    "- If technicals are neutral but a high-materiality positive catalyst exists, explain that the stock is worth watching instead of pretending the chart is confirmed.\n"
    "- If the technical setup is bullish but recent negative guidance, litigation, FDA rejection, or another high-materiality negative catalyst exists, weaken the thesis and actionability.\n"
    "- Entry zones, targets, and invalidation levels must come only from provided prices, support/resistance, moving averages, recent highs/lows, ATR, or candle data.\n"
    "- If a precise entry, target, or invalidation level cannot be supported by provided data, state that it is not supported by the available data."
)

ACTIONABLE_OUTPUT_INSTRUCTIONS = (
    "Actionable output instructions:\n"
    "- Start from the decision, then justify it.\n"
    "- Timeframe reasons must be different and specific to their horizon; do not repeat the same reason for short_term, swing, and long_term.\n"
    "- final_verdict must clearly say one of: actionable long, long watchlist, neutral wait, short watchlist, actionable short, avoid, or high risk.\n"
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
