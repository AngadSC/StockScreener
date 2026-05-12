from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.ai.prompt_builder import OUTPUT_FORMAT_INSTRUCTIONS, OUTPUT_RESPONSE_SCHEMA, SYSTEM_PROMPT
from app.ai.schemas import AIReportOutput
from app.config import settings
from app.database.models import AIUsageEvent

logger = logging.getLogger(__name__)


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
    user_content = (
        "Analyze this input payload. It is source data, not the response shape:\n"
        f"{json.dumps(payload, sort_keys=True, default=str)}\n\n"
        f"{OUTPUT_FORMAT_INSTRUCTIONS}"
    )
    if retry:
        user_content = (
            f"{user_content}\n\nThe previous response was invalid. "
            "Return only one valid JSON object matching the required schema. "
            "Do not include input payload keys such as analysis_type, ticker, company_profile, "
            "price_history, technical_summary, volume_summary, fundamental_summary, "
            "valuation_summary, news, data_quality, deterministic_scores, or constraints."
        )
    return user_content


def _attach_deterministic_report_fields(candidate: dict[str, Any], payload: dict) -> dict[str, Any]:
    candidate = dict(candidate)
    technical_summary = payload.get("technical_summary") if isinstance(payload, dict) else {}
    if not isinstance(technical_summary, dict):
        technical_summary = {}

    price_action_structure = technical_summary.get("price_action_structure")
    if isinstance(price_action_structure, dict):
        candidate["price_action_structure"] = price_action_structure

    deterministic_scores = payload.get("deterministic_scores") if isinstance(payload, dict) else {}
    if isinstance(deterministic_scores, dict):
        for field in AIReportOutput.model_fields:
            if field.endswith("_score") and field in deterministic_scores:
                candidate[field] = deterministic_scores[field]
    return candidate


def _create_anthropic_message(client: Any, model: str, payload: dict, retry: bool) -> Any:
    user_content = _retry_user_content(payload, retry)
    try:
        return client.messages.create(
            model=model,
            max_tokens=3500,
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
            max_tokens=3500,
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
    json_schema_response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "ai_report_output",
            "strict": True,
            "schema": OUTPUT_RESPONSE_SCHEMA,
        },
    }
    base_request: dict[str, Any] = {
        "model": model,
        "response_format": json_schema_response_format,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _retry_user_content(payload, retry)},
        ],
    }

    request_variants = [
        {"max_completion_tokens": 3500, "temperature": 0.3},
        {"max_completion_tokens": 3500},
        {"max_tokens": 3500, "temperature": 0.3},
        {"max_tokens": 3500},
    ]
    last_error: BadRequestError | None = None

    for overrides in request_variants:
        request = {**base_request, **overrides}
        try:
            logger.info(
                "OpenAI report request model=%s retry=%s params=%s response_format=%s",
                model,
                retry,
                ",".join(sorted(overrides.keys())),
                "response_format" in request,
            )
            return client.chat.completions.create(**request)
        except BadRequestError as exc:
            message = str(exc).lower()
            logger.warning("OpenAI report request rejected model=%s params=%s error=%s", model, ",".join(sorted(overrides.keys())), exc)
            retryable_parameter_error = any(
                parameter in message
                for parameter in ("max_tokens", "max_completion_tokens", "temperature")
            )
            retryable_response_format_error = "response_format" in message or "json_schema" in message
            if retryable_response_format_error and request.get("response_format") == json_schema_response_format:
                base_request["response_format"] = {"type": "json_object"}
                last_error = exc
                continue
            if not retryable_parameter_error:
                last_error = exc
                break
            last_error = exc

    request = {**base_request, "max_completion_tokens": 3500}
    request.pop("response_format", None)
    try:
        logger.info("OpenAI report request retrying without response_format model=%s retry=%s", model, retry)
        return client.chat.completions.create(**request)
    except BadRequestError as exc:
        logger.warning("OpenAI report request failed without response_format model=%s error=%s", model, exc)
        if last_error is not None:
            raise last_error
        raise


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
    content = _openai_compatible_content(message)
    if not content.strip():
        logger.warning("OpenAI report response was empty model=%s input_tokens=%s output_tokens=%s", model, input_tokens, output_tokens)
    parsed = _extract_json(content)
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
            logger.info(
                "AI report generation attempt ticker=%s user_id=%s provider=%s model=%s attempt=%s",
                ticker.strip().upper(),
                user_id,
                settings.ai_provider,
                model,
                attempt + 1,
            )
            parsed, input_tokens, output_tokens = _generate_raw_report(payload, model, retry=attempt > 0)
            total_input_tokens += input_tokens
            total_output_tokens += output_tokens

            parsed = _attach_deterministic_report_fields(parsed, payload)
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
            logger.warning(
                "AI report response validation failed ticker=%s user_id=%s attempt=%s error=%s",
                ticker.strip().upper(),
                user_id,
                attempt + 1,
                exc,
            )
            if attempt == 0:
                continue
        except HTTPException as exc:
            logger.warning(
                "AI report HTTP failure ticker=%s user_id=%s status=%s detail=%s",
                ticker.strip().upper(),
                user_id,
                exc.status_code,
                exc.detail,
            )
            raise
        except Exception as exc:
            last_error = str(exc)
            logger.exception("AI report generation crashed ticker=%s user_id=%s", ticker.strip().upper(), user_id)
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
