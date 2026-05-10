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

POSITIVE_WORDS = {
    "beat",
    "beats",
    "bullish",
    "gain",
    "gains",
    "growth",
    "higher",
    "outperform",
    "profit",
    "rally",
    "record",
    "upgrade",
    "upside",
}
NEGATIVE_WORDS = {
    "bearish",
    "cut",
    "decline",
    "downgrade",
    "fall",
    "falls",
    "loss",
    "miss",
    "probe",
    "risk",
    "selloff",
    "slump",
    "warning",
    "weak",
}


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


def _sentiment(title: str | None, summary: str | None) -> str:
    text = f"{title or ''} {summary or ''}".lower()
    positive = sum(1 for word in POSITIVE_WORDS if word in text)
    negative = sum(1 for word in NEGATIVE_WORDS if word in text)
    if positive > negative:
        return "positive"
    if negative > positive:
        return "negative"
    return "neutral"


def _clean_article(article: dict[str, Any]) -> dict[str, Any]:
    title = _clean_text(article.get("title"))
    summary = _clean_text(article.get("description") or article.get("summary"))
    source = article.get("source")
    if isinstance(source, dict):
        source = source.get("name")

    return {
        "title": title,
        "source": _clean_text(source),
        "published_at": _clean_text(article.get("publishedAt") or article.get("published_at")),
        "url": _normalize_url(article.get("url") or ""),
        "summary": summary,
        "sentiment": _sentiment(title, summary),
    }


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
    return {
        "title": title,
        "source": _clean_text(provider.get("displayName") or item.get("publisher")),
        "published_at": _clean_text(published),
        "url": _normalize_url(
            canonical_url.get("url") or click_url.get("url") or item.get("link") or ""
        ),
        "summary": summary,
        "sentiment": _sentiment(title, summary),
    }


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
        title = _clean_text(article.get("title"))
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
        cleaned.append(
            {
                "title": title,
                "source": _clean_text(article.get("source")),
                "published_at": _clean_text(article.get("published_at")),
                "url": url,
                "summary": _clean_text(article.get("summary")),
                "sentiment": (
                    article.get("sentiment")
                    if article.get("sentiment") in {"positive", "negative", "neutral"}
                    else "neutral"
                ),
            }
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
