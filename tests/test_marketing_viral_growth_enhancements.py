"""Unit and Integration Tests for Marketing Viral Growth and Algorithm Retention Upgrades."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.marketing.campaign_os.contracts import (
    TimeSlotSpec,
    BrandContextAnchor,
    PlatformPostDraft,
    AudiencePersonaSpec,
)
from app.services.marketing.campaign_os.roles import CampaignRolesEngine
from app.services.marketing.campaign_os.orchestrator import FinalCopyComposer
from app.services.marketing.compiler.prompt_compiler import (
    VideoShotPlan,
    MediaPromptCompiler,
)
from app.services.marketing.context_radar.news_radar import NewsRadar
from app.services.marketing.virtual_influencer import validate_virtual_influencer_brief


def test_final_copy_composer_strips_outbound_links_on_linkedin_and_instagram():
    """Verify FinalCopyComposer prevents algorithm penalties by stripping URLs from captions."""
    raw_body = "We discovered 3 critical bottlenecks in autonomous systems. Read our full report at https://octaos.com/whitepaper for more."
    raw_cta = "Visit https://octaos.com/demo to schedule."
    
    # LinkedIn
    li_copy = FinalCopyComposer.compose(
        hook="Why 90% of automated workflows stall at scale.",
        body=raw_body,
        cta=raw_cta,
        hashtags=["#Automation", "#Enterprise"],
        platform="linkedin",
    )
    assert "https://octaos.com" not in li_copy
    assert "🔗 Direct resource link is pinned in the first comment below." in li_copy

    # Instagram
    ig_copy = FinalCopyComposer.compose(
        hook="Why 90% of automated workflows stall at scale.",
        body=raw_body,
        cta=raw_cta,
        hashtags=["#Tech", "#AI"],
        platform="instagram",
    )
    assert "https://octaos.com" not in ig_copy
    assert "💬 Comment below and we'll DM you the complete access link." in ig_copy

    # X / Twitter preserves link
    x_copy = FinalCopyComposer.compose(
        hook="Why 90% of automated workflows stall at scale.",
        body=raw_body,
        cta=raw_cta,
        hashtags=["#AI"],
        platform="x",
    )
    assert "https://octaos.com" in x_copy


def test_media_prompt_compiler_video_reel_metadata():
    """Verify VideoShotPlan and MediaPromptCompiler compile complete Reel blueprints with audio & subtitles."""
    plan = VideoShotPlan(
        scene_description="Developer looking at glowing analytics dashboard",
        duration_seconds=5,
        aspect_ratio="9:16",
        hook_3s="Stop manually routing your B2B leads",
        voiceover_script="Manual lead routing is costing you 40% of inbound revenue every week.",
        caption_style="kinetic_bold_center",
        audio_direction="high_tempo_tech_pulse",
    )
    compiled = MediaPromptCompiler.compile_video_shot_list(plan)
    
    assert compiled["aspect_ratio"] == "9:16"
    assert compiled["duration"] == 5
    assert compiled["hook_3s"] == "Stop manually routing your B2B leads"
    assert "Manual lead routing is costing you" in compiled["voiceover_script"]
    assert compiled["caption_style"] == "kinetic_bold_center"
    assert compiled["audio_direction"] == "high_tempo_tech_pulse"
    assert "Cinematic 9:16 video sequence" in compiled["prompt"]


def test_media_prompt_compiler_carousel_slides():
    """Verify compile_carousel_slides generates high-retention 5-slide document blueprints."""
    takeaways = [
        "Audit where your engineers spend >30 mins daily",
        "Replace fragmented notifications with unified event routing",
        "Set strict deterministic guardrails before autonomous execution",
        "Review weekly completion metrics instead of vanity activity",
    ]
    carousel = MediaPromptCompiler.compile_carousel_slides(
        headline="The 4-Step Autonomous Playbook",
        takeaways=takeaways,
        brand_colors=["#0F172A", "#38BDF8", "#FFFFFF"],
        cta="Save this for your sprint planning",
    )
    assert carousel["format"] == "carousel_pdf"
    assert carousel["slide_count"] == 6  # 1 cover + 4 content + 1 save CTA
    assert carousel["slides"][0]["role"] == "hook_cover"
    assert carousel["slides"][0]["title"] == "The 4-Step Autonomous Playbook"
    assert carousel["slides"][-1]["role"] == "save_cta"
    assert "Save this breakdown" in carousel["slides"][-1]["title"]


def test_news_radar_viral_reel_hooks():
    """Verify NewsRadar generates structured short-form video formats tailored for retention."""
    mock_db = MagicMock()
    radar = NewsRadar(mock_db, "tenant_test")
    reel_hooks = radar.get_viral_reel_hooks(industry="SaaS")
    
    assert len(reel_hooks) >= 3
    formats = [h["format"] for h in reel_hooks]
    assert "counter_intuitive_truth" in formats
    assert "workflow_teardown" in formats
    assert "behind_the_scenes_audit" in formats
    for h in reel_hooks:
        assert "{industry}" not in h["hook"]
        assert "0-1.5s" in h["structure"] or "0-2s" in h["structure"]


def test_virtual_influencer_consistency_anchors():
    """Verify virtual influencer validation preserves facial consistency seeds and traits."""
    data = {
        "name": "Maya Lin",
        "persona": "AI Systems Architect and Tech Creator",
        "audience": "Founders and Senior Engineers",
        "voice": "Direct, insightful, pragmatic",
        "visual_prompt": "Portrait of a 28yo Asian-American tech specialist in modern studio",
        "intro_caption": "Hey everyone, I'm Maya! Exploring autonomous systems.",
        "content_pillars": ["AI Architecture", "System Scaling"],
        "reference_image_url": "https://cdn.example.com/maya_canonical.png",
        "character_seed": 98765,
        "consistency_traits": "dark hair in minimalist ponytail, oval glasses, neutral linen blazer",
    }
    validated = validate_virtual_influencer_brief(data)
    assert validated["name"] == "Maya Lin"
    assert validated["reference_image_url"] == "https://cdn.example.com/maya_canonical.png"
    assert validated["character_seed"] == 98765
    assert "oval glasses" in validated["consistency_traits"]
    assert validated["disclosure"] == "AI-generated virtual persona; not a real person or customer."


@pytest.mark.asyncio
async def test_viral_hook_engineer_eliminates_corporate_fluff():
    """Verify Viral Hook Engineer replaces corporate throat-clearing with high-impact curiosity lines."""
    mock_db = MagicMock()
    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value="""{
        "winning_hook": "Why top engineering teams are quietly replacing traditional sprint planning.",
        "angle_type": "counter_intuitive_truth",
        "hook_variants": [
            {"type": "counter_intuitive_truth", "text": "Why top engineering teams are quietly replacing traditional sprint planning."},
            {"type": "negative_curiosity", "text": "Stop holding 2-hour backlog grooming sessions before checking this bottleneck."},
            {"type": "behind_the_curtain", "text": "We analyzed 200 sprint logs. Here is where 35% of engineering velocity disappears."}
        ]
    }""")
    
    roles = CampaignRolesEngine(mock_db, "tenant_test")
    roles.llm = mock_llm

    slot = TimeSlotSpec(
        day=1,
        slot_index=1,
        slot_label="Day 1 Slot 1",
        platform="linkedin",
        thematic_angle="Engineering Efficiency",
        scheduled_time_utc="2026-11-01T09:00:00Z",
        target_action="engagement",
    )
    audience = AudiencePersonaSpec(
        target_persona="VP of Engineering",
        acute_pain_points=["Sprint planning drag", "Context switching"],
        primary_objections=["Too busy to adopt new tooling"],
        content_appetite="Data-driven benchmarks",
    )
    brand_anchor = MagicMock()
    brand_anchor.industry = "Software & Cloud Infrastructure"
    brand_anchor.audience_persona = audience

    draft = PlatformPostDraft(
        platform="linkedin",
        day=1,
        hook="In today's fast-paced enterprise landscape, agility is crucial.",
        body_content="Sprint planning often takes up hours.",
        cta_sentence="Learn more.",
        hashtags=["#Engineering"],
        formatted_full_post="In today's fast-paced enterprise landscape, agility is crucial.",
    )

    hook_variant = await roles.execute_hook_engineer(slot, brand_anchor, draft)
    assert hook_variant.winning_hook == "Why top engineering teams are quietly replacing traditional sprint planning."
    assert "In today's" not in hook_variant.winning_hook
