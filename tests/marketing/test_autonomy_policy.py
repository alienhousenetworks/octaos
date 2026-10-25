"""Tests for marketing autonomy policy and virtual influencer guardrails."""
import pytest

from app.services.marketing.autonomy.policy import evaluate_marketing_action
from app.services.marketing.virtual_influencer import validate_virtual_influencer_brief


def test_fallback_generation_never_auto_approves():
    decision = evaluate_marketing_action(
        confidence=0.99,
        generation_status="fallback_requires_review",
    )
    assert decision["approved"] is False
    assert "generation_status_fallback_requires_review_requires_review" in decision["reasons"]


def test_news_without_source_requires_review():
    decision = evaluate_marketing_action(
        confidence=0.99,
        context_trigger="news",
        context_score=0.9,
        source_url=None,
    )
    assert decision["decision"] == "needs_review"
    assert "news_context_has_no_source_url" in decision["reasons"]


def test_required_but_missing_media_requires_review():
    decision = evaluate_marketing_action(
        confidence=0.99,
        media_required=True,
        media_generated=False,
    )
    assert not decision["approved"]
    assert "required_media_not_generated" in decision["reasons"]



def test_unavailable_publisher_adapter_cannot_auto_schedule():
    decision = evaluate_marketing_action(
        confidence=1.0,
        publisher_supported=False,
    )
    assert decision["approved"] is False
    assert "publisher_adapter_unavailable" in decision["reasons"]

def test_tenant_approval_policy_overrides_confidence():
    decision = evaluate_marketing_action(confidence=1.0, require_approval=True)
    assert not decision["approved"]


def test_virtual_influencer_brief_requires_minimum_fields_and_disclosure():
    data = validate_virtual_influencer_brief({
        "name": "Mira",
        "persona": "An original fictional adult character.",
        "audience": "Design teams",
        "voice": "Curious and clear",
        "visual_prompt": "Original fictional adult character, no real-person resemblance.",
        "intro_caption": "Meet Mira, our AI-generated virtual persona.",
        "content_pillars": ["Design education"],
    })
    assert data["approval_required"] is True
    assert "AI-generated" in data["disclosure"]
    assert data["status"] == "draft_requires_review"


def test_invalid_virtual_influencer_brief_is_rejected():
    with pytest.raises(ValueError):
        validate_virtual_influencer_brief({"name": "Mira"})
