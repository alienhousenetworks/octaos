"""Dynamic Creative Director (Stage 3 & 4 of Universal Visual Creation).

Assembles specialist reasoning lenses (photographer, painter, DP, colorist, retoucher, social creator)
and synthesizes their craft recommendations into a cohesive CreativeBrief.
"""
from typing import List, Dict, Any, Optional
from app.services.marketing.visual_creative.contracts import (
    VisualIntentInputContract,
    CreativeBrief,
    CreativeSpecialist,
)


class DynamicCreativeDirector:
    """Orchestrates specialist lenses and produces a unified professional Creative Brief."""

    @classmethod
    def assemble_specialists(cls, intent: VisualIntentInputContract) -> List[CreativeSpecialist]:
        """Dynamically selects only the creative specialists relevant to this deliverable."""
        lowered = f"{intent.subject} {' '.join(intent.style_direction)}".lower()
        deliverable = intent.deliverable

        specialists: List[CreativeSpecialist] = []

        if deliverable in ("video", "reel", "short"):
            if "ugc" in lowered or "tiktok" in lowered or "creator" in lowered or "influencer" in lowered:
                specialists.append(CreativeSpecialist(
                    role_id="social_creator",
                    role_name="Social Creator Strategist",
                    discipline="Creator content & audience retention",
                    key_recommendation="Vertical 9:16 framing, immediate 1.5s hook, natural relatable smartphone delivery."
                ))
                specialists.append(CreativeSpecialist(
                    role_id="social_editor",
                    role_name="Social Video Editor",
                    discipline="Pacing & platform native formatting",
                    key_recommendation="Punchy jump-cuts, clear safe-area for captions, authentic audio ambience."
                ))
            else:
                specialists.append(CreativeSpecialist(
                    role_id="film_director",
                    role_name="Cinematic Film Director",
                    discipline="Visual storytelling & narrative arc",
                    key_recommendation="Single coherent action beat, deliberate cinematic pacing, establish clear emotional hook."
                ))
                specialists.append(CreativeSpecialist(
                    role_id="cinematographer",
                    role_name="Director of Photography (DP)",
                    discipline="Camera kinetics & lens language",
                    key_recommendation="Smooth motivated dolly or crane glide at 24fps, shallow depth of field, anamorphic bokeh."
                ))
                specialists.append(CreativeSpecialist(
                    role_id="colorist",
                    role_name="Senior Film Colorist",
                    discipline="Color grading & tone curve",
                    key_recommendation="Subtle film stock emulation (Kodak 5219), rich shadow rolloff, natural skin tones."
                ))
            return specialists

        # Image Deliverable Specialists
        if any(w in lowered for w in ["painting", "watercolor", "oil painting", "illustration", "sketch", "canvas"]):
            specialists.append(CreativeSpecialist(
                role_id="fine_artist",
                role_name="Master Artist & Visual Designer",
                discipline="Fine art painting & drawing craft",
                key_recommendation="Emphasize visible tactile impasto brushwork, edge control, and organic pigment behavior."
            ))
            specialists.append(CreativeSpecialist(
                role_id="color_theorist",
                role_name="Color Theorist & Compositionist",
                discipline="Palette harmony & negative space",
                key_recommendation="Curated complementary palette with harmonious tonal temperature contrast."
            ))
        elif any(w in lowered for w in ["poster", "cover", "typography", "magazine", "layout", "text"]):
            specialists.append(CreativeSpecialist(
                role_id="brand_art_director",
                role_name="Brand Identity Art Director",
                discipline="Commercial graphic layout & typography",
                key_recommendation="Uncompromising typographic hierarchy, Swiss grid alignment, clean negative space."
            ))
            specialists.append(CreativeSpecialist(
                role_id="typographer",
                role_name="Typographic Designer",
                discipline="Letterform clarity & margin safety",
                key_recommendation="Pristine letter kerning, high contrast legibility against backdrops, zero glyph warping."
            ))
        else:
            # Commercial / Editorial Photography (Default)
            specialists.append(CreativeSpecialist(
                role_id="commercial_photographer",
                role_name="Commercial Product & Editorial Photographer",
                discipline="Subject staging & lens optics",
                key_recommendation="Shot on Hasselblad H6D-100c with 85mm prime lens, clean geometric perspective, macro micro-textures."
            ))
            specialists.append(CreativeSpecialist(
                role_id="lighting_director",
                role_name="Studio Lighting Director",
                discipline="Illumination architecture & shadow physics",
                key_recommendation="Soft diffused key light from 45 degrees, gentle rim light separating subject from backdrop, realistic reflections."
            ))
            specialists.append(CreativeSpecialist(
                role_id="commercial_retoucher",
                role_name="Senior Commercial Retoucher",
                discipline="Material truth & artifact control",
                key_recommendation="Authentic material refraction, preserve natural surface micro-pores, eliminate artificial AI gloss."
            ))

        return specialists

    @classmethod
    def create_brief(
        cls,
        intent: VisualIntentInputContract,
        specialists: Optional[List[CreativeSpecialist]] = None,
    ) -> CreativeBrief:
        """Synthesize specialist guidance into an authoritative, actionable Creative Brief."""
        team = specialists or cls.assemble_specialists(intent)
        specialist_names = [s.role_name for s in team]

        # Extract brand or default colors
        palette = list(intent.brand_constraints.get("color_accents", []))
        if not palette and intent.brand_constraints.get("primary_color"):
            palette.append(intent.brand_constraints["primary_color"])
            if intent.brand_constraints.get("secondary_color"):
                palette.append(intent.brand_constraints["secondary_color"])
        if not palette:
            palette = ["#0F172A", "#38BDF8", "#F8FAFC"]

        # Camera & Lighting defaults informed by specialists
        has_video = intent.deliverable in ("video", "reel", "short")
        is_fine_art = any("Artist" in s.role_name for s in team)
        is_poster = any("Typographic" in s.role_name or "Brand" in s.role_name for s in team)

        if has_video:
            concept = f"Cinematic {intent.aspect_ratio} visual narrative depicting {intent.subject} with intentional temporal coherence."
            composition = "Dynamic rule of thirds with leading lines guiding gaze"
            camera_view = "Slow cinematic dolly glide on 35mm prime lens at 24fps"
            lighting = "Atmospheric motivated key light with subtle natural fill"
            materials = "Physically plausible motion dynamics and seamless temporal continuity"
        elif is_fine_art:
            concept = f"Tactile fine art composition of {intent.subject} emphasizing authentic medium craft."
            composition = "Harmonious golden ratio with deliberate edge softening"
            camera_view = "Frontal eye-level canvas presentation"
            lighting = "Classic directional chiaroscuro lighting"
            materials = "Viscous oil pigment, rich textured canvas weave, authentic brush stroke impasto"
        elif is_poster:
            concept = f"Editorial graphic design poster featuring {intent.subject} with disciplined typography."
            composition = "Swiss minimalist grid with 40% clean negative space for headline typography"
            camera_view = "Studio frontal architectural alignment"
            lighting = "Even diffused commercial studio illumination"
            materials = "Matte coated editorial stock, sharp vector outlines, clean print finishes"
        else:
            concept = f"High-end commercial editorial centerpiece capturing {intent.subject}."
            composition = "Hero product center stage with intentional negative space for copy"
            camera_view = "85mm prime commercial lens at f/2.8, eye-level medium shot"
            lighting = "Soft overhead diffuse key lighting with subtle edge rim light and true physical reflections"
            materials = "Subsurface scattering, authentic material roughness, tactile micro-textures"

        # Build prompt blueprint
        blueprint_parts = [
            f"{camera_view} capturing {intent.subject}",
            f"set within a {intent.emotion} environment",
            f"composition: {composition}",
            f"lighting: {lighting}",
            f"color palette: {', '.join(palette)}",
            f"materials & craft: {materials}",
            f"Zero artificial AI smoothing, authentic tactile realism."
        ]
        prompt_blueprint = ", ".join([p for p in blueprint_parts if p])

        return CreativeBrief(
            concept=concept,
            focal_subject=intent.subject,
            visual_hierarchy=f"Focal subject '{intent.subject}' dominant; environment secondary",
            composition=composition,
            camera_viewpoint=camera_view,
            lighting_setup=lighting,
            color_palette=palette,
            materials_and_surfaces=materials,
            emotional_mood=intent.emotion,
            selected_specialists=specialist_names,
            positive_prompt_blueprint=prompt_blueprint,
            negative_constraints=intent.must_avoid,
            delivery_specs={
                "aspect_ratio": intent.aspect_ratio,
                "deliverable": intent.deliverable,
                "duration_seconds": intent.duration_seconds,
                "platform": intent.platform,
            }
        )
