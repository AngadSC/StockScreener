from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx
import yfinance as yf

from app.config import settings


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
    title = article.get("title") or ""
    summary = article.get("description") or article.get("summary") or ""
    source = article.get("source")
    if isinstance(source, dict):
        source = source.get("name")

    return {
        "title": title,
        "source": source or "",
        "published_at": article.get("publishedAt") or article.get("published_at") or "",
        "url": article.get("url") or "",
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
    return [_clean_article(article) for article in articles[:10]]


def _extract_yfinance_content(item: dict[str, Any]) -> dict[str, Any]:
    content = item.get("content") if isinstance(item.get("content"), dict) else item
    provider = content.get("provider") if isinstance(content.get("provider"), dict) else {}
    canonical_url = content.get("canonicalUrl") if isinstance(content.get("canonicalUrl"), dict) else {}
    click_url = content.get("clickThroughUrl") if isinstance(content.get("clickThroughUrl"), dict) else {}
    published = content.get("pubDate") or content.get("displayTime")

    if not published and item.get("providerPublishTime"):
        published = datetime.utcfromtimestamp(item["providerPublishTime"]).isoformat()

    summary = content.get("summary") or item.get("summary") or ""
    title = content.get("title") or item.get("title") or ""
    return {
        "title": title,
        "source": provider.get("displayName") or item.get("publisher") or "",
        "published_at": published or "",
        "url": canonical_url.get("url") or click_url.get("url") or item.get("link") or "",
        "summary": summary,
        "sentiment": _sentiment(title, summary),
    }


def _get_yfinance_articles(ticker: str) -> list[dict[str, Any]]:
    try:
        news_items = yf.Ticker(ticker).news or []
    except Exception:
        return []
    return [_extract_yfinance_content(item) for item in news_items[:10]]


def get_recent_stock_news(ticker: str) -> list[dict]:
    ticker = ticker.strip().upper()
    articles = _get_newsapi_articles(ticker) or _get_yfinance_articles(ticker)

    cleaned: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for article in articles:
        url = article.get("url") or ""
        if url and url in seen_urls:
            continue
        seen_urls.add(url)
        cleaned.append(
            {
                "title": article.get("title") or "",
                "source": article.get("source") or "",
                "published_at": article.get("published_at") or "",
                "url": url,
                "summary": article.get("summary") or "",
                "sentiment": article.get("sentiment") or "neutral",
            }
        )
        if len(cleaned) >= 10:
            break

    return cleaned[:10]
