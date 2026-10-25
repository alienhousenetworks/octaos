from app.services.marketing.virtual_influencer import validate_virtual_influencer_brief


def test_virtual_influencer_brief_requires_core_fields():
    try:
        validate_virtual_influencer_brief({"name": "Nova"})
    except ValueError as exc:
        assert "persona" in str(exc)
    else:
        raise AssertionError("incomplete persona brief must be rejected")


def test_virtual_influencer_brief_forces_disclosure_and_review():
    result = validate_virtual_influencer_brief({
        "name": "Nova",
        "persona": "A fictional adult outdoor enthusiast.",
        "audience": "Weekend hikers",
        "voice": "Practical and warm",
        "visual_prompt": "An original fictional adult character in a mountain setting.",
        "intro_caption": "Meet Nova, an AI-generated virtual persona.",
        "content_pillars": ["Trail preparation", "Outdoor safety"],
    })
    assert result["disclosure"] == "AI-generated virtual persona; not a real person or customer."
    assert result["approval_required"] is True
    assert result["status"] == "draft_requires_review"
    assert len(result["content_pillars"]) == 2
