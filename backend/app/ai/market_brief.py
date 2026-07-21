"""Daily Market Brief — payload builder, LLM generation, and email render.

Self-contained module for QuantorSignal's once-per-day AI market brief. The
brief is generated a single time per trading day (ONE LLM call), cached in
Redis, then fanned out to eligible subscribers by
``app.jobs.daily_brief_job``.

Public surface:
    - ``build_brief_payload(db) -> dict | None`` — market snapshot from the
      latest two dates in ``daily_ohlcv`` (index proxies, sector performance,
      top movers, aggregate breadth). Computed with a handful of set-based
      queries; no per-ticker loops.
    - ``generate_brief(payload, force=False) -> dict | None`` — ONE LLM call
      producing ``{headline, market_summary, sector_rotation, notable_movers,
      watch_today}``. Validates + retries once, caches in Redis for 48h so
      re-runs never re-call the LLM, and skips entirely when EMAIL_ENABLED is
      off (unless ``force`` — used by the admin preview).
    - ``render_brief_html(payload, brief) -> str`` — email body composed from
      the shared template block helpers.
    - ``brief_subject(payload, brief) -> str`` — subject line.

Provider switching (Anthropic vs OpenAI-compatible), client construction, and
usage extraction follow the conventions in ``app.ai.llm_client``.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ValidationError, field_validator
from sqlalchemy import and_, func
from sqlalchemy.orm import Session, aliased

from app.config import settings
from app.database.models import DailyOHLCV, StockFundamental, Ticker
from app.services import email_templates as tpl
from app.services.cache import cache_service

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------
# Index proxies (ETFs) used as headline market gauges.
INDEX_SYMBOLS = ["SPY", "QQQ", "DIA", "IWM"]
INDEX_NAMES = {
    "SPY": "S&P 500",
    "QQQ": "Nasdaq 100",
    "DIA": "Dow Jones",
    "IWM": "Russell 2000",
}

# Liquidity filter for the tradable universe (movers / sectors / breadth).
LIQ_MIN_PRICE = 2.0
LIQ_MIN_VOLUME = 200_000

# 48h so re-runs the same day NEVER re-call the LLM.
BRIEF_CACHE_TTL_SECONDS = 48 * 60 * 60


# ----------------------------------------------------------------------------
# Output schema / validation
# ----------------------------------------------------------------------------
BRIEF_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "headline": {"type": "string"},
        "market_summary": {"type": "string"},
        "sector_rotation": {"type": "string"},
        "notable_movers": {"type": "string"},
        "watch_today": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "headline",
        "market_summary",
        "sector_rotation",
        "notable_movers",
        "watch_today",
    ],
}


class BriefOutput(BaseModel):
    """Validated shape of the LLM's market-brief JSON."""

    headline: str
    market_summary: str
    sector_rotation: str
    notable_movers: str
    watch_today: list[str]

    @field_validator("headline", "market_summary", "sector_rotation", "notable_movers")
    @classmethod
    def _non_empty_text(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("text field must be a non-empty string")
        return " ".join(value.split())

    @field_validator("watch_today")
    @classmethod
    def _clean_bullets(cls, value: Any) -> list[str]:
        if not isinstance(value, list):
            raise ValueError("watch_today must be a list")
        items = [" ".join(str(x).split()) for x in value if str(x).strip()]
        if not items:
            raise ValueError("watch_today must contain at least one bullet")
        # Keep 2-3 bullets; clamp rather than reject to avoid needless retries.
        return items[:3]


# ----------------------------------------------------------------------------
# 1. Market payload builder
# ----------------------------------------------------------------------------
def build_brief_payload(db: Session) -> Optional[dict[str, Any]]:
    """Assemble the market snapshot for the brief from ``daily_ohlcv``.

    Uses the latest two dates present in ``daily_ohlcv``. Returns ``None`` when
    fewer than two trading days of data exist. Everything is computed with a
    small number of set-based queries; aggregation happens in-process over the
    single result set (no per-ticker round-trips).
    """
    # One query for the most recent (up to) 20 distinct dates. The two newest
    # drive the % change; all of them feed the 20-day average-volume fallback.
    recent_dates = [
        row[0]
        for row in (
            db.query(DailyOHLCV.date)
            .distinct()
            .order_by(DailyOHLCV.date.desc())
            .limit(20)
            .all()
        )
    ]
    if len(recent_dates) < 2:
        return None
    latest_date, prev_date = recent_dates[0], recent_dates[1]

    # 20-day average volume per ticker — the liquidity fallback when a ticker
    # has no stored avg_volume in stock_fundamentals.
    avg_vol_map: dict[int, float] = {
        int(ticker_id): float(avg_volume)
        for ticker_id, avg_volume in (
            db.query(DailyOHLCV.ticker_id, func.avg(DailyOHLCV.volume))
            .filter(DailyOHLCV.date.in_(recent_dates))
            .group_by(DailyOHLCV.ticker_id)
            .all()
        )
        if avg_volume is not None
    }

    # Single set-based join: latest close + prior close + sector + avg_volume
    # for every ticker present on both dates.
    latest = aliased(DailyOHLCV)
    prev = aliased(DailyOHLCV)
    rows = (
        db.query(
            Ticker.id.label("id"),
            Ticker.symbol.label("symbol"),
            Ticker.name.label("name"),
            StockFundamental.sector.label("sector"),
            StockFundamental.avg_volume.label("avg_volume"),
            latest.close.label("close"),
            latest.volume.label("volume"),
            prev.close.label("prev_close"),
        )
        .select_from(Ticker)
        .join(latest, and_(latest.ticker_id == Ticker.id, latest.date == latest_date))
        .join(prev, and_(prev.ticker_id == Ticker.id, prev.date == prev_date))
        .outerjoin(StockFundamental, StockFundamental.ticker_id == Ticker.id)
        .all()
    )

    indices_map: dict[str, dict[str, Any]] = {}
    liquid: list[dict[str, Any]] = []

    for r in rows:
        if r.close is None or r.prev_close is None or r.prev_close == 0:
            continue
        close = float(r.close)
        change_pct = round((close - float(r.prev_close)) / float(r.prev_close) * 100.0, 2)

        if r.symbol in INDEX_NAMES:
            indices_map[r.symbol] = {
                "symbol": r.symbol,
                "name": INDEX_NAMES[r.symbol],
                "close": round(close, 2),
                "change_pct": change_pct,
            }

        eff_volume = r.avg_volume or avg_vol_map.get(int(r.id)) or r.volume or 0
        if close >= LIQ_MIN_PRICE and float(eff_volume) >= LIQ_MIN_VOLUME:
            liquid.append(
                {
                    "symbol": r.symbol,
                    "name": r.name,
                    "sector": r.sector,
                    "close": round(close, 2),
                    "change_pct": change_pct,
                }
            )

    indices = [indices_map[s] for s in INDEX_SYMBOLS if s in indices_map]

    # Sector performance (liquid universe, non-null sectors).
    sector_agg: dict[str, dict[str, float]] = defaultdict(
        lambda: {"sum": 0.0, "adv": 0, "dec": 0, "count": 0}
    )
    for rec in liquid:
        sector = rec["sector"]
        if not sector:
            continue
        agg = sector_agg[sector]
        agg["sum"] += rec["change_pct"]
        agg["count"] += 1
        if rec["change_pct"] > 0:
            agg["adv"] += 1
        elif rec["change_pct"] < 0:
            agg["dec"] += 1

    sectors = [
        {
            "sector": sector,
            "avg_change_pct": round(agg["sum"] / agg["count"], 2),
            "advancers": int(agg["adv"]),
            "decliners": int(agg["dec"]),
            "count": int(agg["count"]),
        }
        for sector, agg in sector_agg.items()
        if agg["count"] > 0
    ]
    sectors.sort(key=lambda s: s["avg_change_pct"], reverse=True)

    # Aggregate breadth over the liquid universe.
    total = len(liquid)
    up = sum(1 for r in liquid if r["change_pct"] > 0)
    down = sum(1 for r in liquid if r["change_pct"] < 0)
    flat = total - up - down
    breadth = {
        "advancers": up,
        "decliners": down,
        "unchanged": flat,
        "total": total,
        "pct_up": round(up / total * 100.0, 1) if total else 0.0,
        "pct_down": round(down / total * 100.0, 1) if total else 0.0,
    }

    top_gainers = sorted(liquid, key=lambda r: r["change_pct"], reverse=True)[:5]
    top_losers = sorted(liquid, key=lambda r: r["change_pct"])[:5]

    return {
        "as_of_date": latest_date.isoformat(),
        "prior_date": prev_date.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "indices": indices,
        "sectors": sectors,
        "top_gainers": top_gainers,
        "top_losers": top_losers,
        "breadth": breadth,
        "universe_size": total,
    }


# ----------------------------------------------------------------------------
# 2. LLM generation
# ----------------------------------------------------------------------------
BRIEF_SYSTEM_PROMPT = (
    "You are a professional markets-desk analyst writing QuantorSignal's Daily "
    "Market Brief, a short pre-market email for experienced retail traders. "
    "Write in a concise, factual, neutral-professional tone. "
    "Describe only what the supplied data shows; never invent prices, "
    "percentages, tickers, catalysts, or news. "
    "No hype, no exclamation marks, no emojis. "
    "Do not give personalized financial advice, buy/sell recommendations, "
    "price targets, or predictions of future prices. You may describe observed "
    "moves and note what traders may reasonably watch, framed as general "
    "observations. Every percentage or price level you cite must come directly "
    "from the supplied data."
)

BRIEF_OUTPUT_INSTRUCTIONS = (
    "Return ONE JSON object with exactly these keys:\n"
    "- headline: a single factual sentence (~90 characters max) summarizing the session.\n"
    "- market_summary: 2-4 sentences on overall index performance and market breadth.\n"
    "- sector_rotation: 2-4 sentences on which sectors led and which lagged.\n"
    "- notable_movers: 2-4 sentences on the standout gainers and losers.\n"
    "- watch_today: an array of 2-3 short bullet strings on themes to watch, "
    "each phrased as a general observation (not advice).\n"
    "Do not include any keys other than these five. Do not add commentary "
    "outside the JSON object."
)


def _llm_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Trim the full payload to the fields the model needs (keeps tokens low)."""
    sectors = payload.get("sectors", [])
    return {
        "as_of_date": payload["as_of_date"],
        "prior_date": payload["prior_date"],
        "indices": payload["indices"],
        "breadth": payload["breadth"],
        "sectors_leading": sectors[:6],
        "sectors_lagging": sectors[-6:] if len(sectors) > 6 else [],
        "top_gainers": payload["top_gainers"],
        "top_losers": payload["top_losers"],
        "universe_size": payload["universe_size"],
    }


def _user_content(payload: dict[str, Any], retry: bool) -> str:
    content = (
        "Here is today's US market data as JSON. Write the brief strictly about "
        "this data:\n"
        f"{json.dumps(_llm_payload(payload), sort_keys=True, default=str)}\n\n"
        f"{BRIEF_OUTPUT_INSTRUCTIONS}"
    )
    if retry:
        content += (
            "\n\nThe previous response was invalid. Return ONLY one JSON object "
            "with keys headline, market_summary, sector_rotation, notable_movers, "
            "and watch_today."
        )
    return content


def _extract_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(text[start : end + 1])


# --- Anthropic -------------------------------------------------------------
def _anthropic_usage(message: Any) -> tuple[int, int]:
    usage = getattr(message, "usage", None)
    if usage is None:
        return 0, 0
    return (
        int(getattr(usage, "input_tokens", 0) or 0),
        int(getattr(usage, "output_tokens", 0) or 0),
    )


def _anthropic_payload(message: Any) -> dict[str, Any] | str:
    parts = getattr(message, "content", None) or []
    for part in parts:
        if getattr(part, "type", None) == "tool_use":
            tool_input = getattr(part, "input", None)
            if isinstance(tool_input, dict):
                return tool_input
    texts = [getattr(p, "text", "") or "" for p in parts]
    return "".join(texts)


def _generate_with_anthropic(payload: dict[str, Any], model: str, retry: bool) -> tuple[dict[str, Any], int, int]:
    try:
        from anthropic import Anthropic
    except ImportError as exc:  # pragma: no cover - dependency guaranteed in prod
        raise RuntimeError("anthropic package is not installed") from exc

    api_key = settings.anthropic_api_key or settings.ai_api_key or None
    client = Anthropic(api_key=api_key) if api_key else Anthropic()
    user_content = _user_content(payload, retry)
    try:
        message = client.messages.create(
            model=model,
            max_tokens=1500,
            temperature=0.3,
            system=BRIEF_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
            tools=[
                {
                    "name": "emit_market_brief",
                    "description": "Emit the daily market brief as a structured JSON object.",
                    "input_schema": BRIEF_RESPONSE_SCHEMA,
                }
            ],
            tool_choice={"type": "tool", "name": "emit_market_brief"},
        )
    except TypeError:
        message = client.messages.create(
            model=model,
            max_tokens=1500,
            temperature=0.3,
            system=BRIEF_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )

    input_tokens, output_tokens = _anthropic_usage(message)
    candidate = _anthropic_payload(message)
    parsed = candidate if isinstance(candidate, dict) else _extract_json(candidate)
    return parsed, input_tokens, output_tokens


# --- OpenAI-compatible -----------------------------------------------------
def _openai_result(response: Any) -> tuple[dict[str, Any], int, int]:
    choices = getattr(response, "choices", None) or []
    content = (
        getattr(getattr(choices[0], "message", None), "content", None) if choices else None
    )
    usage = getattr(response, "usage", None)
    input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0) if usage else 0
    output_tokens = int(getattr(usage, "completion_tokens", 0) or 0) if usage else 0
    parsed = _extract_json(content or "")
    return parsed, input_tokens, output_tokens


def _generate_with_openai(payload: dict[str, Any], model: str, retry: bool) -> tuple[dict[str, Any], int, int]:
    try:
        from openai import BadRequestError, OpenAI
    except ImportError as exc:  # pragma: no cover - dependency guaranteed in prod
        raise RuntimeError("openai package is not installed") from exc

    api_key = settings.openai_api_key or settings.ai_api_key
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY or AI_API_KEY is not set")

    client = OpenAI(api_key=api_key, base_url=settings.openai_base_url.rstrip("/"), timeout=60.0)
    messages = [
        {"role": "system", "content": BRIEF_SYSTEM_PROMPT},
        {"role": "user", "content": _user_content(payload, retry)},
    ]
    json_schema_format = {
        "type": "json_schema",
        "json_schema": {"name": "market_brief", "strict": True, "schema": BRIEF_RESPONSE_SCHEMA},
    }
    base: dict[str, Any] = {"model": model, "messages": messages, "response_format": json_schema_format}
    variants = [
        {"max_completion_tokens": 1500, "temperature": 0.3},
        {"max_completion_tokens": 1500},
        {"max_tokens": 1500, "temperature": 0.3},
        {"max_tokens": 1500},
    ]
    last_error: Optional[Exception] = None

    for overrides in variants:
        request = {**base, **overrides}
        try:
            return _openai_result(client.chat.completions.create(**request))
        except BadRequestError as exc:
            message = str(exc).lower()
            last_error = exc
            if (
                ("response_format" in message or "json_schema" in message)
                and request.get("response_format") == json_schema_format
            ):
                base["response_format"] = {"type": "json_object"}
                continue
            if not any(p in message for p in ("max_tokens", "max_completion_tokens", "temperature")):
                break

    # Last resort: no response_format at all (prompt still demands JSON).
    request = {**base, "max_completion_tokens": 1500}
    request.pop("response_format", None)
    try:
        return _openai_result(client.chat.completions.create(**request))
    except BadRequestError:
        if last_error is not None:
            raise last_error
        raise


def _generate_raw_brief(payload: dict[str, Any], retry: bool) -> tuple[dict[str, Any], int, int]:
    provider = (settings.ai_provider or "").strip().lower().replace("_", "-")
    model = settings.ai_model
    if provider in {"anthropic", "claude"}:
        return _generate_with_anthropic(payload, model, retry)
    if provider in {"openai", "openai-compatible", "compatible"}:
        return _generate_with_openai(payload, model, retry)
    raise RuntimeError(f"unsupported ai_provider: {settings.ai_provider}")


def _generate_and_validate(payload: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Run the LLM call, validating the JSON and retrying once on failure."""
    model = settings.ai_model
    last_error = "unknown_error"
    for attempt in range(2):
        try:
            parsed, input_tokens, output_tokens = _generate_raw_brief(payload, retry=attempt > 0)
            validated = BriefOutput.model_validate(parsed)
            result = validated.model_dump(mode="json")
            result["_usage"] = {
                "provider": settings.ai_provider,
                "model_used": model,
                "tokens_input": input_tokens,
                "tokens_output": output_tokens,
            }
            return result
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            last_error = str(exc)
            logger.warning("Daily brief validation failed attempt=%s error=%s", attempt + 1, exc)
            continue
        except Exception as exc:  # network / provider / SDK failure
            last_error = str(exc)
            logger.exception("Daily brief generation crashed")
            break

    logger.error("Daily brief generation failed after retries: %s", last_error)
    return None


def generate_brief(payload: Optional[dict[str, Any]], force: bool = False) -> Optional[dict[str, Any]]:
    """Generate (or fetch cached) the market brief for ``payload``'s date.

    - Returns ``None`` when ``payload`` is ``None`` (insufficient data).
    - Skips generation entirely (logs + returns ``None``) when EMAIL_ENABLED is
      False, unless ``force`` is set — so the nightly job never burns tokens
      while email is off, but the admin preview can still render one.
    - Reads/writes Redis key ``brief:<date>`` (48h TTL): a same-day re-run
      NEVER re-calls the LLM.
    """
    if payload is None:
        return None

    as_of = payload["as_of_date"]

    if not settings.EMAIL_ENABLED and not force:
        logger.info("Daily brief generation skipped: EMAIL_ENABLED is False (as_of=%s)", as_of)
        return None

    cache_key = f"brief:{as_of}"
    cached = cache_service.get(cache_key)
    if cached:
        logger.info("Daily brief cache hit for %s", as_of)
        return cached

    brief = _generate_and_validate(payload)
    if brief is not None:
        cache_service.set(cache_key, brief, ttl=BRIEF_CACHE_TTL_SECONDS)
        logger.info(
            "Daily brief generated for %s (tokens_in=%s tokens_out=%s)",
            as_of,
            brief.get("_usage", {}).get("tokens_input"),
            brief.get("_usage", {}).get("tokens_output"),
        )
    return brief


# ----------------------------------------------------------------------------
# 3. Email render
# ----------------------------------------------------------------------------
def _watch_bullets(items: list[str]) -> str:
    """Render the 'What to watch' bullets as a styled list."""
    lis = "".join(
        f'<li style="font-family:{tpl.FONT};font-size:15px;line-height:1.55;'
        f'color:{tpl.INK};margin:0 0 6px;">{tpl._esc(item)}</li>'
        for item in items
    )
    return f'<ul style="margin:0 0 14px;padding-left:20px;">{lis}</ul>'


def _sector_line(sector: dict[str, Any]) -> str:
    value = f'{sector["advancers"]}▲ / {sector["decliners"]}▼'
    return tpl.stat_row(sector["sector"], value, change_pct=sector["avg_change_pct"])


def render_brief_html(payload: dict[str, Any], brief: dict[str, Any]) -> str:
    """Compose the email body from the shared template block helpers.

    Returns body-content HTML (headline lives in the subject / base H1). The
    email service wraps this in the branded base template + unsubscribe footer.
    """
    parts: list[str] = []

    # Lead summary.
    parts.append(tpl.paragraph(brief["market_summary"]))

    # Index stat rows.
    parts.append(tpl.heading("Major Indices"))
    if payload["indices"]:
        for idx in payload["indices"]:
            parts.append(
                tpl.stat_row(
                    f'{idx["symbol"]} · {idx["name"]}',
                    f'${idx["close"]:,.2f}',
                    change_pct=idx["change_pct"],
                )
            )
    else:
        parts.append(tpl.paragraph("Index data was unavailable for this session."))

    # Breadth.
    breadth = payload["breadth"]
    parts.append(
        tpl.stat_row(
            "Market breadth (advancers)",
            f'{breadth["pct_up"]:.1f}% up · {breadth["pct_down"]:.1f}% down',
        )
    )

    # Sector rotation.
    parts.append(tpl.heading("Sector Rotation"))
    parts.append(tpl.paragraph(brief["sector_rotation"]))
    sectors = payload["sectors"]
    winners = sectors[:3]
    losers = [s for s in reversed(sectors[-3:]) if s not in winners]
    for sector in winners:
        parts.append(_sector_line(sector))
    if losers:
        parts.append(tpl.divider())
        for sector in losers:
            parts.append(_sector_line(sector))

    # Notable movers as compact ticker cards.
    parts.append(tpl.heading("Notable Movers"))
    parts.append(tpl.paragraph(brief["notable_movers"]))
    for mover in payload["top_gainers"]:
        parts.append(
            tpl.ticker_card(
                mover["symbol"],
                mover["name"] or "",
                [
                    f'${mover["close"]:,.2f} ({mover["change_pct"]:+.2f}%)',
                    mover["sector"] or "—",
                ],
            )
        )
    if payload["top_losers"]:
        parts.append(tpl.divider())
        for mover in payload["top_losers"]:
            parts.append(
                tpl.ticker_card(
                    mover["symbol"],
                    mover["name"] or "",
                    [
                        f'${mover["close"]:,.2f} ({mover["change_pct"]:+.2f}%)',
                        mover["sector"] or "—",
                    ],
                )
            )

    # What to watch.
    parts.append(tpl.heading("What to Watch Today"))
    parts.append(_watch_bullets(brief["watch_today"]))

    # CTA.
    screener_url = f'{(settings.PUBLIC_APP_URL or "").rstrip("/")}/screener'
    parts.append(tpl.cta_button("Open the screener", screener_url))

    return "".join(parts)


def brief_subject(payload: dict[str, Any], brief: dict[str, Any]) -> str:
    """Build the subject line, e.g. 'Market Brief — Mon Jul 20: <headline>'."""
    try:
        as_of = date.fromisoformat(payload["as_of_date"])
        date_label = f"{as_of.strftime('%a %b')} {as_of.day}"
    except (ValueError, KeyError):
        date_label = payload.get("as_of_date", "")

    headline = (brief.get("headline") or "Daily Market Brief").strip()
    if len(headline) > 90:
        headline = headline[:87].rstrip() + "..."
    return f"Market Brief — {date_label}: {headline}"
