from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.ai.prompt_builder import SYSTEM_PROMPT
from app.ai.schemas import AIReportOutput
from app.config import settings
from app.database.models import AIUsageEvent


def _content_text(message: Any) -> str:
    parts = getattr(message, "content", None) or []
    text_parts: list[str] = []
    for part in parts:
        text = getattr(part, "text", None)
        if text:
            text_parts.append(text)
    return "".join(text_parts)


def _content_payload(message: Any) -> dict[str, Any] | str:
    parts = getattr(message, "content", None) or []
    for part in parts:
        if getattr(part, "type", None) == "tool_use":
            tool_input = getattr(part, "input", None)
            if isinstance(tool_input, dict):
                return tool_input
    return _content_text(message)


def _usage_tokens(message: Any) -> tuple[int, int]:
    usage = getattr(message, "usage", None)
    if usage is None:
        return 0, 0
    return int(getattr(usage, "input_tokens", 0) or 0), int(getattr(usage, "output_tokens", 0) or 0)


def _extract_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(text[start : end + 1])


def _record_llm_usage(
    user_id: str,
    ticker: str,
    model_used: str,
    tokens_input: int,
    tokens_output: int,
    report_type: str,
    db: Session,
) -> None:
    db.add(
        AIUsageEvent(
            user_id=int(user_id),
            ticker=ticker.strip().upper(),
            report_type=report_type,
            model_used=model_used,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
        )
    )
    db.commit()


def _create_message(client: Any, model: str, payload: dict, retry: bool) -> Any:
    user_content = json.dumps(payload, sort_keys=True, default=str)
    if retry:
        user_content = (
            f"{user_content}\n\nThe previous response was invalid. "
            "Return only one valid JSON object matching the required schema."
        )

    try:
        return client.messages.create(
            model=model,
            max_tokens=2500,
            temperature=0.3,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
            tools=[
                {
                    "name": "emit_stock_report",
                    "description": "Emit the stock report as a structured JSON object.",
                    "input_schema": AIReportOutput.model_json_schema(),
                }
            ],
            tool_choice={"type": "tool", "name": "emit_stock_report"},
        )
    except TypeError:
        fallback_user_content = user_content
        if retry:
            fallback_user_content = (
                f"{user_content}\n\nThe previous response was invalid. "
                "Return only one valid JSON object matching the required schema."
            )
        return client.messages.create(
            model=model,
            max_tokens=2500,
            temperature=0.3,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": fallback_user_content}],
        )


def generate_single_stock_report(payload: dict, user_id: str, ticker: str, db: Session) -> dict:
    try:
        from anthropic import Anthropic
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail={"error": "anthropic_sdk_missing", "message": "The anthropic package is not installed."},
        )

    model = settings.ai_model
    client = Anthropic()
    total_input_tokens = 0
    total_output_tokens = 0
    last_error = "unknown_error"

    for attempt in range(2):
        try:
            message = _create_message(client, model, payload, retry=attempt > 0)
            input_tokens, output_tokens = _usage_tokens(message)
            total_input_tokens += input_tokens
            total_output_tokens += output_tokens

            candidate = _content_payload(message)
            parsed = candidate if isinstance(candidate, dict) else _extract_json(candidate)
            validated = AIReportOutput.model_validate(parsed)
            result = validated.model_dump(mode="json")
            _record_llm_usage(
                user_id,
                ticker,
                model,
                total_input_tokens,
                total_output_tokens,
                "single_stock",
                db,
            )
            return result
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            last_error = str(exc)
            if attempt == 0:
                continue
        except Exception as exc:
            last_error = str(exc)
            break

    _record_llm_usage(
        user_id,
        ticker,
        model,
        total_input_tokens,
        total_output_tokens,
        "single_stock_failure",
        db,
    )
    raise HTTPException(
        status_code=502,
        detail={
            "error": "ai_report_generation_failed",
            "ticker": ticker.strip().upper(),
            "model": model,
            "message": "The AI response could not be parsed or validated after retry.",
            "last_error": last_error,
        },
    )
