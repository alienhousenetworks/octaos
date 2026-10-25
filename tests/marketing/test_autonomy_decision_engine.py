"""Unit tests for deterministic Marketing AI autonomy decisions."""
from datetime import datetime, timezone

from app.services.marketing.autonomy.decision_engine import (
    compute_schedule_time,
    rank_context_signals,
    score_context_signal,
)


def test_news_with_fresh_relevant_evidence_outranks_unrelated_calendar_event():
    now = datetime(2026, 10, 25, 12, tzinfo=timezone.utc)
    calendar = [{
        "name": "Generic annual observance",
        "days_away": 10,
        "relevance_score": 0.1,
        "confidence": 0.7,
        "url": "https://example.com/calendar",
    }]
    news = [{
        "topic": "Enterprise security regulation update",
        "signal": "Regulator published new guidance for enterprise software vendors",
        "published_at": "2026-10-25T10:00:00Z",
        "relevance_score": 0.95,
        "confidence": 0.95,
        "velocity_score": 0.8,
        "persistence_score": 0.8,
        "risk_score": 0.05,
        "url": "https://example.com/regulatory-update",
    }]

    ranked = rank_context_signals(
        calendar, news, now=now, industry="enterprise software"
    )

    assert ranked[0]["kind"] == "news"
    assert ranked[0]["source_url"] == "https://example.com/regulatory-update"
    assert ranked[0]["score"] > ranked[1]["score"]


def test_undated_news_is_not_treated_as_fresh():
    score = score_context_signal(
        {"topic": "Possibly trending topic", "relevance_score": 0.9, "confidence": 0.9},
        kind="news",
        now=datetime(2026, 10, 25, tzinfo=timezone.utc),
    )
    assert score < 0.7


def test_schedule_respects_account_timezone_and_returns_utc():
    now = datetime(2026, 10, 25, 0, tzinfo=timezone.utc)
    scheduled = compute_schedule_time(
        "instagram",
        timezone_name="Asia/Kolkata",
        now=now,
        preferred_hours={"instagram": 19},
    )

    assert scheduled.tzinfo == timezone.utc
    assert scheduled.hour == 13  # 19:00 IST = 13:30 UTC; scheduler uses top of hour.
    assert scheduled.minute == 30 or scheduled.minute == 0


def test_invalid_timezone_falls_back_to_utc():
    now = datetime(2026, 10, 25, 0, tzinfo=timezone.utc)
    scheduled = compute_schedule_time("linkedin", timezone_name="Not/AZone", now=now)
    assert scheduled.tzinfo == timezone.utc
    assert scheduled.hour == 9
