"""Real Estate Project Campaign Service.

Generates fact-grounded marketing campaigns directly linked to the tenant's
real estate inventory (projects, towers, units, amenities, and RERA numbers).
Zero hallucination of phantom inventory or non-existent floor plans.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.real_estate import RealEstateProject, RealEstateUnit
from app.models.verticals import ContentPost
from app.services.marketing.verticals.compliance import IndustryComplianceEngine
from app.services.marketing.verticals.registry import get_marketing_pack

logger = logging.getLogger(__name__)


class RealEstateMarketingService:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.pack = get_marketing_pack("real_estate") or {}
        from app.services.llm_gateway import LLMGateway
        self.llm = LLMGateway(db, tenant_id)

    def list_available_projects(self) -> List[Dict[str, Any]]:
        """List tenant projects with unit count, price ranges, and unit types."""
        projects = (
            self.db.query(RealEstateProject)
            .filter(RealEstateProject.tenant_id == self.tenant_id)
            .all()
        )
        result = []
        for p in projects:
            units = (
                self.db.query(RealEstateUnit)
                .filter(
                    RealEstateUnit.tenant_id == self.tenant_id,
                    RealEstateUnit.project_id == p.id,
                )
                .all()
            )
            unit_types = sorted(list({u.unit_type for u in units if u.unit_type}))
            min_price = min([u.base_price for u in units if u.base_price], default=None)
            max_price = max([u.base_price for u in units if u.base_price], default=None)
            avail_units = sum(1 for u in units if u.status == "available")

            result.append({
                "id": p.id,
                "name": p.name,
                "code": p.code,
                "location": p.location,
                "city": p.city,
                "status": p.status,
                "total_units": len(units) if units else (p.total_units or 0),
                "available_units": avail_units if units else (p.available_units or 0),
                "rera_number": p.rera_number,
                "amenities": p.amenities or [],
                "unit_types": unit_types,
                "min_price": min_price,
                "max_price": max_price,
            })
        return result

    def get_project_details(self, project_id: str) -> Optional[Dict[str, Any]]:
        p = (
            self.db.query(RealEstateProject)
            .filter(
                RealEstateProject.tenant_id == self.tenant_id,
                RealEstateProject.id == project_id,
            )
            .first()
        )
        if not p:
            return None
        units = (
            self.db.query(RealEstateUnit)
            .filter(
                RealEstateUnit.tenant_id == self.tenant_id,
                RealEstateUnit.project_id == p.id,
            )
            .all()
        )
        return {
            "id": p.id,
            "name": p.name,
            "code": p.code,
            "location": p.location,
            "city": p.city,
            "status": p.status,
            "rera_number": p.rera_number,
            "amenities": p.amenities or [],
            "units": [
                {
                    "id": u.id,
                    "tower": u.tower,
                    "unit_number": u.unit_number,
                    "unit_type": u.unit_type,
                    "carpet_sqft": u.carpet_sqft,
                    "base_price": u.base_price,
                    "status": u.status,
                }
                for u in units
            ],
        }

    async def generate_project_campaign(
        self,
        project_id: str,
        campaign_type: str = "project_showcase",
        unit_id: Optional[str] = None,
        platform: str = "linkedin",
        persist_post: bool = True,
    ) -> Dict[str, Any]:
        """Generate a grounded, RERA-compliant multi-channel campaign for a property using real inventory data and LLM generation."""
        import json
        import re

        project = (
            self.db.query(RealEstateProject)
            .filter(
                RealEstateProject.tenant_id == self.tenant_id,
                RealEstateProject.id == project_id,
            )
            .first()
        )
        if not project:
            raise KeyError(f"Project '{project_id}' not found for tenant '{self.tenant_id}'")

        unit = None
        if unit_id:
            unit = (
                self.db.query(RealEstateUnit)
                .filter(
                    RealEstateUnit.tenant_id == self.tenant_id,
                    RealEstateUnit.id == unit_id,
                    RealEstateUnit.project_id == project.id,
                )
                .first()
            )
            if unit is None:
                raise KeyError(f"Unit '{unit_id}' not found in project '{project_id}'")
        elif campaign_type == "unit_spotlight":
            unit = (
                self.db.query(RealEstateUnit)
                .filter(
                    RealEstateUnit.tenant_id == self.tenant_id,
                    RealEstateUnit.project_id == project.id,
                    RealEstateUnit.status == "available",
                )
                .order_by(RealEstateUnit.unit_number.asc())
                .first()
            )
            if unit is None:
                raise KeyError(f"No available unit found in project '{project_id}'")

        project_units = (
            self.db.query(RealEstateUnit)
            .filter(
                RealEstateUnit.tenant_id == self.tenant_id,
                RealEstateUnit.project_id == project.id,
            )
            .all()
        )

        # Grounded facts pool from database records ONLY
        loc_str = f"{project.location}, {project.city}" if project.location and project.city else (project.location or project.city or "")
        amenities = [a.strip() for a in (project.amenities or []) if a and isinstance(a, str)]
        amenities_str = ", ".join(amenities[:5]) if amenities else ""
        rera_number = project.rera_number or ""
        rera_str = f"RERA Reg. No: {rera_number}" if rera_number else ""

        unit_types = sorted(list({u.unit_type for u in project_units if u.unit_type}))
        unit_prices = [u.base_price for u in project_units if u.base_price]
        min_price = min(unit_prices) if unit_prices else None
        max_price = max(unit_prices) if unit_prices else None

        # Format real specs without fabricating phantom values
        if unit:
            tower_part = unit.tower if (unit.tower and unit.tower.lower().startswith("tower")) else (f"Tower {unit.tower}" if unit.tower else "")
            residence_desc = f"{tower_part + ', ' if tower_part else ''}Unit {unit.unit_number}"
            sqft_val = int(unit.carpet_sqft) if (unit.carpet_sqft and float(unit.carpet_sqft).is_integer()) else unit.carpet_sqft
            sqft_str = f"{sqft_val} sqft" if sqft_val else ""
            config_desc = f"{unit.unit_type}" + (f" ({sqft_str})" if sqft_str else "")
            price_desc = f"Starting at ${unit.base_price:,.0f}" if unit.base_price else ""
        else:
            config_desc = ", ".join(unit_types) if unit_types else ""
            if min_price and max_price and min_price != max_price:
                price_desc = f"Starting from ${min_price:,.0f} to ${max_price:,.0f}"
            elif min_price:
                price_desc = f"Starting from ${min_price:,.0f}"
            else:
                price_desc = ""
            residence_desc = ""

        # Visual tokens from marketing pack configuration
        visual_tokens = self.pack.get("visual_creative_tokens", {})
        visual_aesthetic = visual_tokens.get("aesthetic", "Architectural exterior photography, daylight, modern aesthetic")

        # LLM Generation with factual grounding
        hook = ""
        body = ""
        cta = ""
        image_prompt = ""

        prompt = f"""You are a professional real estate marketing copywriter. Write a fact-grounded {platform} campaign post and an architectural image generation prompt.

Grounding Facts (Do NOT invent phantom amenities, fake guarantees, or non-existent warranties):
- Project Name: {project.name}
- Location: {loc_str or 'Prime Location'}
- Address: {project.address or ''}
- Status: {project.status or 'Available'}
- Available Configurations: {config_desc or 'Multiple configurations'}
- Pricing: {price_desc or 'Contact for pricing'}
{f'- Featured Residence: {residence_desc}' if residence_desc else ''}
{f'- Verified Amenities: {amenities_str}' if amenities_str else ''}
{f'- RERA Registration: {rera_number}' if rera_number else ''}

Campaign Type: {campaign_type}
Platform: {platform}

Instructions:
1. Write a catchy opening hook sentence.
2. Write a clear, engaging post body explaining the project value using ONLY the provided facts.
3. Write a professional Call to Action (CTA) matching the campaign type (e.g. site visit tour, floor plan download, consultation).
4. Write a concise photographic image prompt for AI image generation depicting {project.name}.
5. Return JSON format with exact keys: "hook", "body", "cta", "image_prompt".
"""
        system_prompt = (
            "You are an AI real estate marketing specialist. Output valid JSON only with keys: hook, body, cta, image_prompt. "
            "Never invent false guarantees, discriminatory terms, or phantom amenities."
        )

        try:
            raw_resp = await self.llm.complete(
                prompt=prompt,
                system_prompt=system_prompt,
            )
            json_match = re.search(r"\{.*\}", raw_resp, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                hook = str(parsed.get("hook", "")).strip()
                body = str(parsed.get("body", "")).strip()
                cta = str(parsed.get("cta", "")).strip()
                image_prompt = str(parsed.get("image_prompt", "")).strip()
        except Exception as e:
            logger.warning(f"[RealEstateMarketingService] LLM campaign copy generation failed: {e}. Using deterministic fact-based composition.")

        # Fact-based fallback when LLM is unavailable or returns empty
        if not hook or not body:
            if campaign_type == "site_visit_drive":
                hook = f"VIP site visits now open at {project.name}{f' in {loc_str}' if loc_str else ''}."
                body_lines = [f"Explore residences at {project.name}."]
                if config_desc:
                    body_lines.append(f"• Configurations: {config_desc}")
                if amenities_str:
                    body_lines.append(f"• Signature Amenities: {amenities_str}")
                if price_desc:
                    body_lines.append(f"• Pricing: {price_desc}")
                body = "\n".join(body_lines)
                cta = f"Book your on-site property walkthrough at {project.name}."
            elif campaign_type == "unit_spotlight" and unit:
                hook = f"Spotlight on {unit.unit_type or 'Featured Residence'} at {project.name}."
                body_lines = [f"• Residence: {residence_desc}"]
                if config_desc:
                    body_lines.append(f"• Layout: {config_desc}")
                if price_desc:
                    body_lines.append(f"• Value: {price_desc}")
                if amenities_str:
                    body_lines.append(f"• Amenities: {amenities_str}")
                body = "\n".join(body_lines)
                cta = f"Request the full floor plan and schedule a private showing for {unit.unit_number}."
            elif campaign_type == "investor_yield":
                hook = f"Prime property investment at {project.name}{f' in {loc_str}' if loc_str else ''}."
                body_lines = [f"Capital growth and long-term asset value in {loc_str or project.name}."]
                if config_desc:
                    body_lines.append(f"• Available Configurations: {config_desc}")
                if price_desc:
                    body_lines.append(f"• Pricing: {price_desc}")
                if amenities_str:
                    body_lines.append(f"• Amenities: {amenities_str}")
                body = "\n".join(body_lines)
                cta = f"Request our investment overview for {project.name}."
            else:  # project_showcase
                hook = f"Discover modern architectural living at {project.name}{f' in {loc_str}' if loc_str else ''}."
                body_lines = [f"A premier development in {loc_str or project.name}."]
                if config_desc:
                    body_lines.append(f"• Configurations: {config_desc}")
                if amenities_str:
                    body_lines.append(f"• Amenities: {amenities_str}")
                if price_desc:
                    body_lines.append(f"• Pricing: {price_desc}")
                body = "\n".join(body_lines)
                cta = f"Schedule your consultation or explore floor plans at {project.name}."

        if not image_prompt:
            image_prompt = (
                f"Professional architectural exterior photography of {project.name}{f' in {loc_str}' if loc_str else ''}. "
                f"{visual_aesthetic}. Photorealistic 8k, crisp architectural perspective."
            )

        # Statutory RERA and Fair Housing footer
        footer_parts = []
        if rera_str:
            footer_parts.append(rera_str)
        footer_parts.append("Equal Housing Opportunity.")
        footer = f"\n\n{' | '.join(footer_parts)}"

        clean_tag = re.sub(r"[^a-zA-Z0-9]", "", project.name)
        full_content = f"{hook}\n\n{body}\n\n{cta}{footer}\n\n#RealEstate #PropertyInvestment #{clean_tag}"

        # Audit compliance
        compliance_check = IndustryComplianceEngine.audit_post(
            content=full_content,
            platform=platform,
            pack_id="real_estate",
        )

        # Persist post if requested
        post_record = None
        if persist_post:
            post_record = ContentPost(
                tenant_id=self.tenant_id,
                platform=platform,
                content=full_content,
                image_prompt=image_prompt,
                image_prompt_enabled=True,
                status="draft",
            )
            self.db.add(post_record)
            self.db.commit()
            self.db.refresh(post_record)

        return {
            "project_id": project.id,
            "project_name": project.name,
            "campaign_type": campaign_type,
            "platform": platform,
            "content": full_content,
            "image_prompt": image_prompt,
            "post_id": post_record.id if post_record else None,
            "compliance": compliance_check.model_dump(),
            "visual_tokens": visual_tokens,
        }
