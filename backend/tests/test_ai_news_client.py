from __future__ import annotations

from typing import Any

from app.ai import news_client


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self.payload


def test_newsapi_data_cleaning(monkeypatch) -> None:
    monkeypatch.setattr(news_client.settings, "news_api_key", "test-key")

    def fake_get(*_args: Any, **_kwargs: Any) -> _FakeResponse:
        return _FakeResponse(
            {
                "articles": [
                    {
                        "title": "  Apple&nbsp;beats estimates  ",
                        "source": {"name": " Example   News "},
                        "publishedAt": "2026-05-08T13:00:00Z",
                        "url": "HTTPS://EXAMPLE.COM/aapl/?utm_source=newsletter&ref=home#section",
                        "description": "  Profit   growth continues. ",
                    }
                ]
            }
        )

    monkeypatch.setattr(news_client.httpx, "get", fake_get)

    articles = news_client._get_newsapi_articles("AAPL")

    assert articles == [
        {
            "headline": "Apple beats estimates",
            "title": "Apple beats estimates",
            "source": "Example News",
            "published_at": "2026-05-08T13:00:00Z",
            "url": "https://example.com/aapl?ref=home",
            "event_type": "earnings",
            "sentiment": "positive",
            "materiality": "high",
            "time_horizon": "immediate",
            "summary": "Profit growth continues.",
            "why_it_matters": "High-materiality earnings news can change near-term estimate and momentum assumptions.",
        }
    ]


def test_yfinance_news_cleaning() -> None:
    article = news_client._extract_yfinance_content(
        {
            "content": {
                "title": " Apple faces warning ",
                "summary": " Shares fall on risk. ",
                "provider": {"displayName": " Yahoo Finance "},
                "canonicalUrl": {
                    "url": "https://finance.yahoo.com/news/apple-warning/?utm_medium=social",
                },
            },
            "providerPublishTime": 1_778_240_400,
        }
    )

    assert article == {
        "headline": "Apple faces warning",
        "title": "Apple faces warning",
        "source": "Yahoo Finance",
        "published_at": "2026-05-08T11:40:00Z",
        "url": "https://finance.yahoo.com/news/apple-warning",
        "event_type": "unknown",
        "sentiment": "negative",
        "materiality": "low",
        "time_horizon": "medium_term",
        "summary": "Shares fall on risk.",
        "why_it_matters": "Low-materiality headline may affect sentiment, but event details are limited.",
    }


def test_get_recent_stock_news_dedupes_by_url_and_normalized_title(monkeypatch) -> None:
    monkeypatch.setattr(news_client.settings, "news_api_key", "test-key")
    monkeypatch.setattr(
        news_client,
        "_get_newsapi_articles",
        lambda _ticker: [
            {
                "title": "Apple shares rally",
                "source": "One",
                "published_at": "2026-05-08T13:00:00Z",
                "url": "https://example.com/aapl?utm_source=x",
                "summary": "Shares gain.",
                "sentiment": "positive",
            },
            {
                "title": "Different headline",
                "source": "Two",
                "published_at": "2026-05-08T14:00:00Z",
                "url": "https://example.com/aapl",
                "summary": "Duplicate URL.",
                "sentiment": "neutral",
            },
            {
                "title": "Apple Shares Rally!",
                "source": "Three",
                "published_at": "2026-05-08T15:00:00Z",
                "url": "https://example.com/aapl-2",
                "summary": "Duplicate title.",
                "sentiment": "positive",
            },
        ],
    )

    payload = news_client.get_recent_stock_news("aapl")

    assert payload["provider_used"] == "newsapi"
    assert payload["article_count"] == 1
    assert payload["articles"][0]["title"] == "Apple shares rally"
    assert payload["articles"][0]["event_type"] == "unknown"
    assert payload["articles"][0]["materiality"] == "low"
    assert payload["data_quality"]["available"] is True
    assert payload["data_quality"]["latest_article_date"] == "2026-05-08T13:00:00Z"
    assert "Dropped 2 duplicate news article(s)." in payload["data_quality"]["warnings"]


def test_get_recent_stock_news_reports_provider_fallback_metadata(monkeypatch) -> None:
    monkeypatch.setattr(news_client.settings, "news_api_key", "test-key")
    monkeypatch.setattr(news_client, "_get_newsapi_articles", lambda _ticker: [])
    monkeypatch.setattr(
        news_client,
        "_get_yfinance_articles",
        lambda _ticker: [
            {
                "title": "Apple gains on upgrade",
                "source": "Yahoo Finance",
                "published_at": "2026-05-07T19:00:00Z",
                "url": "https://finance.yahoo.com/news/aapl",
                "summary": "Analysts upgrade the stock.",
                "sentiment": "positive",
            }
        ],
    )

    payload = news_client.get_recent_stock_news("aapl")

    assert payload["provider_used"] == "yfinance"
    assert payload["article_count"] == 1
    assert payload["articles"][0]["event_type"] == "analyst_rating"
    assert payload["articles"][0]["materiality"] == "medium"
    assert payload["data_quality"] == {
        "available": True,
        "latest_article_date": "2026-05-07T19:00:00Z",
        "warnings": ["NewsAPI returned no usable articles; used yfinance fallback."],
    }


def test_get_recent_stock_news_reports_none_when_no_provider_has_articles(monkeypatch) -> None:
    monkeypatch.setattr(news_client.settings, "news_api_key", "")
    monkeypatch.setattr(news_client, "_get_yfinance_articles", lambda _ticker: [])

    payload = news_client.get_recent_stock_news("aapl")

    assert payload == {
        "provider_used": "none",
        "article_count": 0,
        "articles": [],
        "data_quality": {
            "available": False,
            "latest_article_date": None,
            "warnings": [
                "NewsAPI is not configured; used yfinance fallback.",
                "yfinance returned no usable articles.",
            ],
        },
    }
