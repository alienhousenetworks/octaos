"""Tests for Universal Visual Creative Director Skill & Runtime Orchestration."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.skill_synthesizer import ProgressiveSkillSynthesizer, skill_synthesizer
from app.services.marketing.visual_creative.contracts import (
    VisualIntentInputContract,
    CreativeBrief,
    QualityReviewScorecard,
    QualityCriteriaScore,
    VisualRunRecord,
)
from app.services.marketing.visual_creative.analyzer import VisualIntentAnalyzer
from app.services.marketing.visual_creative.creative_director import DynamicCreativeDirector
from app.services.marketing.visual_creative.model_router import VisualModelRouter
from app.services.marketing.visual_creative.critic import VisualCritic
from app.services.marketing.visual_creative.revision_controller import RevisionController
from app.services.marketing.visual_creative.validator import DeliveryValidator
from app.services.marketing.visual_creative.orchestrator import VisualCreativeOrchestrator


def test_skill_discovery_and_progressive_disclosure():
    """Verify built-in SKILL.md auto-discovery and 3-level progressive disclosure."""
    skills = skill_synthesizer.list_all_skills()
    assert "universal_visual_creative_director" in skills

    # Level 1 (~20 tokens: Name + summary)
    l1 = skill_synthesizer.get_skill_disclosure("universal_visual_creative_director", level=1)
    assert "universal-visual-creative-director" in l1
    assert "Turn any image or video request into a professionally art-directed" in l1

    # Level 2 (~200 tokens: Schema, input modes, triggers)
    l2 = skill_synthesizer.get_skill_disclosure("universal_visual_creative_director", level=2)
    assert "Input Modes:" in l2
    assert "Output Modes:" in l2
    assert "Triggers:" in l2

    # Level 3 (Full procedural execution body)
    l3 = skill_synthesizer.get_skill_disclosure("universal_visual_creative_director", level=3)
    assert "# Universal Visual Creative Director — OctaOS Skill" in l3
    assert "Phase 5 — Generate and inspect" in l3

    # Resolve registered skill on visual prompt trigger
    res = skill_synthesizer.resolve_registered_skill("Create a luxury perfume commercial video for Instagram")
    assert res["matched"] is True
    assert res["skill_id"] == "creative.universal_visual_director"


def test_visual_intent_analyzer_archetypes():
    """Verify intent analysis accurately classifies distinct visual archetypes."""
    # A. Luxury product
    luxury = VisualIntentAnalyzer.analyze("Create a luxury perfume bottle advertisement with golden reflections")
    assert any("luxury" in a.lower() for a in luxury.assumptions)
    assert luxury.deliverable == "image"
    assert "plastic over-smoothed skin" in luxury.must_avoid

    # B. Fine art painting
    fine_art = VisualIntentAnalyzer.analyze("Fine-art watercolor painting of an alpine lake at sunrise with visible brushwork")
    assert any("fine_art" in a.lower() for a in fine_art.assumptions)
    assert any("brushwork" in s.lower() for s in fine_art.style_direction)

    # C. Cinematic video
    cinematic = VisualIntentAnalyzer.analyze("Cinematic short film trailer of an astronaut exploring a neon cave", deliverable="video")
    assert cinematic.deliverable == "video"
    assert cinematic.duration_seconds == 5
    assert cinematic.aspect_ratio in ("16:9", "9:16")

    # D. Influencer / UGC
    ugc = VisualIntentAnalyzer.analyze("UGC creator selfie video demonstrating our SaaS analytics dashboard on TikTok", deliverable="video", platform="tiktok")
    assert ugc.aspect_ratio == "9:16"
    assert any("ugc" in s.lower() for s in ugc.style_direction)


def test_dynamic_creative_director_specialist_selection():
    """Verify dynamic creative director assembles correct specialists per domain."""
    # Luxury product brief
    luxury_intent = VisualIntentAnalyzer.analyze("Luxury watch commercial product photo with dark sapphire backdrop")
    luxury_team = DynamicCreativeDirector.assemble_specialists(luxury_intent)
    roles = [s.role_name for s in luxury_team]
    assert any("Photographer" in r for r in roles)
    assert any("Lighting" in r for r in roles)
    assert any("Retoucher" in r for r in roles)

    brief = DynamicCreativeDirector.create_brief(luxury_intent, specialists=luxury_team)
    assert brief.focal_subject != ""
    assert "lighting" in brief.lighting_setup.lower()
    assert len(brief.negative_constraints) > 0

    # Fine art brief
    art_intent = VisualIntentAnalyzer.analyze("Impressionist oil painting on canvas")
    art_team = DynamicCreativeDirector.assemble_specialists(art_intent)
    art_roles = [s.role_name for s in art_team]
    assert any("Artist" in r for r in art_roles)

    # Cinematic video brief
    video_intent = VisualIntentAnalyzer.analyze("Dramatic cinematic car commercial", deliverable="video")
    video_team = DynamicCreativeDirector.assemble_specialists(video_intent)
    video_roles = [s.role_name for s in video_team]
    assert any("Director" in r for r in video_roles)
    assert any("Cinematographer" in r or "DP" in r for r in video_roles)


def test_visual_model_router():
    """Verify model routing and target syntax compilation."""
    intent = VisualIntentAnalyzer.analyze("Editorial poster with bold headline typography reading Launch Today")
    brief = DynamicCreativeDirector.create_brief(intent)

    provider, model = VisualModelRouter.select_model(intent, brief)
    # Posters route to ideogram
    assert "ideogram" in model.lower()

    payload = VisualModelRouter.compile_payload(intent, brief, provider, model, headline_text="Launch Today")
    assert "prompt" in payload
    assert payload["aspect_ratio"] == intent.aspect_ratio


@pytest.mark.asyncio
async def test_visual_critic_and_scorecard():
    """Verify visual critic scores the 7 criteria and identifies blockers."""
    mock_db = MagicMock()
    critic = VisualCritic(mock_db, "test-tenant")

    intent = VisualIntentAnalyzer.analyze("Commercial photo of an executive laptop")
    brief = DynamicCreativeDirector.create_brief(intent)

    # 1. Inspection with valid asset
    scorecard = await critic.inspect(
        asset_url="https://cdn.octaos.ai/img/test_laptop.png",
        intent=intent,
        brief=brief,
    )
    assert scorecard.weighted_score >= 70.0
    assert scorecard.passed is True
    assert len(scorecard.criteria) == 7

    # 2. Inspection with generation failure
    failed_scorecard = await critic.inspect(
        asset_url=None,
        intent=intent,
        brief=brief,
        generation_error="API key missing",
    )
    assert failed_scorecard.passed is False
    assert failed_scorecard.weighted_score == 0.0
    assert len(failed_scorecard.critical_blockers) > 0


def test_revision_controller_bounded_retries():
    """Verify revision controller manages targeted defect repair within bounds."""
    # Failed scorecard
    failing_scorecard = QualityReviewScorecard(
        weighted_score=55.0,
        critical_blockers=["Broken anatomy in human hand"],
        passed=False,
    )

    intent = VisualIntentAnalyzer.analyze("Portrait of an engineer typing on keyboard")
    brief = DynamicCreativeDirector.create_brief(intent)
    initial_payload = {"prompt": "Portrait of engineer", "aspect_ratio": "1:1"}

    assert RevisionController.should_revise(failing_scorecard, current_iteration=0) is True
    assert RevisionController.should_revise(failing_scorecard, current_iteration=1) is True
    # At max iteration 2, should not revise further
    assert RevisionController.should_revise(failing_scorecard, current_iteration=2) is False

    fix = RevisionController.formulate_targeted_fix(
        scorecard=failing_scorecard,
        intent=intent,
        brief=brief,
        compiled_payload=initial_payload,
        iteration=1,
    )
    assert "anatomically flawless" in fix["payload"]["prompt"]
    assert fix["revision_item"].iteration == 1


@pytest.mark.asyncio
async def test_full_orchestrator_pipeline():
    """Verify end-to-end execution of the 7-stage VisualCreativeOrchestrator."""
    mock_db = MagicMock()
    orchestrator = VisualCreativeOrchestrator(mock_db, "test-tenant")

    # Mock asset generator to return a valid URL
    with patch.object(
        orchestrator.generator,
        "execute_generation",
        new_callable=AsyncMock,
        return_value={"success": True, "url": "https://cdn.octaos.ai/img/mock_asset.png", "error": None}
    ):
        record: VisualRunRecord = await orchestrator.execute(
            raw_prompt="A luxury espresso machine on dark granite with steam and morning light",
            deliverable="image",
            platform="instagram",
            inspect_quality=True,
        )

        assert record.status == "completed"
        assert record.primary_asset_url == "https://cdn.octaos.ai/img/mock_asset.png"
        assert len(record.selected_specialists) >= 2
        assert record.quality_review.passed is True
        assert record.quality_review.weighted_score >= 70.0
        assert record.creative_brief is not None
        assert "espresso" in record.creative_brief.focal_subject.lower()


@pytest.mark.asyncio
async def test_multimodal_vision_critic_parsing():
    """Verify visual critic processes multimodal vision model responses with markdown fences."""
    mock_db = MagicMock()
    critic = VisualCritic(mock_db, "test-tenant")
    intent = VisualIntentAnalyzer.analyze("Commercial photo of an executive laptop")
    brief = DynamicCreativeDirector.create_brief(intent)

    mock_vision_json = """```json
    {
      "scores": {
        "brief_fidelity": 4,
        "composition": 4,
        "craft_lighting": 4,
        "naturalness": 3,
        "continuity_anatomy": 4,
        "typography_brand": 3,
        "technical_delivery": 4
      },
      "defects": ["Minor reflection softness on bezel"],
      "blockers": []
    }
    ```"""

    with patch("app.services.llm_gateway.LLMGateway.complete_vision", new_callable=AsyncMock, return_value=mock_vision_json):
        scorecard = await critic.inspect(
            asset_url="https://cdn.octaos.ai/img/test_laptop.png",
            intent=intent,
            brief=brief,
        )
        assert scorecard.inspected is True
        assert scorecard.passed is True
        assert scorecard.weighted_score > 85.0
        assert len(scorecard.defects) == 1
        assert "bezel" in scorecard.defects[0]["defect"].lower()


def test_model_router_provider_key_fallback():
    """Verify router falls back to available configured provider when preferred lacks key."""
    intent = VisualIntentAnalyzer.analyze("Editorial poster with bold typography")
    brief = DynamicCreativeDirector.create_brief(intent)

    mock_db = MagicMock()
    # Mock LLMGateway._get_api_key so openrouter has no key, but together has key
    def fake_get_key(provider):
        return "fake-together-key" if provider == "together" else ""

    with patch("app.services.llm_gateway.LLMGateway._get_api_key", side_effect=fake_get_key):
        provider, model = VisualModelRouter.select_model(
            intent=intent,
            brief=brief,
            db_session=mock_db,
            tenant_id="test-tenant",
        )
        # Should fallback from openrouter/ideogram to together/flux
        assert provider == "together"
        assert "flux" in model.lower()


@pytest.mark.asyncio
async def test_skill_synthesizer_execute_bridge():
    """Verify skill synthesizer provides direct executable runner for visual skill."""
    mock_db = MagicMock()
    with patch(
        "app.services.marketing.visual_creative.asset_generator.AssetGenerator.execute_generation",
        new_callable=AsyncMock,
        return_value={"success": True, "url": "https://cdn.octaos.ai/img/bridge_asset.png", "error": None}
    ):
        result = await skill_synthesizer.execute_skill(
            "creative.universal_visual_director",
            db_session=mock_db,
            tenant_id="test-tenant",
            raw_prompt="Portrait of a founder",
            deliverable="image",
            inspect_quality=False,
        )
        assert result.status == "completed"
        assert result.primary_asset_url == "https://cdn.octaos.ai/img/bridge_asset.png"

