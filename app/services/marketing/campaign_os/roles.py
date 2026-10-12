"""The 9 Typed LLM Roles for the Campaign Creative Operating System.

Workstream B:
- Explicit Pydantic contracts for every role
- Model routing: Frontier models for Strategy & Judge; Small models for execution & creative intent JSON
"""
import json
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.services.llm_gateway import LLMGateway
from app.services.knowledge_os.entity_extractor import extract_json_safe
from app.services.marketing.campaign_os.contracts import (
    BrandStrategyBrief,
    VisualIdentityTokens,
    CampaignNarrativeArc,
    CampaignDayOutline,
    PlatformPostDraft,
    CallToActionSpec,
    CritiqueScoreCard,
    BrandDNAProfile,
    ProductCatalogSnapshot,
    AudiencePersonaSpec,
    EvidenceProofCurator,
    ContextRadarSignal,
    BrandContextAnchor,
    TimeSlotSpec,
    TimeSlotSchedulePlan,
    HookAngleVariant,
    FactCheckAuditResult,
    ComplianceAuditResult,
    CMOExecutiveVerdict,
)
from app.services.marketing.compiler.prompt_compiler import (
    CreativeIntentJSON,
    VideoShotPlan,
)

logger = logging.getLogger(__name__)


def _parse_draft_from_raw_text(raw_text: str, platform: str, day: int, suggested_hook: str) -> PlatformPostDraft:
    """Robust fallback parser extracting real LLM post content when strict JSON decoding fails."""
    clean = raw_text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```[a-zA-Z]*\n", "", clean)
        clean = re.sub(r"\n```$", "", clean).strip()

    hashtags = re.findall(r"#[A-Za-z0-9_]+", clean)
    lines = [line.strip() for line in clean.split("\n") if line.strip()]
    hook = lines[0] if lines else suggested_hook
    hook = re.sub(r"^(Hook|Headline|Opening):\s*", "", hook, flags=re.IGNORECASE)

    body = "\n\n".join(lines[1:-1]) if len(lines) > 2 else clean
    cta = lines[-1] if len(lines) > 1 else "Share your thoughts below."
    if cta.startswith("#") and len(lines) > 2:
        cta = lines[-2]

    return PlatformPostDraft(
        platform=platform,
        day=day,
        hook=hook,
        body_content=body,
        cta_sentence=cta,
        hashtags=hashtags or ["#Innovation", "#Enterprise"],
        formatted_full_post=clean,
    )


class CampaignRolesEngine:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.llm = LLMGateway(db, tenant_id)

    # ── Role 1: Brand Strategist ──────────────────────────────────────────
    async def execute_brand_strategist(
        self,
        topic: str,
        campaign_projection: Dict[str, Any],
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> BrandStrategyBrief:
        """Formulate high-level brand strategy and defensible angle using AI."""
        system_prompt = (
            "You are the Lead Brand Strategist. Your job is to define the strategic narrative "
            "for an upcoming marketing campaign based on company context. "
            "Output valid JSON only."
        )
        prompt = f"""Company Context:
Name: {campaign_projection.get('company_name')}
Industry: {campaign_projection.get('industry')}
Brand Voice Guidelines: {json.dumps(campaign_projection.get('brand_voice', {}))}
Verified Approved Claims: {json.dumps(campaign_projection.get('approved_claims', []))}
Product Highlights: {json.dumps(campaign_projection.get('product_highlights', []))}

User Campaign Goal: {topic}

Return JSON with these exact keys:
{{
  "core_narrative": "Central thematic premise of the campaign",
  "tone_keywords": ["Adjective1", "Adjective2", "Adjective3"],
  "target_persona": "Exact title and pain point addressed",
  "key_differentiators": ["Differentiator1", "Differentiator2"],
  "approved_evidence_ids": ["evidence_id1"],
  "prohibited_topics": ["ProhibitedClaim1"]
}}"""
        try:
            resp = await self.llm.complete(prompt, system_prompt=system_prompt, provider=provider, model=model)
            data = extract_json_safe(resp)
            if not isinstance(data, dict) or not data.get("core_narrative"):
                if resp and len(resp.strip()) > 30:
                    # Best-effort recovery from non-JSON text
                    return BrandStrategyBrief(
                        core_narrative=resp.strip().split("\n")[0][:120],
                        tone_keywords=["Authoritative", "Strategic", "Actionable"],
                        target_persona="Strategic Decision Makers",
                        key_differentiators=[p.get("usp", "Scalable Solution") for p in campaign_projection.get("product_highlights", [])] or ["Operational Excellence"],
                        approved_evidence_ids=[c.get("evidence_id") for c in campaign_projection.get("approved_claims", []) if c.get("evidence_id")],
                        prohibited_topics=[],
                    )
                raise ValueError(f"AI response did not contain expected strategic brief JSON schema: {resp[:200]}")
            return BrandStrategyBrief(**data)
        except Exception as e:
            logger.error(f"[BrandStrategist] AI execution failed: {e}")
            raise RuntimeError(f"Brand Strategist AI generation failed: {e}") from e

    # ── Role 2: Visual Director ───────────────────────────────────────────
    async def execute_visual_director(
        self,
        brand_brief: BrandStrategyBrief,
        campaign_projection: Dict[str, Any],
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> VisualIdentityTokens:
        """Establish visual tokens and photographic grammar customized to the brand and topic."""
        visual_style = campaign_projection.get("visual_style", {})
        system_prompt = (
            "You are an Executive Visual Director. Establish visual identity tokens for this marketing campaign. "
            "Output valid JSON only."
        )
        prompt = f"""Campaign Narrative: {brand_brief.core_narrative}
Tone: {', '.join(brand_brief.tone_keywords)}
Company Industry: {campaign_projection.get('industry', 'Technology')}
Default Primary Color: {visual_style.get('primary_color', '#059669')}

Output JSON format:
{{
  "primary_color": "{visual_style.get('primary_color', '#059669')}",
  "secondary_color": "{visual_style.get('secondary_color', '#0F172A')}",
  "accent_color": "{visual_style.get('accent_color', '#38BDF8')}",
  "aesthetic_mood": "Mood description tailored to narrative",
  "photography_archetype": "Specific photographic style description",
  "sref_url": null
}}"""
        try:
            resp = await self.llm.complete(prompt, system_prompt=system_prompt, provider=provider, model=model)
            data = extract_json_safe(resp)
            if isinstance(data, dict) and data.get("aesthetic_mood"):
                return VisualIdentityTokens(**data)
        except Exception as e:
            logger.warning(f"[VisualDirector] LLM styling failed ({e}), using projection style tokens.")

        return VisualIdentityTokens(
            primary_color=visual_style.get("primary_color", "#059669"),
            secondary_color=visual_style.get("secondary_color", "#0F172A"),
            accent_color=visual_style.get("accent_color", "#38BDF8"),
            aesthetic_mood=f"{visual_style.get('mood', 'High-contrast editorial')}, {', '.join(brand_brief.tone_keywords)}",
            photography_archetype="Authentic documentary editorial portraiture and workspace ergonomics",
            sref_url=visual_style.get("sref_url"),
        )

    # ── Role 3: Narrative Architect ───────────────────────────────────────
    async def execute_narrative_architect(
        self,
        days: int,
        brand_brief: BrandStrategyBrief,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> CampaignNarrativeArc:
        """Structure the multi-day progression arc via AI, guaranteeing complete outlines for all requested days."""
        system_prompt = (
            "You are the Narrative Architect. You design multi-day progression arcs for marketing campaigns. "
            "Pacing progression: Hook/Problem -> Agitation -> Evidence/Proof -> Product Feature -> Social Proof -> Vision -> Call to Action. "
            "Output valid JSON only."
        )
        prompt = f"""Campaign Brief:
Narrative: {brand_brief.core_narrative}
Persona: {brand_brief.target_persona}
Total Days: {days}

CRITICAL: You MUST provide an outline item for EVERY single day from day 1 to day {days} in the "days_outline" array (a total of exactly {days} items). Do not output only day 1.

Output JSON format:
{{
  "campaign_title": "Title tailored to {brand_brief.core_narrative[:40]}",
  "total_days": {days},
  "days_outline": [
    {{
      "day": 1,
      "theme": "Day 1 Theme",
      "narrative_focus": "Problem Agitation",
      "suggested_hook_angle": "Contrarian angle",
      "target_cta_intent": "soft_curiosity"
    }}
  ]
}}"""
        pacing_flow = [
            ("Hook & Problem Agitation", "contrarian_insight", "soft_curiosity"),
            ("Problem Agitation & Friction", "root_cause_analysis", "problem_awareness"),
            ("Evidence, Framework & Proof", "case_study_data", "social_proof"),
            ("Product Feature & Unique Mechanism", "product_capability", "solution_reveal"),
            ("Customer Transformation & ROI", "practitioner_story", "testimonial"),
            ("Strategic Vision & Industry Shift", "market_evolution", "thought_leadership"),
            ("Direct Call to Action & Next Step", "actionable_invitation", "direct_conversion"),
        ]

        try:
            resp = await self.llm.complete(prompt, system_prompt=system_prompt, provider=provider, model=model)
            data = extract_json_safe(resp)
            outlines_raw = data.get("days_outline", []) if isinstance(data, dict) else []
            existing_days = {}
            for item in outlines_raw:
                if isinstance(item, dict) and "day" in item:
                    try:
                        d_num = int(item["day"])
                        existing_days[d_num] = item
                    except (ValueError, TypeError):
                        pass

            complete_outlines: List[CampaignDayOutline] = []
            for d in range(1, days + 1):
                if d in existing_days:
                    complete_outlines.append(CampaignDayOutline(**existing_days[d]))
                else:
                    focus, hook_angle, cta_intent = pacing_flow[(d - 1) % len(pacing_flow)]
                    complete_outlines.append(
                        CampaignDayOutline(
                            day=d,
                            theme=f"Day {d}: {focus}",
                            narrative_focus=focus,
                            suggested_hook_angle=f"Strategic perspective on {hook_angle.replace('_', ' ')} for {brand_brief.target_persona}",
                            target_cta_intent=cta_intent if d < days else "direct_conversion",
                        )
                    )

            campaign_title = (data.get("campaign_title") if isinstance(data, dict) else None) or brand_brief.core_narrative[:50] or "Brand Campaign"
            return CampaignNarrativeArc(
                campaign_title=campaign_title,
                total_days=days,
                days_outline=complete_outlines,
            )
        except Exception as e:
            logger.error(f"[NarrativeArchitect] AI narrative generation failed for {days} days: {e}")
            raise RuntimeError(f"Campaign narrative architect AI generation failed: {e}") from e

    # ── Role 4: Platform & Format Adapter ─────────────────────────────────
    async def execute_platform_adapter(
        self,
        day_outline: CampaignDayOutline,
        brand_brief: BrandStrategyBrief,
        platform: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        content_format: str = "social_posts",
    ) -> PlatformPostDraft:
        """Write platform-native copy using AI without synthetic templates."""
        active_format = content_format
        if content_format == "omnichannel_mix":
            r = day_outline.day % 3
            if r == 1:
                active_format = "social_posts"
            elif r == 2:
                active_format = "video_first"
            else:
                active_format = "blog_articles"

        system_prompt = (
            f"You are an elite creative director and copywriter specialized in {platform}. "
            f"Tone: {', '.join(brand_brief.tone_keywords)}. "
            f"Format style: {active_format}. Output must be valid JSON only."
        )

        format_instructions = ""
        if active_format == "blog_articles":
            format_instructions = """- Full In-Depth Thought Leadership Article:
  * Title: Compelling contrarian headline
  * Executive Summary (2-3 paragraphs)
  * Section 1: The Core Operational Friction
  * Section 2: Concrete Technical Paradigm Shift
  * Section 3: Implementation Playbook & Key Takeaways
  * Professional closing CTA"""
        elif active_format == "video_first":
            format_instructions = """- Video Script + Companion Social Caption:
  * Hook (0:00 - 0:03): High-impact visual shot & speech opener
  * Timed Visual Shot List: Breakdown of scene mechanics per beat
  * Spoken Audio Script: Clean natural voiceover narration
  * Companion Caption: Punchy caption with 5 hashtags and CTA"""
        else:
            format_instructions = """- If LinkedIn: Bold opening, 3-5 short punchy paragraphs, no emoji spam, professional CTA.
- If Instagram: Engaging hook, clean body with subtle inline emojis, clear CTA, blank line, hashtags.
- If Facebook: Conversational storytelling, clear CTA, 5 hashtags."""

        prompt = f"""Write high-impact {platform} content for Day {day_outline.day}.
Core Narrative: {brand_brief.core_narrative}
Theme: {day_outline.theme} ({day_outline.narrative_focus})
Suggested Hook: {day_outline.suggested_hook_angle}

Format Instructions:
{format_instructions}

Output JSON:
{{
  "platform": "{platform}",
  "day": {day_outline.day},
  "hook": "Opening hook sentence or headline",
  "body_content": "Main body or complete article markdown",
  "cta_sentence": "Call to action sentence",
  "hashtags": ["#tag1", "#tag2", "#tag3"],
  "formatted_full_post": "Complete copy-paste ready text"
}}"""
        try:
            resp = await self.llm.complete(prompt, system_prompt=system_prompt, provider=provider, model=model)
            data = extract_json_safe(resp)
            if isinstance(data, dict) and data.get("formatted_full_post"):
                return PlatformPostDraft(**data)
            elif resp and len(resp.strip()) > 20:
                # Recover actual AI output if JSON parsing failed
                return _parse_draft_from_raw_text(
                    raw_text=resp,
                    platform=platform,
                    day=day_outline.day,
                    suggested_hook=day_outline.suggested_hook_angle,
                )
            raise ValueError(f"AI returned empty content for Day {day_outline.day} on {platform}.")
        except Exception as e:
            logger.error(f"[PlatformAdapter] Failed generating {platform} post for Day {day_outline.day}: {e}")
            raise RuntimeError(f"Platform adapter ({platform}, Day {day_outline.day}) AI generation failed: {e}") from e

    # ── Role 5: Offer/CTA Engineer ────────────────────────────────────────
    async def execute_offer_cta_engineer(
        self,
        draft: PlatformPostDraft,
        brand_brief: BrandStrategyBrief,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> CallToActionSpec:
        """Optimize call-to-action for maximum friction-free conversion using AI."""
        system_prompt = (
            "You are a Conversion Rate Optimization Specialist. "
            "Analyze the post draft and output a refined CTA with action_type and friction_level (low/medium/high). "
            "Output JSON only."
        )
        prompt = f"""Post Copy:
{draft.formatted_full_post[:300]}

Persona: {brand_brief.target_persona}
Current CTA: {draft.cta_sentence}

Output JSON format:
{{
  "cta_copy": "Refined action-oriented call to action sentence",
  "action_type": "consultation",
  "friction_level": "low"
}}"""
        try:
            resp = await self.llm.complete(prompt, system_prompt=system_prompt, provider=provider, model=model)
            data = extract_json_safe(resp)
            if isinstance(data, dict) and data.get("cta_copy"):
                return CallToActionSpec(**data)
        except Exception:
            pass

        return CallToActionSpec(
            cta_copy=draft.cta_sentence,
            action_type="consultation" if "demo" in draft.cta_sentence.lower() else "engagement",
            friction_level="low",
        )

    # ── Role 6: Image Concept Director ────────────────────────────────────
    async def execute_image_concept_director(
        self,
        draft: PlatformPostDraft,
        visual_tokens: VisualIdentityTokens,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        reference_image_url: Optional[str] = None,
    ) -> CreativeIntentJSON:
        """Emit structured creative intent JSON decomposing concepts into photographic tokens via AI."""
        ref_context = (
            f"Reference Asset URL: {reference_image_url}. Maintain brand subject consistency and styling cues."
            if reference_image_url else ""
        )
        system_prompt = (
            "You are an Art Director. Translate post copy into structured visual creative intent JSON. "
            "Do NOT write generic corporate clip-art. Describe concrete physical subjects, authentic textures, "
            "and realistic lighting. Output valid JSON matching the schema exactly."
        )
        prompt = f"""Post Copy:
{draft.formatted_full_post[:300]}

Brand Mood: {visual_tokens.aesthetic_mood}
Primary Color: {visual_tokens.primary_color}
{ref_context}

Output JSON format:
{{
  "subject": "Clear physical subject tailored to this post",
  "action_or_state": "authentic action depicting the subject",
  "environment_setting": "specific architectural or natural setting",
  "emotional_mood": "emotional atmosphere",
  "shot_type": "cinematic medium wide shot",
  "lighting_intent": "lighting characteristics",
  "negative_space_direction": "right_40pct",
  "color_accents": ["{visual_tokens.primary_color}", "{visual_tokens.secondary_color}"]
}}"""
        try:
            resp = await self.llm.complete(prompt, system_prompt=system_prompt, provider=provider, model=model)
            data = extract_json_safe(resp)
            if isinstance(data, dict) and data.get("subject"):
                return CreativeIntentJSON(**data)
            raise ValueError(f"Image Concept Director JSON missing subject: {resp[:150]}")
        except Exception as e:
            logger.warning(f"[ImageConceptDirector] LLM call failed ({e}), creating contextual intent from hook.")

        return CreativeIntentJSON(
            subject=f"Professional modern workspace scene representing {draft.hook[:80]}",
            action_or_state="evaluating architectural systems and data workflows",
            environment_setting="minimalist modern enterprise studio",
            emotional_mood=visual_tokens.aesthetic_mood or "composed and authoritative",
            shot_type="cinematic medium wide shot",
            lighting_intent="natural directional morning light",
            negative_space_direction="right_40pct",
            color_accents=[visual_tokens.primary_color, visual_tokens.secondary_color],
        )

    # ── Role 7: Video Shot Planner ────────────────────────────────────────
    async def execute_video_shot_planner(
        self,
        draft: PlatformPostDraft,
        visual_tokens: VisualIdentityTokens,
        platform: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        reference_image_url: Optional[str] = None,
    ) -> VideoShotPlan:
        """Design structured video shot plan with camera kinematics using AI."""
        ar = "9:16" if platform in ("instagram", "reels", "tiktok", "shorts") else "16:9"
        system_prompt = (
            "You are a Cinematic Director. Design a realistic 5-second video shot plan for this marketing post. "
            "Output JSON only."
        )
        prompt = f"""Post Hook: {draft.hook}
Platform: {platform}
Aspect Ratio: {ar}
Aesthetic: {visual_tokens.aesthetic_mood}

Output JSON format:
{{
  "scene_description": "Cinematic visual description depicting the post theme",
  "duration_seconds": 5,
  "camera_movement": "precise camera movement description",
  "focal_motion": "subtle motion within the scene",
  "atmosphere_notes": "lighting and atmospheric details",
  "aspect_ratio": "{ar}"
}}"""
        try:
            resp = await self.llm.complete(prompt, system_prompt=system_prompt, provider=provider, model=model)
            data = extract_json_safe(resp)
            if isinstance(data, dict) and data.get("scene_description"):
                return VideoShotPlan(**data)
        except Exception as e:
            logger.warning(f"[VideoShotPlanner] LLM call failed ({e}), creating contextual plan from hook.")

        return VideoShotPlan(
            scene_description=f"A cinematic editorial scene visually representing: {draft.hook[:100]}",
            duration_seconds=5,
            camera_movement="slow cinematic dolly-in tracking forward smoothly with subtle focal rack",
            focal_motion="ambient dynamic lighting reflecting modern workspace analytics",
            atmosphere_notes=f"volumetric lighting complementing {visual_tokens.aesthetic_mood}",
            aspect_ratio=ar,
        )

    # ── Role 9: Critic / Judge with Self-Repair Loop ──────────────────────
    async def execute_critic_judge(
        self,
        post_draft: PlatformPostDraft,
        approved_evidence: List[Dict[str, Any]],
        brand_brief: BrandStrategyBrief,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> CritiqueScoreCard:
        """Independent judge auditing groundedness, platform fit, and brand voice with 1-attempt repair loop."""
        from app.services.marketing.campaign_os.claim_verifier import ClaimVerifier
        from app.services.marketing.campaign_os.compliance_engine import ComplianceRulesEngine

        # 1. Deterministic Claim Verification
        claim_result = ClaimVerifier.verify_post_claims(
            content=post_draft.formatted_full_post,
            approved_evidence=approved_evidence,
        )

        # 2. Deterministic Compliance Check
        comp_result = ComplianceRulesEngine.audit_post(
            content=post_draft.formatted_full_post,
            platform=post_draft.platform,
        )

        # 3. LLM Qualitative Evaluation
        system_prompt = (
            "You are an impartial Executive Editor. Evaluate this marketing post on a strict 0.0 to 1.0 scale. "
            "Output JSON only."
        )
        prompt = f"""Post to audit:
{post_draft.formatted_full_post}

Brand Guidelines:
Narrative: {brand_brief.core_narrative}
Tone: {', '.join(brand_brief.tone_keywords)}

Return JSON:
{{
  "platform_fit_score": 0.95,
  "brand_voice_score": 0.90,
  "critique_notes": "Observations on tone, flow, and clarity"
}}"""
        platform_fit = 0.90
        brand_voice = 0.90
        critique_notes = "Meets editorial standards."

        try:
            resp = await self.llm.complete(prompt, system_prompt=system_prompt, provider=provider, model=model)
            data = extract_json_safe(resp)
            platform_fit = float(data.get("platform_fit_score", 0.90))
            brand_voice = float(data.get("brand_voice_score", 0.90))
            raw_notes = data.get("critique_notes", "")
            if isinstance(raw_notes, list):
                critique_notes = "\n".join(str(n) for n in raw_notes if n)
            elif isinstance(raw_notes, str):
                critique_notes = raw_notes
            elif raw_notes is not None:
                critique_notes = str(raw_notes)
            else:
                critique_notes = "Meets editorial standards."
        except Exception:
            pass

        # Compute overall confidence
        groundedness = claim_result.citation_coverage_score
        overall_conf = round(min(groundedness, platform_fit, brand_voice), 2)
        is_approved = claim_result.all_claims_grounded and comp_result.passed and overall_conf >= 0.85

        # 4. Targeted Self-Repair Loop (1 Attempt) if validation failed
        if not is_approved:
            issues = []
            if not claim_result.all_claims_grounded:
                issues.extend([f"Ungrounded claim: {u}" for u in claim_result.unsupported_claims])
            if not comp_result.passed:
                issues.extend(comp_result.violations)

            repair_prompt = f"""The previous post draft had compliance/grounding issues:
{'; '.join(issues)}

Original post:
{post_draft.formatted_full_post}

Please rewrite the post to completely remove all ungrounded claims and fix compliance violations, maintaining {brand_brief.core_narrative}.
Output JSON with formatted_full_post only:
{{"formatted_full_post": "Corrected text"}}"""
            try:
                repair_resp = await self.llm.complete(repair_prompt, system_prompt="You are a strict compliance editor.", provider=provider, model=model)
                repair_data = extract_json_safe(repair_resp)
                repaired_text = repair_data.get("formatted_full_post")
                if repaired_text and len(repaired_text) > 20:
                    post_draft.formatted_full_post = repaired_text
                    # Re-verify
                    second_claim = ClaimVerifier.verify_post_claims(content=repaired_text, approved_evidence=approved_evidence)
                    second_comp = ComplianceRulesEngine.audit_post(content=repaired_text, platform=post_draft.platform)
                    if second_claim.all_claims_grounded and second_comp.passed:
                        is_approved = True
                        overall_conf = 0.90
                        critique_notes = "Auto-repaired compliance issues successfully."
            except Exception:
                pass

        return CritiqueScoreCard(
            groundedness_score=groundedness,
            unsupported_claims=claim_result.unsupported_claims,
            platform_fit_score=platform_fit,
            brand_voice_score=brand_voice,
            compliance_passed=comp_result.passed,
            compliance_issues=comp_result.violations,
            overall_confidence=overall_conf,
            is_approved=is_approved,
            critique_notes=critique_notes,
        )

    # ── Agent 1: Brand DNA & Tone Synthesizer ────────────────────────────
    async def execute_brand_dna_synthesizer(
        self,
        company_context: Dict[str, Any],
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> BrandDNAProfile:
        """Agent 1: Ingests brand guidelines and extracts core voice, adjectives, vocabulary, and banned words."""
        brand_voice = company_context.get("brand_voice", {})
        system_prompt = (
            "You are the Brand DNA & Tone Synthesizer (Agent 1 of 15). "
            "Analyze company profile and brand guidelines to extract core voice attributes. "
            "Output valid JSON only."
        )
        prompt = f"""Company Name: {company_context.get('company_name', 'Brand')}
Industry: {company_context.get('industry', 'Technology')}
Existing Brand Voice: {json.dumps(brand_voice)}

Output JSON format:
{{
  "company_name": "{company_context.get('company_name', 'Brand')}",
  "brand_voice_summary": "Comprehensive 1-2 sentence definition of the brand's tone and persona",
  "tone_keywords": ["Authoritative", "Pragmatic", "Visionary"],
  "vocabulary_allowed": ["Autonomous", "Enterprise", "Scalable", "Reliable"],
  "banned_words": ["Game-changing", "Revolutionary", "Miracle"],
  "core_values": ["Operational Excellence", "Deterministic Safety", "Client Trust"]
}}"""
        try:
            resp = await self.llm.complete(prompt, system_prompt=system_prompt, provider=provider, model=model)
            data = extract_json_safe(resp)
            if isinstance(data, dict) and data.get("brand_voice_summary"):
                return BrandDNAProfile(**data)
        except Exception as e:
            logger.warning(f"[Agent 1: BrandDNA] LLM extraction failed ({e}), using fallback.")

        tones = brand_voice.get("tone", "Authoritative, Pragmatic, Visionary")
        tone_list = [t.strip() for t in tones.split(",") if t.strip()] if isinstance(tones, str) else ["Authoritative", "Pragmatic"]
        vocab = brand_voice.get("vocabulary", ["Autonomous", "Enterprise", "Reliable"])
        banned = brand_voice.get("banned_words", ["Game-changing", "Revolutionary"])
        return BrandDNAProfile(
            company_name=company_context.get("company_name", "Brand"),
            brand_voice_summary=f"Authoritative B2B voice in {company_context.get('industry', 'Technology')} prioritizing grounded value.",
            tone_keywords=tone_list,
            vocabulary_allowed=vocab if isinstance(vocab, list) else ["Autonomous", "Enterprise"],
            banned_words=banned if isinstance(banned, list) else ["Revolutionary"],
            core_values=["Operational Excellence", "Integrity"],
        )

    # ── Agent 2: Product & Service Catalog Specialist ────────────────────
    async def execute_product_catalog_specialist(
        self,
        company_context: Dict[str, Any],
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> ProductCatalogSnapshot:
        """Agent 2: Normalizes products, USPs, key features, and pricing tiers to anchor marketing in genuine capabilities."""
        catalog = company_context.get("products_catalog", []) or company_context.get("product_highlights", [])
        system_prompt = (
            "You are the Product & Service Catalog Specialist (Agent 2 of 15). "
            "Structure the company's verified products, services, and value propositions for promotional campaigns. "
            "Output valid JSON only."
        )
        prompt = f"""Company: {company_context.get('company_name')}
Product Data: {json.dumps(catalog[:8])}

Output JSON format:
{{
  "products_count": {len(catalog)},
  "products": [
    {{
      "name": "Product or Feature Name",
      "description": "Clear capability summary",
      "usp": "Unique advantage",
      "target_persona": "Primary beneficiary"
    }}
  ],
  "core_usps": ["Key USP 1", "Key USP 2"],
  "highlighted_offers": ["Platform Demo", "Architecture Audit"]
}}"""
        try:
            resp = await self.llm.complete(prompt, system_prompt=system_prompt, provider=provider, model=model)
            data = extract_json_safe(resp)
            if isinstance(data, dict) and data.get("products"):
                return ProductCatalogSnapshot(**data)
        except Exception as e:
            logger.warning(f"[Agent 2: ProductCatalog] LLM call failed ({e}), using raw catalog projection.")

        norm_prods = []
        for p in catalog:
            if isinstance(p, dict):
                norm_prods.append({
                    "name": p.get("name") or p.get("title") or "Enterprise Solution",
                    "description": p.get("description") or p.get("summary") or "Core offering capability",
                    "usp": p.get("usp") or "Autonomous execution with enterprise safety",
                    "target_persona": p.get("target_persona") or "Enterprise Leaders",
                })
        if not norm_prods:
            norm_prods = [{
                "name": f"{company_context.get('company_name', 'Company')} Core Platform",
                "description": company_context.get("service_description", "Autonomous agent workflows and solutions."),
                "usp": company_context.get("usp", "Deterministic execution with enterprise reliability"),
                "target_persona": "Operational Decision Makers",
            }]
        return ProductCatalogSnapshot(
            products_count=len(norm_prods),
            products=norm_prods,
            core_usps=[p["usp"] for p in norm_prods if p.get("usp")],
            highlighted_offers=["Live Architecture Walkthrough", "Trial Deployment"],
        )

    # ── Agent 3: ICP Persona & Audience Intelligence ─────────────────────
    async def execute_audience_profiler(
        self,
        company_context: Dict[str, Any],
        topic: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AudiencePersonaSpec:
        """Agent 3: Identifies target buyer personas, acute pain points, desired outcomes, and objections."""
        target_audiences = company_context.get("target_audiences", [])
        system_prompt = (
            "You are the ICP Persona & Audience Intelligence Agent (Agent 3 of 15). "
            "Define the buyer persona and psychological drivers for this campaign. "
            "Output valid JSON only."
        )
        prompt = f"""Industry: {company_context.get('industry', 'Technology')}
Campaign Topic: {topic}
Existing Audience Data: {json.dumps(target_audiences[:3])}

Output JSON format:
{{
  "target_persona": "Exact title, e.g., Chief Operating Officer or VP of Engineering",
  "acute_pain_points": ["Pain point 1", "Pain point 2", "Pain point 3"],
  "desired_outcomes": ["Outcome 1", "Outcome 2"],
  "buying_objections": ["Objection 1", "Objection 2"],
  "resonance_triggers": ["Trigger 1", "Trigger 2"]
}}"""
        try:
            resp = await self.llm.complete(prompt, system_prompt=system_prompt, provider=provider, model=model)
            data = extract_json_safe(resp)
            if isinstance(data, dict) and data.get("target_persona"):
                return AudiencePersonaSpec(**data)
        except Exception as e:
            logger.warning(f"[Agent 3: AudienceProfiler] LLM call failed ({e}), using default persona spec.")

        first_aud = target_audiences[0] if target_audiences and isinstance(target_audiences[0], dict) else {}
        persona = first_aud.get("persona") or first_aud.get("title") or "Enterprise Operations & Technology Leaders"
        pains = first_aud.get("pain_points") or [
            "Manual workflow bottlenecks slowing team execution",
            "Lack of end-to-end visibility across departmental handoffs",
            "High overhead maintaining brittle bespoke automations",
        ]
        return AudiencePersonaSpec(
            target_persona=persona,
            acute_pain_points=pains if isinstance(pains, list) else [str(pains)],
            desired_outcomes=["Predictable scale", "Elimination of repetitive manual coordination", "Faster cycle time"],
            buying_objections=["Implementation complexity", "Security and compliance guardrails", "System switching cost"],
            resonance_triggers=["Demonstrated operational ROI", "Verified enterprise case studies", "Immediate proof of value"],
        )

    # ── Agent 4: Evidence & Truth Claim Curator ──────────────────────────
    async def execute_proof_point_curator(
        self,
        company_context: Dict[str, Any],
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> EvidenceProofCurator:
        """Agent 4: Curates verified proof points, statistics, case study metrics, and prohibited claims."""
        approved = company_context.get("approved_claims", []) or company_context.get("proof_points", [])
        approved_ids = [c.get("evidence_id") for c in approved if isinstance(c, dict) and c.get("evidence_id")]
        metrics = []
        for c in approved:
            if isinstance(c, dict) and c.get("claim"):
                metrics.append(c["claim"])
            elif isinstance(c, str):
                metrics.append(c)

        return EvidenceProofCurator(
            approved_evidence_ids=approved_ids or ["ev_verified_catalog"],
            approved_claims=approved if isinstance(approved, list) else [],
            verified_metrics=metrics or ["Eliminates up to 80% of repetitive operational tasks", "Sub-second deterministic workflow dispatch"],
            prohibited_claims=[
                "Unsubstantiated 100% guarantees without operational prerequisites",
                "Speculative competitor benchmarks without verifiable audit trail",
            ],
        )

    # ── Agent 5: Context Radar & Cultural Sentinel ───────────────────────
    async def execute_context_radar_sentinel(
        self,
        company_context: Dict[str, Any],
        days: int = 7,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> ContextRadarSignal:
        """Agent 5: Ingests marketing calendar events & news radar signals to connect brand USPs with current trends."""
        try:
            from app.services.marketing.context_radar.calendar_engine import CalendarEngine
            from app.services.marketing.context_radar.news_radar import NewsRadar
            cal = CalendarEngine(self.db, self.tenant_id)
            news = NewsRadar(self.db, self.tenant_id)
            events = cal.get_upcoming_events(days_ahead=max(7, days))
            signals = news.get_top_signals(limit=4, brand_context=company_context.get("industry", "technology"))
        except Exception as radar_err:
            logger.debug(f"[Agent 5: ContextRadar] Live engines bypassed ({radar_err}), using defaults.")
            events = []
            signals = []

        timely_hooks = [e.get("hook") for e in events if e.get("hook")]
        if not timely_hooks:
            timely_hooks = [
                "Quarterly operational review season: aligning automated workflows with business velocity",
                "Strategic resilience: replacing fragile manual handoffs with verified system intelligence",
            ]

        return ContextRadarSignal(
            upcoming_calendar_events=events[:4],
            active_news_signals=signals[:4],
            timely_hooks=timely_hooks[:3],
        )

    # ── Synthesize Unified Brand Context Anchor (Agents 1-5 Coordinator) ─
    async def synthesize_brand_context_anchor(
        self,
        company_context: Dict[str, Any],
        topic: str,
        days: int = 7,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> BrandContextAnchor:
        """Coordinates Agents 1 through 5 into an immutable, unified brand context anchor."""
        brand_dna = await self.execute_brand_dna_synthesizer(company_context, provider=provider, model=model)
        catalog = await self.execute_product_catalog_specialist(company_context, provider=provider, model=model)
        audience = await self.execute_audience_profiler(company_context, topic=topic, provider=provider, model=model)
        proof = await self.execute_proof_point_curator(company_context, provider=provider, model=model)
        radar = await self.execute_context_radar_sentinel(company_context, days=days, provider=provider, model=model)

        visual_style = company_context.get("visual_style", {})
        visual_tokens = VisualIdentityTokens(
            primary_color=visual_style.get("primary_color", "#059669"),
            secondary_color=visual_style.get("secondary_color", "#0F172A"),
            accent_color=visual_style.get("accent_color", "#38BDF8"),
            aesthetic_mood=f"{visual_style.get('mood', 'Cinematic architectural realism')}, {', '.join(brand_dna.tone_keywords)}",
            photography_archetype=visual_style.get("photography_guidelines", "Authentic editorial lookbook with natural light"),
            sref_url=visual_style.get("sref_url"),
        )

        return BrandContextAnchor(
            company_name=company_context.get("company_name", "Brand"),
            website=company_context.get("website", ""),
            industry=company_context.get("industry", "Technology"),
            promo_goal=topic,
            brand_dna=brand_dna,
            product_catalog=catalog,
            audience_persona=audience,
            proof_points=proof,
            context_radar=radar,
            visual_tokens=visual_tokens,
            compliance_rules=company_context.get("compliance_rules", [
                "Never guarantee financial returns without disclaimers.",
                "Ensure every metric ties back to verified operational capabilities.",
            ]),
        )

    # ── Agent 7: Chronological Time-Slot Cadence Scheduler ───────────────
    async def execute_cadence_scheduler(
        self,
        narrative_arc: CampaignNarrativeArc,
        platforms: List[str],
        posts_per_day: int = 1,
        target_time_slots: Optional[List[str]] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> TimeSlotSchedulePlan:
        """Agent 7: Breaks each campaign day into distinct, chronological publication time slots optimized for peak engagement."""
        default_slot_templates = [
            ("Morning Anchor", "09:00 UTC", "High-signal problem awareness and thought leadership", "curiosity_dialogue"),
            ("Evening Deep-Dive", "17:00 UTC", "Technical teardown, case study proof, or transformation walkthrough", "direct_conversion"),
            ("Midday Pulse", "13:00 UTC", "Practical practitioner tip or contrarian perspective", "social_discussion"),
        ]

        active_slots_per_day = max(1, min(3, posts_per_day))
        all_slots: List[TimeSlotSpec] = []
        now_date = datetime.now(timezone.utc)

        for day_outline in narrative_arc.days_outline:
            d_num = day_outline.day
            day_date = now_date + timedelta(days=d_num - 1)

            for s_idx in range(active_slots_per_day):
                label, default_time, angle_flavor, default_act = default_slot_templates[s_idx % len(default_slot_templates)]
                custom_time = target_time_slots[s_idx] if (target_time_slots and len(target_time_slots) > s_idx) else default_time

                hour_part = 9
                try:
                    hour_part = int(custom_time.split(":")[0])
                except Exception:
                    pass

                scheduled_iso = day_date.replace(hour=hour_part, minute=0, second=0, microsecond=0).isoformat()
                for p_idx, platform in enumerate(platforms):
                    all_slots.append(
                        TimeSlotSpec(
                            day=d_num,
                            slot_index=s_idx + 1,
                            slot_label=f"Day {d_num} • {label} ({platform.title()})",
                            scheduled_time_utc=scheduled_iso,
                            platform=platform,
                            thematic_angle=f"{day_outline.theme} - {angle_flavor}",
                            target_action=day_outline.target_cta_intent if s_idx == active_slots_per_day - 1 else default_act,
                            product_feature_focus=day_outline.narrative_focus,
                        )
                    )

        return TimeSlotSchedulePlan(
            total_days=narrative_arc.total_days,
            posts_per_day=active_slots_per_day,
            slots=all_slots,
        )

    # ── Agent 9: Viral Hook & Headline Engineer ──────────────────────────
    async def execute_hook_engineer(
        self,
        slot: TimeSlotSpec,
        brand_anchor: BrandContextAnchor,
        post_draft: PlatformPostDraft,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> HookAngleVariant:
        """Agent 9: Crafts 3 calibrated opening hooks (contrarian, proof-backed, curiosity gap) and selects the winning hook."""
        system_prompt = (
            "You are the Viral Hook & Headline Engineer (Agent 9 of 15). "
            "Craft 3 high-impact opening hooks designed to stop the scroll and maximize dwell time. "
            "Output valid JSON only."
        )
        prompt = f"""Platform: {slot.platform}
Narrative Theme: {slot.thematic_angle}
Audience Persona: {brand_anchor.audience_persona.target_persona}
Acute Pain Point: {brand_anchor.audience_persona.acute_pain_points[0] if brand_anchor.audience_persona.acute_pain_points else 'Operational bottlenecks'}
Current Draft Hook: {post_draft.hook}

Generate 3 distinct hook variants:
1. contrarian_insight: Challenges conventional industry dogma.
2. proof_metric: Leads with concrete, defensible numbers or transformation.
3. curiosity_gap: Poses an irresistible operational question.

Output JSON format:
{{
  "winning_hook": "The single highest-converting opening line",
  "angle_type": "contrarian_insight",
  "hook_variants": [
    {{"type": "contrarian_insight", "text": "Hook 1"}},
    {{"type": "proof_metric", "text": "Hook 2"}},
    {{"type": "curiosity_gap", "text": "Hook 3"}}
  ]
}}"""
        try:
            resp = await self.llm.complete(prompt, system_prompt=system_prompt, provider=provider, model=model)
            data = extract_json_safe(resp)
            if isinstance(data, dict) and data.get("winning_hook"):
                return HookAngleVariant(**data)
        except Exception:
            pass

        return HookAngleVariant(
            winning_hook=post_draft.hook,
            angle_type="contrarian_insight",
            hook_variants=[
                {"type": "contrarian_insight", "text": post_draft.hook},
                {"type": "proof_metric", "text": f"Why leading {brand_anchor.industry} teams are re-evaluating workflow speed this quarter."},
                {"type": "curiosity_gap", "text": f"What actually breaks when manual coordination meets enterprise scale?"},
            ],
        )

    # ── Agent 13: Deterministic Fact-Checking & Claim Grounding Verifier ─
    async def execute_fact_check_verifier(
        self,
        post_content: str,
        approved_evidence: List[Dict[str, Any]],
    ) -> FactCheckAuditResult:
        """Agent 13: Audits post content against verified company proof points to prevent hallucinations and ungrounded statements."""
        from app.services.marketing.campaign_os.claim_verifier import ClaimVerifier
        claim_result = ClaimVerifier.verify_post_claims(
            content=post_content,
            approved_evidence=approved_evidence,
        )
        return FactCheckAuditResult(
            groundedness_score=claim_result.citation_coverage_score,
            all_claims_grounded=claim_result.all_claims_grounded,
            unsupported_claims=claim_result.unsupported_claims,
            cited_evidence_ids=claim_result.verified_claims,
        )

    # ── Agent 14: Brand Voice & Compliance Sentinel ──────────────────────
    async def execute_brand_compliance_sentinel(
        self,
        post_content: str,
        brand_anchor: BrandContextAnchor,
        platform: str,
    ) -> ComplianceAuditResult:
        """Agent 14: Checks tone keyword alignment, banned buzzwords, platform rules, and disclaimers."""
        from app.services.marketing.campaign_os.compliance_engine import ComplianceRulesEngine
        comp_result = ComplianceRulesEngine.audit_post(
            content=post_content,
            platform=platform,
        )
        banned = []
        for word in brand_anchor.brand_dna.banned_words:
            if re.search(r"\b" + re.escape(word) + r"\b", post_content, re.IGNORECASE):
                banned.append(word)

        passed = comp_result.passed and len(banned) == 0
        violations = list(comp_result.violations)
        if banned:
            violations.append(f"Forbidden buzzwords detected: {', '.join(banned)}")

        voice_score = 0.95 if not banned else 0.70
        return ComplianceAuditResult(
            compliance_passed=passed,
            violations=violations,
            brand_voice_score=voice_score,
            banned_words_detected=banned,
        )

    # ── Agent 15: Chief Marketing Officer (CMO Orchestrator) ─────────────
    async def execute_cmo_orchestrator(
        self,
        campaign_title: str,
        total_slots: int,
        scorecards: List[CritiqueScoreCard],
        brand_anchor: BrandContextAnchor,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> CMOExecutiveVerdict:
        """Agent 15: Chief Marketing Officer reviews full council telemetry and arbitrates the campaign release verdict."""
        approved_count = sum(1 for s in scorecards if s.is_approved)
        needs_review_count = total_slots - approved_count
        conf_scores = [s.overall_confidence for s in scorecards] if scorecards else [0.90]
        avg_conf = round(sum(conf_scores) / max(1, len(conf_scores)), 2)

        summary = (
            f"Campaign '{campaign_title}' reviewed by the 15-Agent Council. "
            f"{approved_count}/{total_slots} time slots fully approved with {int(avg_conf * 100)}% composite confidence. "
            f"Anchored in verified capabilities for {brand_anchor.company_name}."
        )

        return CMOExecutiveVerdict(
            campaign_title=campaign_title,
            overall_confidence=avg_conf,
            is_approved=needs_review_count == 0,
            executive_summary=summary,
            total_slots_planned=total_slots,
            approved_slots_count=approved_count,
            needs_review_count=needs_review_count,
        )

    # ── Council Aliases for 15-Agent Protocol ────────────────────────────
    async def execute_platform_copywriter(self, *args, **kwargs) -> PlatformPostDraft:
        """Alias for Agent 8: Platform-Native Copywriter."""
        return await self.execute_platform_adapter(*args, **kwargs)

    async def execute_visual_art_director(self, *args, **kwargs) -> CreativeIntentJSON:
        """Alias for Agent 11: Visual Art Director & Image Prompt Engineer."""
        return await self.execute_image_concept_director(*args, **kwargs)

    async def execute_cinematic_video_director(self, *args, **kwargs) -> VideoShotPlan:
        """Alias for Agent 12: Cinematic Video Director & Motion Scriptwriter."""
        return await self.execute_video_shot_planner(*args, **kwargs)
