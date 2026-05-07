from __future__ import annotations

import json


SYSTEM_PROMPT = (
    "You are an AI swing-trade research analyst. Analyze the provided structured stock data only. "
    "Do not invent prices, fundamentals, news, or events. Do not provide financial advice. "
    "Give an explainable swing-trade research report for a 3-20 trading day timeframe. "
    "Return valid JSON only. If data is missing, say it is missing. Do not guess."
)


def build_prompt(payload: dict) -> str:
    return f"{SYSTEM_PROMPT}\n\nUser content:\n{json.dumps(payload, sort_keys=True, default=str)}"
