from __future__ import annotations

import json

from app.ai.schemas import AIEvidenceOutput, AIReportOutput


EVIDENCE_FIELDS = tuple(AIEvidenceOutput.model_fields.keys())
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


TRADE_CARD_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "decision": {
            "type": "string",
            "enum": [
                "Long Setup Active",
                "Conditional Long",
                "Bullish Watch",
                "No Trade",
                "Conditional Short",
                "Short Setup Active",
                "Avoid",
                "High Risk",
            ],
        },
        "ai_lean": {"type": "string", "enum": ["bullish", "bearish", "neutral"]},
        "best_action_now": {
            "type": "string",
            "enum": [
                "buy_now",
                "wait_for_breakout",
                "wait_for_pullback",
                "hold_if_in",
                "avoid",
                "short_now",
                "wait_for_breakdown",
            ],
        },
        "verdict": {"type": "string", "minLength": 1, "maxLength": 300},
        "setup_type": {"type": "string", "minLength": 1, "maxLength": 60},
        "confidence_label": {"type": "string", "enum": ["low", "moderate", "strong", "very_strong"]},
        "setup_score": {"type": "number", "minimum": 0, "maximum": 100},
        "trade_levels": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "current_price": {"type": ["number", "null"]},
                "preferred_entry": {"type": ["number", "null"]},
                "aggressive_entry_min": {"type": ["number", "null"]},
                "aggressive_entry_max": {"type": ["number", "null"]},
                "confirmation_trigger": {"type": ["number", "null"]},
                "add_level": {"type": ["number", "null"]},
                "invalidation_level": {"type": ["number", "null"]},
                "target_1": {"type": ["number", "null"]},
                "target_2": {"type": ["number", "null"]},
                "chase_above": {"type": ["number", "null"]},
                "method": {"type": ["string", "null"]},
                "warnings": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "current_price",
                "preferred_entry",
                "aggressive_entry_min",
                "aggressive_entry_max",
                "confirmation_trigger",
                "add_level",
                "invalidation_level",
                "target_1",
                "target_2",
                "chase_above",
                "method",
                "warnings",
            ],
        },
        "main_reason": {"type": "string", "minLength": 1},
        "main_risk": {"type": "string", "minLength": 1},
        "bull_case": {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 1},
        "bear_case": {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 1},
        "if_then_plan": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "if_trigger_hits": {"type": "string", "minLength": 1},
                "if_rejects": {"type": "string", "minLength": 1},
                "if_breaks_invalidation": {"type": "string", "minLength": 1},
                "if_already_holding": {"type": "string", "minLength": 1},
                "if_missed_entry": {"type": "string", "minLength": 1},
            },
            "required": [
                "if_trigger_hits",
                "if_rejects",
                "if_breaks_invalidation",
                "if_already_holding",
                "if_missed_entry",
            ],
        },
    },
    "required": [
        "decision",
        "ai_lean",
        "best_action_now",
        "verdict",
        "setup_type",
        "confidence_label",
        "setup_score",
        "trade_levels",
        "main_reason",
        "main_risk",
        "bull_case",
        "bear_case",
        "if_then_plan",
    ],
}


def _response_property(field: str) -> dict:
    if field == "trade_card":
        return {"oneOf": [{"type": "null"}, TRADE_CARD_SCHEMA]}
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


def _evidence_response_property(field: str) -> dict:
    if field in {"bull_case", "bear_case", "missing_data"}:
        return {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 1}
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

EVIDENCE_ANALYZER_ROLE = (
    "You are AI Call 1: Evidence Analyzer for QuantorSignal. "
    "Your job is to read the backend feature-engineered stock payload and extract evidence only. "
    "Do not make final ratings, action labels, confidence calls, or a user-facing report. "
    "Analyze only the provided data. Do not invent prices, fundamentals, news, filings, catalysts, or events."
)

OUTPUT_RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {field: _response_property(field) for field in OUTPUT_FIELDS},
    "required": list(OUTPUT_FIELDS),
}
OUTPUT_SCHEMA_JSON = json.dumps(OUTPUT_RESPONSE_SCHEMA, sort_keys=True)

EVIDENCE_RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {field: _evidence_response_property(field) for field in EVIDENCE_FIELDS},
    "required": list(EVIDENCE_FIELDS),
}
EVIDENCE_SCHEMA_JSON = json.dumps(EVIDENCE_RESPONSE_SCHEMA, sort_keys=True)

EVIDENCE_OUTPUT_FORMAT_INSTRUCTIONS = (
    "Evidence Analyzer output requirements:\n"
    f"- Return exactly one JSON object with these top-level keys only: {', '.join(EVIDENCE_FIELDS)}.\n"
    "- bull_case must be an array of concise evidence strings supporting upside or long interest, grounded in the provided data.\n"
    "- bear_case must be an array of concise evidence strings supporting downside, avoidance, or risk, grounded in the provided data.\n"
    "- setup_type must be a short label such as mean_reversion_bounce, breakout, pullback, momentum_continuation, breakdown_risk, no_clear_setup, max 50 characters.\n"
    "- missing_data must list missing or weak evidence that limits confidence, such as stale OHLCV, missing fundamentals, missing valuation, missing news, weak volume confirmation, or unsupported levels.\n"
    "- Do not include ratings, action_label, timeframe_ratings, confidence_score, final_verdict, markdown, or prose outside JSON.\n"
    f"- The JSON object must validate against this schema: {EVIDENCE_SCHEMA_JSON}"
)

OUTPUT_FORMAT_INSTRUCTIONS = (
    "Output requirements:\n"
    f"- Return exactly one JSON object with these top-level keys only: {', '.join(OUTPUT_FIELDS)}.\n"
    "- Do not return the input payload, source data, nested research sections, markdown, or prose outside JSON.\n"
    "- Do not include input keys such as market_payload, evidence_analysis, analysis_type, ticker, company_profile, price_history, technical_summary, volume_summary, fundamental_summary, valuation_summary, news, data_quality, deterministic_scores, or constraints.\n"
    "- action_label must be one of: actionable_long, long_watchlist, neutral_wait, short_watchlist, actionable_short, avoid, high_risk.\n"
    "- directional_bias must be one of: bullish, bearish, neutral, mixed_bullish_lean, mixed_bearish_lean.\n"
    "- timeframe_ratings.short_term.rating must be one of: buy, watch, avoid, with timeframe exactly '1-10 trading days' and a 0-100 confidence_score.\n"
    "- timeframe_ratings.swing.rating must be one of: buy, watch, avoid, with timeframe exactly '2-8 weeks' and a 0-100 confidence_score.\n"
    "- timeframe_ratings.long_term.rating must be one of: accumulate, hold, avoid, unknown, with timeframe exactly '6-24 months' and a 0-100 confidence_score.\n"
    "- timeframe_ratings.short_term.reason, timeframe_ratings.swing.reason, and timeframe_ratings.long_term.reason are required non-empty strings.\n"
    "- price_action_structure must copy technical_summary.price_action_structure exactly; do not reinterpret or change its deterministic flags, levels, labels, or distances.\n"
    "- setup_type must be a short label such as mean_reversion_bounce, breakout, pullback, momentum_continuation, breakdown_risk, no_clear_setup, max 50 characters.\n"
    "- confidence_score must copy deterministic_scores.confidence_score exactly.\n"
    "- entry_zone, confirmation_trigger, invalidation_level, target_1, and target_2 must be actionable levels or conditions based only on provided price data; say data is missing if a level cannot be supported.\n"
    "- risk_reward_summary must explain the setup's reward versus invalidation risk using the provided levels.\n"
    "- watchlist_action must state the next practical tracking action.\n"
    "- Score fields must be numbers from 0 to 100 copied exactly from deterministic_scores; explain the scores in prose fields, but do not invent or adjust score values.\n"
    "- confirmation_signals must be an array of short strings.\n"
    "- If supporting data is missing, state that in the relevant string fields instead of inventing facts.\n"
    "- trade_card must be included in the output as a top-level field. It must follow the TRADE_CARD_SCHEMA exactly.\n"
    "- trade_card.decision mapping rules:\n"
    "  * 'Long Setup Active' = strong uptrend + confirmed breakout + volume confirmation\n"
    "  * 'Conditional Long' = uptrend + near resistance + no breakout confirmation yet, OR setup forming but awaiting trigger\n"
    "  * 'Bullish Watch' = bullish structure but no clean entry, or constructive but needs catalyst\n"
    "  * 'No Trade' = mixed/sideways/no edge\n"
    "  * 'Conditional Short' = downtrend + near support, breakdown pending\n"
    "  * 'Short Setup Active' = downtrend + breakdown + volume confirmation\n"
    "  * 'Avoid' = failed breakout / distribution / high risk / weak setup\n"
    "  * 'High Risk' = setup may exist but risk is elevated\n"
    "- trade_card.verdict must be exactly ONE sentence. It must state what the AI would do and what makes it actionable or not actionable. It must NOT be only 'wait and watch.'\n"
    "- trade_card.trade_levels: If backend-provided trade_levels are in the payload under deterministic_scores.trade_levels, copy them directly. Do NOT invent prices. If deterministic levels are null, set those fields to null.\n"
    "- trade_card.setup_score must copy deterministic_scores.setup_quality_score exactly.\n"
    "- trade_card.confidence_label mapping based on deterministic_scores.confidence_score:\n"
    "  * 0-39: 'low'\n"
    "  * 40-59: 'moderate'\n"
    "  * 60-79: 'strong'\n"
    "  * 80-100: 'very_strong'\n"
    "- trade_card.bull_case and bear_case: use the Evidence Analyzer bull_case/bear_case output, shortened to 2-4 items max of 15 words each or fewer.\n"
    "- trade_card.if_then_plan must include specific conditions and levels, NOT generic 'wait' language.\n"
    "- The payload may include deterministic_scores.trade_levels with pre-calculated price levels. If present and non-null, these are computed from ATR, support, resistance, and price structure. Copy them into trade_card.trade_levels exactly. Do not substitute your own prices.\n"
    "- If deterministic_scores.trade_levels is missing or trade_levels.method is 'no_setup', set all price fields in trade_card.trade_levels to null and add a warning explaining insufficient price structure.\n"
    f"- The JSON object must validate against this schema: {OUTPUT_SCHEMA_JSON}"
)

INPUT_ANALYSIS_INSTRUCTIONS = (
    "Input analysis instructions:\n"
    "- Flow: Market Data -> Backend Feature Engineering -> AI Call 1 Evidence Analyzer -> AI Call 2 Decision Synthesizer.\n"
    "- Backend feature engineering already separates trend, momentum, volume, price structure, support/resistance, volatility, risk/reward, fundamentals, and news into the structured payload.\n"
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

EVIDENCE_ANALYSIS_INSTRUCTIONS = (
    "Evidence analysis instructions:\n"
    "- Read the feature-engineered payload after backend calculations for trend, momentum, volume, price structure, support/resistance, volatility, risk/reward, fundamentals, and news.\n"
    "- Extract bull_case and bear_case from explicit payload facts only.\n"
    "- Identify setup_type from technical_summary.price_action_structure, price levels, trend, momentum, and volume confirmation.\n"
    "- Identify missing_data from data_quality, unavailable fundamentals or valuation, absent or low-materiality news, stale or thin OHLCV, unclear support/resistance, weak risk/reward, or missing confirmation.\n"
    "- Treat volume_summary as primary evidence for setup quality, confirmation, and risk.\n"
    "- Treat lagging indicators such as RSI, SMA, and moving-average trend as secondary context.\n"
    "- Do not decide final stance, confidence, timeframe ratings, or report copy."
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
    "- If a precise entry, target, or invalidation level cannot be supported by provided data, state that it is not supported by the available data.\n"
    "- You are not allowed to end the trade_card.verdict with only 'wait and watch.' If the setup is not actionable yet, state the direction you favor, the exact price or condition that would make it actionable, and what invalidates it.\n"
    "- If all signals are mixed with no clear edge, use decision='No Trade' and explain why in verdict.\n"
    "- trade_card.decision should match action_label per these mappings:\n"
    "  * actionable_long -> 'Long Setup Active'\n"
    "  * long_watchlist -> 'Conditional Long' if there is a specific price trigger, 'Bullish Watch' if more general\n"
    "  * neutral_wait -> 'No Trade'\n"
    "  * short_watchlist -> 'Conditional Short' or 'Bullish Watch' depending on context\n"
    "  * actionable_short -> 'Short Setup Active'\n"
    "  * avoid -> 'Avoid'\n"
    "  * high_risk -> 'High Risk'"
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
    "- Use plain English. Avoid vague phrases like 'could be interesting' unless followed by a concrete condition.\n"
    "- trade_card.if_then_plan.if_trigger_hits: state what to do when the confirmation_trigger is hit (e.g., 'Enter long at $X, target $Y1 and $Y2, stop at $Z').\n"
    "- trade_card.if_then_plan.if_rejects: state what happens if price rejects at resistance (e.g., 'Exit or don't enter, reassess at $X support').\n"
    "- trade_card.if_then_plan.if_breaks_invalidation: state what happens when invalidation_level is breached.\n"
    "- trade_card.if_then_plan.if_already_holding: give position management guidance.\n"
    "- trade_card.if_then_plan.if_missed_entry: give advice on whether to chase or wait for another entry."
)


EVIDENCE_SYSTEM_PROMPT = (
    f"{EVIDENCE_ANALYZER_ROLE}\n\n"
    f"{EVIDENCE_ANALYSIS_INSTRUCTIONS}\n\n"
    f"{EVIDENCE_OUTPUT_FORMAT_INSTRUCTIONS}"
)

SYSTEM_PROMPT = (
    f"{SYSTEM_ROLE}\n\n"
    f"{INPUT_ANALYSIS_INSTRUCTIONS}\n\n"
    "Decision Synthesizer instructions:\n"
    "- You are AI Call 2: Decision Synthesizer. Use the Evidence Analyzer output as the organized bull/bear/setup/missing-data layer, then synthesize the final ratings, final stance, confidence, and user-facing report.\n"
    "- The original backend feature-engineered payload is provided under market_payload; the first-call evidence object is provided under evidence_analysis.\n"
    "- Do not ignore the original feature-engineered payload. Resolve conflicts by relying on deterministic payload facts and the provided evidence analysis.\n"
    "- If the evidence analysis overstates unsupported facts, defer to the original payload and mention limitations in the relevant report fields.\n\n"
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
