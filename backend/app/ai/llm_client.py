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


def _retry_user_content(payload: dict, retry: bool) -> str:
    user_content = json.dumps(payload, sort_keys=True, default=str)
    if retry:
        user_content = (
            f"{user_content}\n\nThe previous response was invalid. "
            "Return only one valid JSON object matching the required schema."
        )
    return user_content


def _create_anthropic_message(client: Any, model: str, payload: dict, retry: bool) -> Any:
    user_content = _retry_user_content(payload, retry)
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
        return client.messages.create(
            model=model,
            max_tokens=2500,
            temperature=0.3,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )


def _openai_compatible_api_key() -> str:
    return settings.openai_api_key or settings.ai_api_key


def _create_openai_compatible_message(model: str, payload: dict, retry: bool) -> Any:
    try:
        from openai import BadRequestError, OpenAI
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail={"error": "openai_sdk_missing", "message": "The openai package is not installed."},
        )

    api_key = _openai_compatible_api_key()
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "ai_api_key_missing",
                "message": "Set OPENAI_API_KEY or AI_API_KEY for OpenAI-compatible AI providers.",
            },
        )

    client = OpenAI(api_key=api_key, base_url=settings.openai_base_url.rstrip("/"), timeout=60.0)
    request: dict[str, Any] = {
        "model": model,
        "temperature": 0.3,
        "max_tokens": 2500,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _retry_user_content(payload, retry)},
        ],
    }
    try:
        return client.chat.completions.create(**request)
    except BadRequestError as exc:
        if "response_format" not in str(exc).lower():
            raise
        request.pop("response_format", None)
        return client.chat.completions.create(**request)


def _openai_compatible_content(message: Any) -> str:
    choices = getattr(message, "choices", None) or []
    if not choices:
        return ""
    content = getattr(getattr(choices[0], "message", None), "content", None)
    return content or ""


def _openai_compatible_usage_tokens(message: Any) -> tuple[int, int]:
    usage = getattr(message, "usage", None)
    if usage is None:
        return 0, 0
    return int(getattr(usage, "prompt_tokens", 0) or 0), int(getattr(usage, "completion_tokens", 0) or 0)


def _generate_with_anthropic(payload: dict, model: str, retry: bool) -> tuple[dict[str, Any], int, int]:
    try:
        from anthropic import Anthropic
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail={"error": "anthropic_sdk_missing", "message": "The anthropic package is not installed."},
        )

    api_key = settings.anthropic_api_key or settings.ai_api_key or None
    client = Anthropic(api_key=api_key) if api_key else Anthropic()
    message = _create_anthropic_message(client, model, payload, retry=retry)
    input_tokens, output_tokens = _usage_tokens(message)
    candidate = _content_payload(message)
    parsed = candidate if isinstance(candidate, dict) else _extract_json(candidate)
    return parsed, input_tokens, output_tokens


def _generate_with_openai_compatible(payload: dict, model: str, retry: bool) -> tuple[dict[str, Any], int, int]:
    message = _create_openai_compatible_message(model, payload, retry=retry)
    input_tokens, output_tokens = _openai_compatible_usage_tokens(message)
    parsed = _extract_json(_openai_compatible_content(message))
    return parsed, input_tokens, output_tokens


def _generate_raw_report(payload: dict, model: str, retry: bool) -> tuple[dict[str, Any], int, int]:
    provider = settings.ai_provider.strip().lower().replace("_", "-")
    if provider in {"anthropic", "claude"}:
        return _generate_with_anthropic(payload, model, retry)
    if provider in {"openai", "openai-compatible", "compatible"}:
        return _generate_with_openai_compatible(payload, model, retry)
    raise HTTPException(
        status_code=500,
        detail={
            "error": "unsupported_ai_provider",
            "provider": settings.ai_provider,
            "supported_providers": ["anthropic", "openai-compatible"],
        },
    )


def generate_single_stock_report(payload: dict, user_id: str, ticker: str, db: Session) -> dict:
    model = settings.ai_model
    total_input_tokens = 0
    total_output_tokens = 0
    last_error = "unknown_error"

    for attempt in range(2):
        try:
            parsed, input_tokens, output_tokens = _generate_raw_report(payload, model, retry=attempt > 0)
            total_input_tokens += input_tokens
            total_output_tokens += output_tokens

            validated = AIReportOutput.model_validate(parsed)
            result = validated.model_dump(mode="json")
            result["_usage"] = {
                "model_used": model,
                "tokens_input": total_input_tokens,
                "tokens_output": total_output_tokens,
            }
            return result
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            last_error = str(exc)
            if attempt == 0:
                continue
        except HTTPException:
            raise
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
