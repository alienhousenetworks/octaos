"""Contract tests for the end-to-end AI influencer creative workflow."""
import pytest
from pydantic import ValidationError

from app.api.v1.endpoints.marketing import (
    InfluencerCreativeGenerateRequest,
    InfluencerCreativePlanRequest,
)


def test_creative_plan_accepts_supported_reel_brief_and_user_script():
    req = InfluencerCreativePlanRequest(
        company_name="Example Brand",
        industry="Consumer products",
        campaign_goal="Explain one product use case",
        format="reel",
        duration_seconds=30,
        script_input="Opening: show the everyday problem.",
        product_context="Use only the facts provided here.",
    )
    assert req.format == "reel"
    assert req.duration_seconds == 30
    assert "everyday problem" in req.script_input


def test_creative_plan_rejects_unsupported_format_and_duration():
    with pytest.raises(ValidationError):
        InfluencerCreativePlanRequest(
            company_name="Example Brand", industry="Retail", campaign_goal="Explain product",
            format="movie", duration_seconds=30,
        )
    with pytest.raises(ValidationError):
        InfluencerCreativePlanRequest(
            company_name="Example Brand", industry="Retail", campaign_goal="Explain product",
            duration_seconds=181,
        )


def test_creative_generation_is_limited_to_image_or_video_and_bounded_references():
    req = InfluencerCreativeGenerateRequest(
        prompt="A fictional adult presenter demonstrates the product in a bright studio.",
        deliverable="video",
        reference_assets=["https://assets.example/reference.png"],
    )
    assert req.deliverable == "video"
    assert len(req.reference_assets) == 1
    with pytest.raises(ValidationError):
        InfluencerCreativeGenerateRequest(prompt="short", deliverable="audio")
