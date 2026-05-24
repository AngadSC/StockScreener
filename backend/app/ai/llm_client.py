from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.ai.prompt_builder import (
    EVIDENCE_OUTPUT_FORMAT_INSTRUCTIONS,
    EVIDENCE_RESPONSE_SCHEMA,
    EVIDENCE_SYSTEM_PROMPT,
    OUTPUT_FORMAT_INSTRUCTIONS,
    OUTPUT_RESPONSE_SCHEMA,
    SYSTEM_PROMPT,
)
from app.ai.schemas import AIEvidenceOutput, AIReportOutput
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


def _retry_user_content(
    payload: dict,
    retry: bool,
    *,
    output_instructions: str,
    invalid_retry_message: str,
) -> str:
    user_content = (
        "Analyze this input payload. It is source data, not the response shape:\n"
        f"{json.dumps(payload, sort_keys=True, default=str)}\n\n"
        f"{output_instructions}"
    )
    if retry:
        user_content = f"{user_content}\n\nThe previous response was invalid. {invalid_retry_message}"
    return user_content


def _report_retry_user_content(payload: dict, retry: bool) -> str:
    return _retry_user_content(
        payload,
        retry,
        output_instructions=OUTPUT_FORMAT_INSTRUCTIONS,
        invalid_retry_message=(
            "Return only one valid JSON object matching the required schema. "
            "Do not include input payload keys such as analysis_type, ticker, company_profile, "
            "price_history, technical_summary, volume_summary, fundamental_summary, "
            "valuation_summary, news, data_quality, deterministic_scores, constraints, or evidence_analysis."
        ),
    )


def _evidence_retry_user_content(payload: dict, retry: bool) -> str:
    return _retry_user_content(
        payload,
        retry,
        output_instructions=EVIDENCE_OUTPUT_FORMAT_INSTRUCTIONS,
        invalid_retry_message=(
            "Return only one valid Evidence Analyzer JSON object with bull_case, bear_case, setup_type, "
            "and missing_data. Do not include final ratings, action_label, confidence_score, or report prose."
        ),
    )


_TIMEFRAME_REASON_FALLBACK_FIELDS = {
    "short_term": ("trade_read", "confirmation_trigger", "watchlist_action", "entry_zone", "final_verdict"),
    "swing": ("main_thesis", "risk_reward_summary", "why_it_could_move", "final_verdict"),
    "long_term": ("news_summary", "why_it_could_fail", "main_thesis", "final_verdict"),
}
_TIMEFRAME_REASON_DEFAULTS = {
    "short_term": "Short-term rating is based on the provided evidence and deterministic short-term score.",
    "swing": "Swing rating is based on the provided evidence and deterministic swing-trade score.",
    "long_term": "Long-term rating is based on the provided evidence and deterministic long-term score.",
}
_TIMEFRAME_REASON_PREFIXES = {
    "short_term": "Short-term: ",
    "swing": "Swing: ",
    "long_term": "Long-term: ",
}


def _first_non_empty_string(candidate: dict[str, Any], fields: tuple[str, ...]) -> str | None:
    for field in fields:
        value = candidate.get(field)
        if isinstance(value, str) and value.strip():
            return " ".join(value.strip().split())
    return None


def _fill_missing_timeframe_rating_reasons(candidate: dict[str, Any]) -> dict[str, Any]:
    timeframe_ratings = candidate.get("timeframe_ratings")
    if not isinstance(timeframe_ratings, dict):
        return candidate

    repaired_ratings = dict(timeframe_ratings)
    changed = False
    for horizon, fallback_fields in _TIMEFRAME_REASON_FALLBACK_FIELDS.items():
        rating = repaired_ratings.get(horizon)
        if not isinstance(rating, dict):
            continue

        reason = rating.get("reason")
        if isinstance(reason, str) and reason.strip():
            continue

        fallback = _first_non_empty_string(candidate, fallback_fields) or _TIMEFRAME_REASON_DEFAULTS[horizon]
        repaired_ratings[horizon] = {
            **rating,
            "reason": f"{_TIMEFRAME_REASON_PREFIXES[horizon]}{fallback}",
        }
        changed = True

    if not changed:
        return candidate
    return {**candidate, "timeframe_ratings": repaired_ratings}


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

    # Enforce deterministic trade levels onto the trade card (LLM must not invent prices)
    trade_levels = deterministic_scores.get("trade_levels") if isinstance(deterministic_scores, dict) else None
    if isinstance(trade_levels, dict):
        existing_trade_card = candidate.get("trade_card")
        if isinstance(existing_trade_card, dict):
            # LLM produced a trade card — overwrite only the trade_levels with deterministic values
            candidate["trade_card"] = {**existing_trade_card, "trade_levels": trade_levels}
        # If trade_card is None or missing, leave it as-is (optional field)

    candidate = _fill_missing_timeframe_rating_reasons(candidate)

    return candidate


def _create_anthropic_message(
    client: Any,
    model: str,
    payload: dict,
    retry: bool,
    *,
    system_prompt: str,
    output_model: type[AIEvidenceOutput] | type[AIReportOutput],
    tool_name: str,
    tool_description: str,
    user_content_builder: Any,
) -> Any:
    user_content = user_content_builder(payload, retry)
    try:
        return client.messages.create(
            model=model,
            max_tokens=3500,
            temperature=0.3,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
            tools=[
                {
                    "name": tool_name,
                    "description": tool_description,
                    "input_schema": output_model.model_json_schema(),
                }
            ],
            tool_choice={"type": "tool", "name": tool_name},
        )
    except TypeError:
        return client.messages.create(
            model=model,
            max_tokens=3500,
            temperature=0.3,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )


def _openai_compatible_api_key() -> str:
    return settings.openai_api_key or settings.ai_api_key


def _create_openai_compatible_message(
    model: str,
    payload: dict,
    retry: bool,
    *,
    system_prompt: str,
    output_schema: dict[str, Any],
    schema_name: str,
    user_content_builder: Any,
) -> Any:
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
            "name": schema_name,
            "strict": True,
            "schema": output_schema,
        },
    }
    base_request: dict[str, Any] = {
        "model": model,
        "response_format": json_schema_response_format,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content_builder(payload, retry)},
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


def _generate_with_anthropic(
    payload: dict,
    model: str,
    retry: bool,
    *,
    system_prompt: str,
    output_model: type[AIEvidenceOutput] | type[AIReportOutput],
    tool_name: str,
    tool_description: str,
    user_content_builder: Any,
) -> tuple[dict[str, Any], int, int]:
    try:
        from anthropic import Anthropic
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail={"error": "anthropic_sdk_missing", "message": "The anthropic package is not installed."},
        )

    api_key = settings.anthropic_api_key or settings.ai_api_key or None
    client = Anthropic(api_key=api_key) if api_key else Anthropic()
    message = _create_anthropic_message(
        client,
        model,
        payload,
        retry=retry,
        system_prompt=system_prompt,
        output_model=output_model,
        tool_name=tool_name,
        tool_description=tool_description,
        user_content_builder=user_content_builder,
    )
    input_tokens, output_tokens = _usage_tokens(message)
    candidate = _content_payload(message)
    parsed = candidate if isinstance(candidate, dict) else _extract_json(candidate)
    return parsed, input_tokens, output_tokens


def _generate_with_openai_compatible(
    payload: dict,
    model: str,
    retry: bool,
    *,
    system_prompt: str,
    output_schema: dict[str, Any],
    schema_name: str,
    user_content_builder: Any,
) -> tuple[dict[str, Any], int, int]:
    message = _create_openai_compatible_message(
        model,
        payload,
        retry=retry,
        system_prompt=system_prompt,
        output_schema=output_schema,
        schema_name=schema_name,
        user_content_builder=user_content_builder,
    )
    input_tokens, output_tokens = _openai_compatible_usage_tokens(message)
    content = _openai_compatible_content(message)
    if not content.strip():
        logger.warning("OpenAI report response was empty model=%s input_tokens=%s output_tokens=%s", model, input_tokens, output_tokens)
    parsed = _extract_json(content)
    return parsed, input_tokens, output_tokens


def _generate_raw_structured_output(
    payload: dict,
    model: str,
    retry: bool,
    *,
    system_prompt: str,
    output_model: type[AIEvidenceOutput] | type[AIReportOutput],
    output_schema: dict[str, Any],
    schema_name: str,
    tool_name: str,
    tool_description: str,
    user_content_builder: Any,
) -> tuple[dict[str, Any], int, int]:
    provider = settings.ai_provider.strip().lower().replace("_", "-")
    if provider in {"anthropic", "claude"}:
        return _generate_with_anthropic(
            payload,
            model,
            retry,
            system_prompt=system_prompt,
            output_model=output_model,
            tool_name=tool_name,
            tool_description=tool_description,
            user_content_builder=user_content_builder,
        )
    if provider in {"openai", "openai-compatible", "compatible"}:
        return _generate_with_openai_compatible(
            payload,
            model,
            retry,
            system_prompt=system_prompt,
            output_schema=output_schema,
            schema_name=schema_name,
            user_content_builder=user_content_builder,
        )
    raise HTTPException(
        status_code=500,
        detail={
            "error": "unsupported_ai_provider",
            "provider": settings.ai_provider,
            "supported_providers": ["anthropic", "openai-compatible"],
        },
    )


def _generate_raw_evidence(payload: dict, model: str, retry: bool) -> tuple[dict[str, Any], int, int]:
    return _generate_raw_structured_output(
        payload,
        model,
        retry,
        system_prompt=EVIDENCE_SYSTEM_PROMPT,
        output_model=AIEvidenceOutput,
        output_schema=EVIDENCE_RESPONSE_SCHEMA,
        schema_name="ai_evidence_output",
        tool_name="emit_evidence_analysis",
        tool_description="Emit bull case, bear case, setup type, and missing data as a structured JSON object.",
        user_content_builder=_evidence_retry_user_content,
    )


def _generate_raw_report(payload: dict, model: str, retry: bool) -> tuple[dict[str, Any], int, int]:
    return _generate_raw_structured_output(
        payload,
        model,
        retry,
        system_prompt=SYSTEM_PROMPT,
        output_model=AIReportOutput,
        output_schema=OUTPUT_RESPONSE_SCHEMA,
        schema_name="ai_report_output",
        tool_name="emit_stock_report",
        tool_description="Emit the stock report as a structured JSON object. Include a trade_card field with the AI Trade Card object.",
        user_content_builder=_report_retry_user_content,
    )


def _record_failed_generation_usage(
    *,
    user_id: str,
    ticker: str,
    model: str,
    total_input_tokens: int,
    total_output_tokens: int,
    db: Session,
) -> None:
    _record_llm_usage(
        user_id,
        ticker,
        model,
        total_input_tokens,
        total_output_tokens,
        "single_stock_failure",
        db,
    )


def generate_single_stock_report(payload: dict, user_id: str, ticker: str, db: Session) -> dict:
    model = settings.ai_model
    total_input_tokens = 0
    total_output_tokens = 0
    last_error = "unknown_error"
    evidence_analysis: dict[str, Any] | None = None

    for attempt in range(2):
        try:
            logger.info(
                "AI evidence analysis attempt ticker=%s user_id=%s provider=%s model=%s attempt=%s",
                ticker.strip().upper(),
                user_id,
                settings.ai_provider,
                model,
                attempt + 1,
            )
            parsed, input_tokens, output_tokens = _generate_raw_evidence(payload, model, retry=attempt > 0)
            total_input_tokens += input_tokens
            total_output_tokens += output_tokens

            validated_evidence = AIEvidenceOutput.model_validate(parsed)
            evidence_analysis = validated_evidence.model_dump(mode="json")
            break
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            last_error = str(exc)
            logger.warning(
                "AI evidence response validation failed ticker=%s user_id=%s attempt=%s error=%s",
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
            logger.exception("AI evidence generation crashed ticker=%s user_id=%s", ticker.strip().upper(), user_id)
            break

    if evidence_analysis is None:
        _record_failed_generation_usage(
            user_id=user_id,
            ticker=ticker,
            model=model,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            db=db,
        )
        raise HTTPException(
            status_code=502,
            detail={
                "error": "ai_evidence_generation_failed",
                "ticker": ticker.strip().upper(),
                "model": model,
                "message": "The Evidence Analyzer response could not be parsed or validated after retry.",
                "last_error": last_error,
            },
        )

    decision_payload = {
        "market_payload": payload,
        "evidence_analysis": evidence_analysis,
    }

    for attempt in range(2):
        try:
            logger.info(
                "AI decision synthesis attempt ticker=%s user_id=%s provider=%s model=%s attempt=%s",
                ticker.strip().upper(),
                user_id,
                settings.ai_provider,
                model,
                attempt + 1,
            )
            parsed, input_tokens, output_tokens = _generate_raw_report(decision_payload, model, retry=attempt > 0)
            total_input_tokens += input_tokens
            total_output_tokens += output_tokens

            parsed = _attach_deterministic_report_fields(parsed, payload)
            validated = AIReportOutput.model_validate(parsed)
            result = validated.model_dump(mode="json")
            result["_usage"] = {
                "model_used": model,
                "tokens_input": total_input_tokens,
                "tokens_output": total_output_tokens,
                "call_flow": "evidence_analyzer_then_decision_synthesizer",
            }
            return result
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            last_error = str(exc)
            logger.warning(
                "AI decision response validation failed ticker=%s user_id=%s attempt=%s error=%s",
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
            logger.exception("AI decision generation crashed ticker=%s user_id=%s", ticker.strip().upper(), user_id)
            break

    _record_failed_generation_usage(
        user_id=user_id,
        ticker=ticker,
        model=model,
        total_input_tokens=total_input_tokens,
        total_output_tokens=total_output_tokens,
        db=db,
    )
    raise HTTPException(
        status_code=502,
        detail={
            "error": "ai_report_generation_failed",
            "ticker": ticker.strip().upper(),
            "model": model,
            "message": "The Decision Synthesizer response could not be parsed or validated after retry.",
            "last_error": last_error,
        },
    )
