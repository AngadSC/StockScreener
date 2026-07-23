"""Elite "Daily Watchlist AI Digest" engine.

Builds a ranked, per-user digest of the existing AI swing analysis for the
stocks on an Elite user's watchlist and renders it into a scannable email body
composed from the shared ``email_templates`` block helpers.

Design goals:
    - REUSE the existing AI pipeline (cache first, then generate + persist).
      Today's cached reports are free; only genuine cache misses cost an LLM
      call, and digest generations are recorded under a separate usage type so
      they never consume a user's on-demand monthly quota.
    - One failing ticker never kills a user's digest (it becomes an
      "analysis unavailable" line).
    - Day-over-day awareness: compares against the user's report from the
      previous trading day and surfaces score / bias / setup changes.

Public surface:
    - ``build_user_digest(user, db, max_stocks=None, *, llm_budget=None)``
    - ``digest_subject(digest)`` / ``render_digest_html(digest)``
    - ``render_digest_document(digest, unsubscribe_url="#")`` (full HTML page)
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.ai.llm_client import generate_single_stock_report
from app.ai.payload_builder import build_ai_payload
from app.ai.report_cache import get_fresh_report, save_report
from app.ai.usage_limits import record_digest_usage_event
from app.config import settings
from app.database.models import AIStockReport, Ticker, User, Watchlist
from app.services import email_templates as tpl
from app.utils.market_calendar import get_previous_trading_day

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------------
# Ranking / rendering tunables
# ----------------------------------------------------------------------------
# setup_quality_score is validated 0-100 by AIReportOutput (see app/ai/schemas.py),
# so the "strong setup" cut is 65.0 here — equivalent to the 6.5/10 threshold in
# the feature spec. The top-N fallback guarantees a non-empty "Strongest setups"
# section even when nothing clears the bar on a quiet day.
STRONG_SETUP_SCORE_THRESHOLD = 65.0
TOP_N_ALWAYS_STRONG = 3
# Minimum absolute day-over-day quality move (0-100 scale) worth surfacing.
SCORE_DELTA_MIN = 1.0
# Truncate the one-line thesis to keep cards scannable.
THESIS_MAX_CHARS = 180
# Truncate individual trade-level strings so a card line stays compact.
LEVEL_MAX_CHARS = 48

_DIGEST_TIER = "elite"

_BIAS_LABELS = {
    "bullish": "Bullish",
    "bearish": "Bearish",
    "neutral": "Neutral",
    "mixed_bullish_lean": "Mixed (bullish lean)",
    "mixed_bearish_lean": "Mixed (bearish lean)",
}


# ----------------------------------------------------------------------------
# Small text helpers
# ----------------------------------------------------------------------------
def _clean(text: Any) -> str:
    return " ".join(str(text).split()) if text is not None else ""


def _truncate(text: Any, max_chars: int) -> Optional[str]:
    cleaned = _clean(text)
    if not cleaned:
        return None
    if len(cleaned) <= max_chars:
        return cleaned
    head = cleaned[:max_chars].rsplit(" ", 1)[0].rstrip(" .,-")
    return (head or cleaned[:max_chars].rstrip()) + "…"


def _pretty_bias(bias: Any) -> str:
    key = _clean(bias).lower()
    if key in _BIAS_LABELS:
        return _BIAS_LABELS[key]
    return _clean(bias).replace("_", " ").title() or "Neutral"


def _quality_score(report: AIStockReport) -> Optional[float]:
    score = report.setup_quality_score
    if score is None:
        ai = report.ai_report if isinstance(report.ai_report, dict) else {}
        score = ai.get("setup_quality_score")
    try:
        return float(score) if score is not None else None
    except (TypeError, ValueError):
        return None


# ----------------------------------------------------------------------------
# Data access
# ----------------------------------------------------------------------------
def _watchlist_entries(user_id: int, db: Session) -> list[tuple[str, Optional[str]]]:
    """Return (symbol, name) for the user's watchlist, oldest addition first."""
    rows = (
        db.query(Ticker.symbol, Ticker.name)
        .join(Watchlist, Watchlist.ticker_id == Ticker.id)
        .filter(Watchlist.user_id == user_id)
        .order_by(Watchlist.added_at.asc(), Watchlist.id.asc())
        .all()
    )
    return [(symbol, name) for symbol, name in rows]


def _previous_report(
    user_id: int, ticker: str, previous_trading_day: date, db: Session
) -> Optional[AIStockReport]:
    """Most recent report for this user+ticker dated the previous trading day."""
    return (
        db.query(AIStockReport)
        .filter(
            and_(
                AIStockReport.user_id == user_id,
                AIStockReport.ticker == ticker.strip().upper(),
                AIStockReport.report_date == previous_trading_day,
            )
        )
        .order_by(AIStockReport.created_at.desc())
        .first()
    )


def _acquire_report(
    user: User, ticker: str, db: Session, *, allow_llm: bool
) -> tuple[Optional[AIStockReport], str]:
    """Return (report, source) for one ticker.

    source is one of:
        - "cache":       a fresh report already exists today (free)
        - "generated":   a new report was built via the LLM and persisted
        - "unavailable": no cache and LLM generation was not permitted here

    Genuine failures (payload build / generation errors) propagate to the
    caller, which converts them into an "analysis unavailable" card.
    """
    user_id = str(user.id)
    cached = get_fresh_report(user_id, ticker, db)
    if cached is not None:
        return cached, "cache"

    if not allow_llm:
        return None, "unavailable"

    payload = build_ai_payload(ticker, db)
    ai_response = generate_single_stock_report(payload, user_id, ticker, db)
    usage = ai_response.pop("_usage", {}) if isinstance(ai_response, dict) else {}
    if not isinstance(usage, dict):
        usage = {}
    saved = save_report(user_id, ticker, payload, ai_response, _DIGEST_TIER, db)
    record_digest_usage_event(
        user_id=user_id,
        ticker=ticker,
        model_used=str(usage.get("model_used") or settings.ai_model),
        tokens_input=int(usage.get("tokens_input") or 0),
        tokens_output=int(usage.get("tokens_output") or 0),
        db=db,
    )
    return saved, "generated"


# ----------------------------------------------------------------------------
# Day-over-day deltas
# ----------------------------------------------------------------------------
def _compute_delta(
    today_report: AIStockReport, previous_report: Optional[AIStockReport]
) -> dict[str, Any]:
    """Compute the change vs the previous trading day's report."""
    if previous_report is None:
        return {"changed_since_yesterday": False, "delta_line": None, "is_new": True}

    parts: list[str] = []
    changed = False

    cur_score = _quality_score(today_report)
    prev_score = _quality_score(previous_report)
    if cur_score is not None and prev_score is not None:
        delta = round(cur_score - prev_score, 1)
        if abs(delta) >= SCORE_DELTA_MIN:
            parts.append(f"quality {round(prev_score)}→{round(cur_score)} ({delta:+.0f})")
            changed = True

    cur_bias = _clean(today_report.swing_bias).lower()
    prev_bias = _clean(previous_report.swing_bias).lower()
    if cur_bias and prev_bias and cur_bias != prev_bias:
        parts.append(f"{_pretty_bias(previous_report.swing_bias)} → {_pretty_bias(today_report.swing_bias)}")
        changed = True

    cur_setup = _clean(today_report.setup_type).lower()
    prev_setup = _clean(previous_report.setup_type).lower()
    if cur_setup and prev_setup and cur_setup != prev_setup:
        parts.append(f"setup: {_clean(previous_report.setup_type)} → {_clean(today_report.setup_type)}")
        changed = True

    return {
        "changed_since_yesterday": changed,
        "delta_line": " · ".join(parts) if parts else None,
        "is_new": False,
    }


# ----------------------------------------------------------------------------
# Per-stock entry assembly
# ----------------------------------------------------------------------------
def _available_entry(
    symbol: str,
    name: Optional[str],
    report: AIStockReport,
    source: str,
    delta: dict[str, Any],
) -> dict[str, Any]:
    ai = report.ai_report if isinstance(report.ai_report, dict) else {}
    return {
        "ticker": symbol,
        "name": name or symbol,
        "available": True,
        "source": source,
        "quality_score": _quality_score(report),
        "swing_bias": report.swing_bias or ai.get("directional_bias") or ai.get("swing_bias") or "neutral",
        "setup_type": report.setup_type or ai.get("setup_type") or "No clear setup",
        "entry_zone": _truncate(ai.get("entry_zone"), LEVEL_MAX_CHARS),
        "invalidation_level": _truncate(ai.get("invalidation_level"), LEVEL_MAX_CHARS),
        "target_1": _truncate(ai.get("target_1"), LEVEL_MAX_CHARS),
        "thesis": _truncate(ai.get("main_thesis"), THESIS_MAX_CHARS),
        "final_verdict": _truncate(ai.get("final_verdict"), THESIS_MAX_CHARS),
        "changed_since_yesterday": bool(delta.get("changed_since_yesterday")),
        "delta_line": delta.get("delta_line"),
        "is_new": bool(delta.get("is_new")),
        "is_strong": False,
    }


def _unavailable_entry(symbol: str, name: Optional[str], reason: str) -> dict[str, Any]:
    return {
        "ticker": symbol,
        "name": name or symbol,
        "available": False,
        "source": "unavailable",
        "quality_score": None,
        "reason": reason,
        "changed_since_yesterday": False,
        "delta_line": None,
        "is_new": False,
        "is_strong": False,
    }


def _sort_key(entry: dict[str, Any]) -> float:
    score = entry.get("quality_score")
    return float(score) if entry.get("available") and score is not None else -1.0


# ----------------------------------------------------------------------------
# Digest builder
# ----------------------------------------------------------------------------
def build_user_digest(
    user: User,
    db: Session,
    max_stocks: Optional[int] = None,
    *,
    llm_budget: Optional[int] = None,
) -> Optional[dict[str, Any]]:
    """Build the ranked digest payload for one user.

    Args:
        user: the recipient (expected Elite/active; caller enforces tier).
        db: session.
        max_stocks: cap on watchlist tickers analyzed (defaults to
            ``settings.ELITE_DIGEST_MAX_STOCKS``). Oldest additions first.
        llm_budget: max NEW LLM report generations this digest may perform.
            ``None`` means unlimited. When the budget is exhausted, remaining
            cache-miss tickers become "analysis unavailable" lines (no LLM
            call). Cached reports are always used and never count against it.

    Returns:
        The digest dict, or ``None`` if the watchlist is empty.
    """
    limit = max_stocks if max_stocks is not None else settings.ELITE_DIGEST_MAX_STOCKS
    limit = max(int(limit), 0)

    entries = _watchlist_entries(user.id, db)
    if not entries:
        return None

    selected = entries[:limit] if limit else []
    total = len(entries)
    truncated = total > len(selected)
    previous_trading_day = get_previous_trading_day(date.today())

    stocks: list[dict[str, Any]] = []
    llm_calls = 0
    cache_hits = 0
    failures = 0
    budget_left = llm_budget

    for symbol, name in selected:
        allow_llm = budget_left is None or budget_left > 0
        try:
            report, source = _acquire_report(user, symbol, db, allow_llm=allow_llm)
        except Exception:
            logger.exception(
                "Digest ticker analysis failed user_id=%s ticker=%s", user.id, symbol
            )
            failures += 1
            stocks.append(_unavailable_entry(symbol, name, "Analysis unavailable today."))
            continue

        if report is None:
            # Cache miss with no LLM budget remaining (cost guard) — not a failure.
            stocks.append(
                _unavailable_entry(symbol, name, "Not analyzed today (daily analysis limit reached).")
            )
            continue

        if source == "cache":
            cache_hits += 1
        elif source == "generated":
            llm_calls += 1
            if budget_left is not None:
                budget_left -= 1

        previous = _previous_report(user.id, symbol, previous_trading_day, db)
        delta = _compute_delta(report, previous)
        stocks.append(_available_entry(symbol, name, report, source, delta))

    # ----- Ranking + section classification -----
    available = sorted(
        (s for s in stocks if s["available"]), key=_sort_key, reverse=True
    )
    unavailable = [s for s in stocks if not s["available"]]

    for index, entry in enumerate(available):
        score = entry.get("quality_score")
        entry["is_strong"] = (
            score is not None and score >= STRONG_SETUP_SCORE_THRESHOLD
        ) or index < TOP_N_ALWAYS_STRONG

    strong = [s for s in available if s["is_strong"]]
    rest = [s for s in available if not s["is_strong"]] + unavailable
    notable_count = sum(
        1
        for s in available
        if s.get("quality_score") is not None
        and s["quality_score"] >= STRONG_SETUP_SCORE_THRESHOLD
    )

    return {
        "user_id": user.id,
        "email": user.email,
        "date": date.today(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_watchlist": total,
        "analyzed_attempted": len(selected),
        "available_count": len(available),
        "notable_count": notable_count,
        "truncated": truncated,
        "truncation_note": (f"showing {len(selected)} of {total}" if truncated else None),
        "strong": strong,
        "rest": rest,
        "stocks": available + unavailable,
        "llm_calls": llm_calls,
        "cache_hits": cache_hits,
        "failures": failures,
    }


# ----------------------------------------------------------------------------
# Email rendering
# ----------------------------------------------------------------------------
def _digest_date(digest: dict[str, Any]) -> date:
    value = digest.get("date")
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            pass
    return date.today()


def digest_subject(digest: dict[str, Any]) -> str:
    """e.g. 'Your Watchlist Digest — Mon Jan 5'."""
    day = _digest_date(digest)
    return f"Your Watchlist Digest — {day:%a %b} {day.day}"


def digest_preheader(digest: dict[str, Any]) -> str:
    """Hidden inbox-preview line, e.g. '8 analyzed · 3 notable setups'."""
    analyzed = digest.get("available_count", 0)
    notable = digest.get("notable_count", 0)
    return f"{analyzed} analyzed · {notable} notable setup{'s' if notable != 1 else ''}"


def _levels_line(stock: dict[str, Any]) -> Optional[str]:
    bits: list[str] = []
    if stock.get("entry_zone"):
        bits.append(f"Entry {stock['entry_zone']}")
    if stock.get("invalidation_level"):
        bits.append(f"Invalidation {stock['invalidation_level']}")
    if stock.get("target_1"):
        bits.append(f"T1 {stock['target_1']}")
    return " · ".join(bits) if bits else None


def _render_stock_card(stock: dict[str, Any]) -> str:
    if not stock.get("available"):
        return tpl.ticker_card(
            stock["ticker"], stock["name"], [stock.get("reason", "Analysis unavailable today.")]
        )

    lines: list[str] = []

    score = stock.get("quality_score")
    score_text = f"Quality {round(score)}/100" if score is not None else "Quality n/a"
    lines.append(f"{_pretty_bias(stock.get('swing_bias'))} · {stock.get('setup_type')} · {score_text}")

    levels = _levels_line(stock)
    if levels:
        lines.append(levels)

    if stock.get("thesis"):
        lines.append(stock["thesis"])

    if stock.get("changed_since_yesterday") and stock.get("delta_line"):
        lines.append(f"Since yesterday: {stock['delta_line']}")

    return tpl.ticker_card(stock["ticker"], stock["name"], lines)


def render_digest_html(digest: dict[str, Any]) -> str:
    """Render the digest BODY html (composed from block helpers).

    This is body content — ``send_categorized_email`` wraps it in the branded
    base template (header + unsubscribe footer). Use ``render_digest_document``
    for a standalone previewable page.
    """
    parts: list[str] = []

    analyzed = digest.get("available_count", 0)
    notable = digest.get("notable_count", 0)
    stock_word = "stock" if analyzed == 1 else "stocks"
    if notable == 0:
        intro = (
            f"We analyzed {analyzed} {stock_word} on your watchlist. "
            "No standout setups today — here is where each one stands."
        )
    else:
        notable_word = "shows" if notable == 1 else "show"
        intro = (
            f"We analyzed {analyzed} {stock_word} on your watchlist. "
            f"{notable} {notable_word} a notable setup right now."
        )
    parts.append(tpl.paragraph(intro))

    if digest.get("truncation_note"):
        parts.append(
            tpl.paragraph(
                f"Your watchlist has more names than we include per digest — "
                f"{digest['truncation_note']} (oldest additions first)."
            )
        )

    strong = digest.get("strong") or []
    rest = digest.get("rest") or []

    if strong:
        parts.append(tpl.heading("Strongest setups"))
        parts.extend(_render_stock_card(s) for s in strong)

    if rest:
        parts.append(tpl.heading("The rest of your list"))
        parts.extend(_render_stock_card(s) for s in rest)

    app_url = (settings.PUBLIC_APP_URL or "https://quantorsignal.com").rstrip("/")
    parts.append(tpl.cta_button("Open full reports", f"{app_url}/ai-analyzer"))

    return "".join(parts)


def render_digest_document(digest: dict[str, Any], unsubscribe_url: str = "#") -> str:
    """Render the full branded HTML page (for admin browser preview)."""
    body = render_digest_html(digest)
    return tpl.render_base(
        title=digest_subject(digest),
        preheader=digest_preheader(digest),
        body_html=body,
        unsubscribe_url=unsubscribe_url,
    )
