"""
Unit tests for _attach_deterministic_report_fields in app.ai.llm_client.

Verifies:
1. trade_card.trade_levels is overwritten with deterministic values when the LLM
   produces a trade card.
2. A None trade_card stays None even when deterministic trade_levels exist.
3. A missing trade_levels key in deterministic_scores leaves the trade_card unchanged.
4. Existing _score field overwrite behaviour is preserved alongside trade_card changes.

No DB, network, or external fixtures are required — all inputs are synthetic dicts.
"""
from __future__ import annotations

import pytest

from app.ai.llm_client import _attach_deterministic_report_fields


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_trade_card(trade_levels: dict | None = None) -> dict:
    """Return a minimal dict that looks like an LLM-produced trade card."""
    return {
        "decision": "Long Setup Active",
        "ai_lean": "bullish",
        "best_action_now": "buy_now",
        "verdict": "Strong bullish setup.",
        "setup_type": "Breakout",
        "confidence_label": "moderate",
        "setup_score": 72.0,
        "trade_levels": trade_levels if trade_levels is not None else {
            "current_price": 999.0,
            "preferred_entry": 888.0,
            "target_1": 1111.0,
            "invalidation_level": 777.0,
        },
        "main_reason": "Price is breaking out.",
        "main_risk": "Market reversal.",
        "bull_case": ["Strong momentum"],
        "bear_case": ["Overbought RSI"],
        "if_then_plan": {
            "if_trigger_hits": "Add",
            "if_rejects": "Exit",
            "if_breaks_invalidation": "Stop out",
            "if_already_holding": "Hold",
            "if_missed_entry": "Wait for pullback",
        },
    }


def _deterministic_trade_levels() -> dict:
    """Return a representative deterministic trade levels dict."""
    return {
        "current_price": 150.25,
        "preferred_entry": 148.50,
        "aggressive_entry_min": 147.00,
        "aggressive_entry_max": 149.00,
        "confirmation_trigger": 152.00,
        "add_level": 151.00,
        "invalidation_level": 144.00,
        "target_1": 158.00,
        "target_2": 165.00,
        "chase_above": 153.00,
        "method": "atr_based",
        "warnings": [],
    }


def _payload_with_trade_levels(trade_levels: dict | None = None) -> dict:
    """Return a minimal payload dict with optional deterministic trade_levels."""
    deterministic_scores: dict = {}
    if trade_levels is not None:
        deterministic_scores["trade_levels"] = trade_levels
    return {"deterministic_scores": deterministic_scores}


# ---------------------------------------------------------------------------
# Test 1 — trade_card.trade_levels is overwritten with deterministic values
# ---------------------------------------------------------------------------

def test_attach_overwrites_trade_card_trade_levels() -> None:
    """LLM-invented prices in trade_card.trade_levels must be replaced with
    the backend-computed deterministic levels."""
    det_levels = _deterministic_trade_levels()
    llm_trade_card = _minimal_trade_card(
        trade_levels={
            "current_price": 999.0,
            "preferred_entry": 888.0,
            "target_1": 1111.0,
            "invalidation_level": 777.0,
        }
    )
    candidate = {
        "technical_score": 55.0,
        "trade_card": llm_trade_card,
    }
    payload = _payload_with_trade_levels(det_levels)

    result = _attach_deterministic_report_fields(candidate, payload)

    assert result["trade_card"] is not None
    result_levels = result["trade_card"]["trade_levels"]
    assert result_levels == det_levels, (
        f"Expected deterministic levels {det_levels!r}, got {result_levels!r}"
    )
    # Sanity check that LLM-invented values were not kept
    assert result_levels["current_price"] == 150.25
    assert result_levels["preferred_entry"] == 148.50
    assert result_levels["target_1"] == 158.00


def test_attach_overwrites_trade_levels_preserves_other_trade_card_fields() -> None:
    """Overwriting trade_levels must not disturb other fields in the trade card."""
    det_levels = _deterministic_trade_levels()
    llm_trade_card = _minimal_trade_card()
    candidate = {"trade_card": llm_trade_card}
    payload = _payload_with_trade_levels(det_levels)

    result = _attach_deterministic_report_fields(candidate, payload)

    tc = result["trade_card"]
    assert tc["decision"] == "Long Setup Active"
    assert tc["ai_lean"] == "bullish"
    assert tc["verdict"] == "Strong bullish setup."
    assert tc["confidence_label"] == "moderate"
    assert tc["setup_score"] == 72.0


# ---------------------------------------------------------------------------
# Test 2 — trade_card=None stays None even when deterministic levels exist
# ---------------------------------------------------------------------------

def test_attach_trade_card_none_stays_none() -> None:
    """When the LLM omits the trade card (None), deterministic trade_levels must
    not inject a synthetic trade card."""
    det_levels = _deterministic_trade_levels()
    candidate: dict = {"technical_score": 60.0, "trade_card": None}
    payload = _payload_with_trade_levels(det_levels)

    result = _attach_deterministic_report_fields(candidate, payload)

    assert result["trade_card"] is None


def test_attach_trade_card_missing_key_stays_absent() -> None:
    """When the trade_card key is not present in the candidate at all, the
    function must not add it."""
    det_levels = _deterministic_trade_levels()
    candidate: dict = {"technical_score": 60.0}
    payload = _payload_with_trade_levels(det_levels)

    result = _attach_deterministic_report_fields(candidate, payload)

    assert "trade_card" not in result


# ---------------------------------------------------------------------------
# Test 3 — missing trade_levels leaves trade_card unchanged
# ---------------------------------------------------------------------------

def test_attach_missing_trade_levels_leaves_trade_card_unchanged() -> None:
    """When deterministic_scores has no trade_levels key, the trade_card produced
    by the LLM (including its invented prices) must be left exactly as-is."""
    llm_trade_card = _minimal_trade_card(
        trade_levels={"current_price": 999.0, "target_1": 1111.0}
    )
    candidate = {"trade_card": llm_trade_card}
    payload: dict = {"deterministic_scores": {}}  # no trade_levels key

    result = _attach_deterministic_report_fields(candidate, payload)

    assert result["trade_card"]["trade_levels"]["current_price"] == 999.0
    assert result["trade_card"]["trade_levels"]["target_1"] == 1111.0


def test_attach_no_deterministic_scores_leaves_trade_card_unchanged() -> None:
    """When the payload has no deterministic_scores at all, the trade_card must
    be left untouched."""
    llm_trade_card = _minimal_trade_card(
        trade_levels={"current_price": 42.0}
    )
    candidate = {"trade_card": llm_trade_card}
    payload: dict = {}  # deterministic_scores key absent entirely

    result = _attach_deterministic_report_fields(candidate, payload)

    assert result["trade_card"]["trade_levels"]["current_price"] == 42.0


# ---------------------------------------------------------------------------
# Test 4 — existing _score field overwrite still works alongside trade_card changes
# ---------------------------------------------------------------------------

def test_attach_scores_still_overwritten() -> None:
    """Deterministic _score overwriting must continue to work correctly even
    when trade_card processing is also triggered."""
    det_levels = _deterministic_trade_levels()
    deterministic_scores = {
        "technical_score": 88.0,
        "momentum_score": 77.0,
        "trade_levels": det_levels,
    }
    llm_trade_card = _minimal_trade_card()
    candidate = {
        "technical_score": 10.0,   # LLM value — should be overwritten
        "momentum_score": 20.0,    # LLM value — should be overwritten
        "news_score": 55.0,        # no deterministic override — should stay
        "trade_card": llm_trade_card,
    }
    payload = {"deterministic_scores": deterministic_scores}

    result = _attach_deterministic_report_fields(candidate, payload)

    # Scores overwritten
    assert result["technical_score"] == 88.0
    assert result["momentum_score"] == 77.0
    # Score without override stays unchanged
    assert result["news_score"] == 55.0
    # Trade levels also overwritten
    assert result["trade_card"]["trade_levels"] == det_levels


def test_attach_scores_overwritten_when_trade_card_none() -> None:
    """_score overwrite must work correctly even when trade_card is None."""
    deterministic_scores = {
        "risk_score": 33.0,
        "trade_levels": _deterministic_trade_levels(),
    }
    candidate = {
        "risk_score": 99.0,
        "trade_card": None,
    }
    payload = {"deterministic_scores": deterministic_scores}

    result = _attach_deterministic_report_fields(candidate, payload)

    assert result["risk_score"] == 33.0
    assert result["trade_card"] is None


# ---------------------------------------------------------------------------
# Test 5 — input candidate is not mutated (function returns a copy)
# ---------------------------------------------------------------------------

def test_attach_does_not_mutate_original_candidate() -> None:
    """_attach_deterministic_report_fields must not modify the original candidate
    dict — it should return a new dict."""
    det_levels = _deterministic_trade_levels()
    llm_trade_card = _minimal_trade_card()
    original_levels = dict(llm_trade_card["trade_levels"])
    candidate = {"trade_card": llm_trade_card}
    payload = _payload_with_trade_levels(det_levels)

    _attach_deterministic_report_fields(candidate, payload)

    # Original candidate trade_card trade_levels must be unchanged
    assert candidate["trade_card"]["trade_levels"] == original_levels
