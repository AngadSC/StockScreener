from __future__ import annotations

from datetime import datetime, timezone
from html import unescape
import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
import yfinance as yf

from app.config import settings


MAX_ARTICLES = 10

EVENT_KEYWORDS = [
    ("guidance", ("guidance", "forecast", "outlook", "raises forecast", "cuts forecast")),
    ("earnings", ("earnings", "eps", "revenue", "sales", "profit", "quarter", "results")),
    ("analyst_rating", ("upgrade", "downgrade", "price target", "rating", "initiates", "analyst")),
    ("FDA", ("fda", "clinical", "trial", "approval", "approved", "rejected", "crl", "drug")),
    ("lawsuit", ("lawsuit", "sues", "sued", "class action", "settlement", "probe", "investigation")),
    ("merger", ("merger", "acquisition", "acquire", "buyout", "takeover", "deal")),
    ("macro", ("fed", "inflation", "rates", "yield", "tariff", "jobs report", "cpi", "macro")),
    ("insider", ("insider", "ceo buys", "ceo sells", "director buys", "director sells", "13d")),
    ("product", ("launch", "product", "partnership", "contract", "order", "shipment", "recall")),
]

POSITIVE_PHRASES = (
    "raises guidance",
    "raises forecast",
    "beats estimates",
    "beats expectations",
    "tops estimates",
    "upgrade",
    "upgraded",
    "price target raised",
    "approved",
    "approval",
    "wins contract",
    "buyout",
    "acquisition offer",
    "record revenue",
    "profit growth",
    "revenue growth",
)
NEGATIVE_PHRASES = (
    "cuts guidance",
    "cuts forecast",
    "misses estimates",
    "misses expectations",
    "downgrade",
    "downgraded",
    "price target cut",
    "warning",
    "lawsuit",
    "class action",
    "probe",
    "investigation",
    "rejected",
    "complete response letter",
    "recall",
    "bankruptcy",
    "dilution",
)


def _clean_text(value: Any) -> str:
    return " ".join(unescape(str(value or "")).strip().split())


def _normalize_title(title: str) -> str:
    normalized = _clean_text(title).lower()
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    return " ".join(normalized.split())


def _normalize_url(url: str) -> str:
    cleaned = _clean_text(url)
    if not cleaned:
        return ""

    try:
        parsed = urlsplit(cleaned)
    except ValueError:
        return cleaned

    query_params = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in {"fbclid", "gclid"}
    ]
    path = parsed.path.rstrip("/") or parsed.path
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            urlencode(query_params, doseq=True),
            "",
        )
    )


def _event_type(title: str, summary: str) -> str:
    text = f"{title} {summary}".lower()
    for event_type, keywords in EVENT_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return event_type
    return "unknown"


def _sentiment(event_type: str, title: str | None, summary: str | None) -> str:
    text = f"{title or ''} {summary or ''}".lower()
    if any(phrase in text for phrase in POSITIVE_PHRASES):
        return "positive"
    if any(phrase in text for phrase in NEGATIVE_PHRASES):
        return "negative"
    if event_type == "lawsuit":
        return "negative"
    if event_type == "analyst_rating" and "outperform" in text:
        return "positive"
    if event_type == "product" and any(word in text for word in ("recall", "delays", "halts")):
        return "negative"
    return "neutral"


def _materiality(event_type: str, sentiment: str, title: str, summary: str) -> str:
    text = f"{title} {summary}".lower()
    if event_type in {"guidance", "FDA", "merger"}:
        return "high"
    if event_type == "lawsuit":
        return "high" if sentiment == "negative" else "medium"
    if event_type == "earnings":
        return "high" if sentiment in {"positive", "negative"} else "medium"
    if event_type == "macro":
        return "high" if any(word in text for word in ("fed", "inflation", "cpi", "rates")) else "medium"
    if event_type == "analyst_rating":
        return "medium"
    if event_type == "product":
        return "medium" if sentiment != "neutral" else "low"
    if event_type == "insider":
        return "medium" if any(word in text for word in ("ceo", "cfo", "director", "10%")) else "low"
    return "low"


def _time_horizon(event_type: str, materiality: str) -> str:
    if event_type in {"earnings", "guidance", "analyst_rating", "FDA", "lawsuit", "merger", "macro"}:
        return "immediate"
    if event_type in {"product", "insider"}:
        return "medium_term" if materiality != "high" else "immediate"
    return "medium_term"


def _why_it_matters(event_type: str, sentiment: str, materiality: str) -> str:
    if event_type == "guidance":
        return f"{materiality.capitalize()}-materiality guidance news can reset forward expectations."
    if event_type == "earnings":
        return f"{materiality.capitalize()}-materiality earnings news can change near-term estimate and momentum assumptions."
    if event_type == "analyst_rating":
        return "Analyst rating changes can affect near-term flows but need confirmation from price and volume."
    if event_type == "FDA":
        return f"{materiality.capitalize()}-materiality FDA news can materially change biotech or healthcare risk/reward."
    if event_type == "lawsuit":
        return "Legal news can add headline risk and pressure valuation until the liability is clearer."
    if event_type == "merger":
        return "Merger or acquisition news can reprice the stock quickly and distort normal technical signals."
    if event_type == "macro":
        return "Macro news can move sector multiples and broad market risk appetite."
    if event_type == "insider":
        return "Insider activity is a secondary signal that needs confirmation from fundamentals and price action."
    if event_type == "product":
        return "Product or contract news can support demand expectations, but market reaction matters."
    if sentiment != "neutral":
        return f"{materiality.capitalize()}-materiality headline may affect sentiment, but event details are limited."
    return "No clearly material company-specific catalyst was detected in the headline."


def _classify_article(title: str, summary: str) -> dict[str, str]:
    event_type = _event_type(title, summary)
    sentiment = _sentiment(event_type, title, summary)
    materiality = _materiality(event_type, sentiment, title, summary)
    return {
        "event_type": event_type,
        "sentiment": sentiment,
        "materiality": materiality,
        "time_horizon": _time_horizon(event_type, materiality),
        "why_it_matters": _why_it_matters(event_type, sentiment, materiality),
    }


def _normalize_article(
    *,
    title: str,
    source: Any,
    published_at: Any,
    url: Any,
    summary: str,
    classification: dict[str, str] | None = None,
) -> dict[str, Any]:
    classified = classification or _classify_article(title, summary)

    return {
        "headline": title,
        "title": title,
        "source": _clean_text(source),
        "published_at": _clean_text(published_at),
        "url": _normalize_url(url or ""),
        "event_type": classified["event_type"],
        "sentiment": classified["sentiment"],
        "materiality": classified["materiality"],
        "time_horizon": classified["time_horizon"],
        "summary": summary,
        "why_it_matters": classified["why_it_matters"],
    }


def _clean_article(article: dict[str, Any]) -> dict[str, Any]:
    title = _clean_text(article.get("title"))
    summary = _clean_text(article.get("description") or article.get("summary"))
    source = article.get("source")
    if isinstance(source, dict):
        source = source.get("name")

    return _normalize_article(
        title=title,
        source=source,
        published_at=article.get("publishedAt") or article.get("published_at"),
        url=article.get("url") or "",
        summary=summary,
    )


def _get_newsapi_articles(ticker: str) -> list[dict[str, Any]]:
    if not settings.news_api_key:
        return []

    params = {
        "q": ticker,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 10,
        "apiKey": settings.news_api_key,
    }
    try:
        response = httpx.get("https://newsapi.org/v2/everything", params=params, timeout=10.0)
        response.raise_for_status()
        data = response.json()
    except Exception:
        return []

    articles = data.get("articles") or []
    return [_clean_article(article) for article in articles[:MAX_ARTICLES]]


def _extract_yfinance_content(item: dict[str, Any]) -> dict[str, Any]:
    content = item.get("content") if isinstance(item.get("content"), dict) else item
    provider = content.get("provider") if isinstance(content.get("provider"), dict) else {}
    canonical_url = content.get("canonicalUrl") if isinstance(content.get("canonicalUrl"), dict) else {}
    click_url = content.get("clickThroughUrl") if isinstance(content.get("clickThroughUrl"), dict) else {}
    published = content.get("pubDate") or content.get("displayTime")

    if not published and item.get("providerPublishTime"):
        published = (
            datetime.fromtimestamp(item["providerPublishTime"], timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )

    summary = _clean_text(content.get("summary") or item.get("summary"))
    title = _clean_text(content.get("title") or item.get("title"))
    return _normalize_article(
        title=title,
        source=provider.get("displayName") or item.get("publisher"),
        published_at=published,
        url=canonical_url.get("url") or click_url.get("url") or item.get("link") or "",
        summary=summary,
    )


def _get_yfinance_articles(ticker: str) -> list[dict[str, Any]]:
    try:
        news_items = yf.Ticker(ticker).news or []
    except Exception:
        return []
    return [_extract_yfinance_content(item) for item in news_items[:MAX_ARTICLES]]


def _parse_published_at(value: str) -> datetime | None:
    cleaned = _clean_text(value)
    if not cleaned:
        return None
    try:
        return datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
    except ValueError:
        return None


def _latest_article_date(articles: list[dict[str, Any]]) -> str | None:
    dated_articles = [
        (published_at, article.get("published_at") or "")
        for article in articles
        if (published_at := _parse_published_at(article.get("published_at") or ""))
    ]
    if dated_articles:
        return max(dated_articles, key=lambda item: item[0])[1]
    return next((article.get("published_at") for article in articles if article.get("published_at")), None)


def _dedupe_articles(articles: list[dict[str, Any]], warnings: list[str]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    dropped_duplicates = 0
    dropped_unusable = 0

    for article in articles:
        title = _clean_text(article.get("headline") or article.get("title"))
        url = _normalize_url(article.get("url") or "")
        title_key = _normalize_title(title)

        if not title and not url:
            dropped_unusable += 1
            continue
        if url and url in seen_urls:
            dropped_duplicates += 1
            continue
        if title_key and title_key in seen_titles:
            dropped_duplicates += 1
            continue

        if url:
            seen_urls.add(url)
        if title_key:
            seen_titles.add(title_key)
        summary = _clean_text(article.get("summary"))
        classification = _classify_article(title, summary)
        if article.get("event_type") in {
            "earnings",
            "guidance",
            "analyst_rating",
            "FDA",
            "lawsuit",
            "merger",
            "macro",
            "insider",
            "product",
            "unknown",
        }:
            classification["event_type"] = str(article["event_type"])
        if article.get("sentiment") in {"positive", "negative", "neutral"}:
            classification["sentiment"] = str(article["sentiment"])
        if article.get("materiality") in {"low", "medium", "high"}:
            classification["materiality"] = str(article["materiality"])
        if article.get("time_horizon") in {"immediate", "medium_term", "long_term"}:
            classification["time_horizon"] = str(article["time_horizon"])
        classification["why_it_matters"] = _clean_text(
            article.get("why_it_matters") or classification["why_it_matters"]
        )

        cleaned.append(
            _normalize_article(
                title=title,
                source=article.get("source"),
                published_at=article.get("published_at"),
                url=url,
                summary=summary,
                classification=classification,
            )
        )
        if len(cleaned) >= MAX_ARTICLES:
            break

    if dropped_duplicates:
        warnings.append(f"Dropped {dropped_duplicates} duplicate news article(s).")
    if dropped_unusable:
        warnings.append(f"Dropped {dropped_unusable} unusable news article(s).")

    return cleaned[:MAX_ARTICLES]


def _news_payload(
    *,
    provider_used: str,
    articles: list[dict[str, Any]],
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "provider_used": provider_used,
        "article_count": len(articles),
        "articles": articles,
        "data_quality": {
            "available": bool(articles),
            "latest_article_date": _latest_article_date(articles),
            "warnings": warnings,
        },
    }


def get_recent_stock_news(ticker: str) -> dict[str, Any]:
    ticker = ticker.strip().upper()
    warnings: list[str] = []

    if settings.news_api_key:
        newsapi_articles = _dedupe_articles(_get_newsapi_articles(ticker), warnings)
        if newsapi_articles:
            return _news_payload(provider_used="newsapi", articles=newsapi_articles, warnings=warnings)
        warnings.append("NewsAPI returned no usable articles; used yfinance fallback.")
    else:
        warnings.append("NewsAPI is not configured; used yfinance fallback.")

    yfinance_articles = _dedupe_articles(_get_yfinance_articles(ticker), warnings)
    if yfinance_articles:
        return _news_payload(provider_used="yfinance", articles=yfinance_articles, warnings=warnings)

    warnings.append("yfinance returned no usable articles.")
    return _news_payload(provider_used="none", articles=[], warnings=warnings)
