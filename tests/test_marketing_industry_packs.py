"""Unit and Integration Tests for Industry-Wise Marketing OS."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.real_estate import RealEstateProject, RealEstateUnit
from app.models.verticals import BusinessProfile, ContentPost, Campaign
from app.services.marketing.verticals.packs import PACKS, PACK_ORDER
from app.services.marketing.verticals.registry import (
    list_marketing_packs,
    get_marketing_pack,
    resolve_marketing_pack_id,
    preview_marketing_switch,
    terminology_for,
    get_content_pillars,
    get_compliance_rules,
)
from app.services.marketing.verticals.compliance import IndustryComplianceEngine
from app.services.marketing.verticals.real_estate.project_campaign_service import (
    RealEstateMarketingService,
)


def test_all_eighteen_marketing_packs_registered():
    """Verify that all 18 marketing vertical packs are defined and distinct."""
    assert len(PACKS) == 18
    assert len(PACK_ORDER) == 18
    assert len(set(PACKS.keys())) == 18

    # Verify key representative packs
    assert PACKS["real_estate"]["representative"] is True
    assert PACKS["real_estate"]["domain_status"] == "available"
    assert PACKS["saas"]["representative"] is True

    # Check required schema keys
    for pack_id, pack in PACKS.items():
        assert pack["id"] == pack_id
        assert "terminology" in pack
        assert "funnel_stages" in pack
        assert len(pack["funnel_stages"]) >= 3
        assert "content_pillars" in pack
        assert len(pack["content_pillars"]) >= 2
        assert "compliance_guardrails" in pack
        assert "visual_creative_tokens" in pack
        assert "industry_calendar_events" in pack


def test_preview_marketing_switch_preserves_records():
    """Verify switching packs preserves all campaigns and posts with zero deletion."""
    preview = preview_marketing_switch("saas", "real_estate", campaigns_count=5, posts_count=42)
    assert preview["from_pack_id"] == "saas"
    assert preview["to_pack_id"] == "real_estate"
    assert preview["to_name"] == "Real Estate & Property Development"
    assert preview["campaigns_preserved"] == 5
    assert preview["posts_preserved"] == 42
    assert preview["records_deleted"] == 0
    assert "stay" in preview["effect"]
    assert preview["terminology"]["campaign"] == "Property Showcase & Booking Drive"


def test_industry_compliance_clean_copy():
    """Compliant copy passes with no violations."""
    clean_copy = (
        "Introducing our newest residential tower with 2BHK and 3BHK layouts. "
        "Floor plans, amenities, and connectivity specs are now available for review. "
        "RERA Reg. No: PRM/KA/RERA/1251/2026/001234. Equal Housing Opportunity. #RealEstate"
    )
    result = IndustryComplianceEngine.audit_post(clean_copy, platform="linkedin", pack_id="real_estate")
    assert result.passed is True
    assert len(result.violations) == 0


def test_industry_compliance_real_estate_fair_housing():
    """Fair Housing exclusionary keywords must trigger regulatory violations."""
    non_compliant = (
        "Exclusive 3BHK penthouse available now. No children allowed, adults only community. "
        "Guaranteed 100% appreciation in 24 months. RERA Reg No: PRM/1234."
    )
    result = IndustryComplianceEngine.audit_post(non_compliant, platform="linkedin", pack_id="real_estate")
    assert result.passed is False
    assert any("Fair Housing" in s or "children" in v or "appreciation" in v for v in result.violations for s in result.remediation_suggestions + result.violations)


def test_industry_compliance_real_estate_missing_rera_warning():
    """Promotional property copy missing RERA registration generates a compliance warning."""
    promo_copy = (
        "New launch alert! Luxury 3BHK apartments with sky terrace and infinity pool in Downtown. "
        "Bookings open this Saturday with exclusive pre-launch pricing. #LuxuryLiving"
    )
    result = IndustryComplianceEngine.audit_post(promo_copy, platform="linkedin", pack_id="real_estate")
    assert any("RERA" in w for w in result.warnings)
    assert any("RERA" in s for s in result.remediation_suggestions)


def test_industry_compliance_banking_guarantees():
    """Banking copies with guaranteed returns must be blocked."""
    banking_copy = "Deposit with our private wealth desk and get a guaranteed 20% annual return risk-free!"
    result = IndustryComplianceEngine.audit_post(banking_copy, platform="linkedin", pack_id="banking")
    assert result.passed is False
    assert len(result.violations) > 0


def test_industry_compliance_pharma_cure_claims():
    """Pharma copies promising miraculous cures must be blocked."""
    pharma_copy = "Our novel breakthrough therapy is a miracle cure that guarantees 100% recovery with zero side effects."
    result = IndustryComplianceEngine.audit_post(pharma_copy, platform="linkedin", pack_id="pharma")
    assert result.passed is False
    assert len(result.violations) > 0


@pytest.mark.asyncio
async def test_real_estate_marketing_service_grounded_generation():
    """Verify RealEstateMarketingService generates grounded campaigns from database inventory."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    tenant_id = "tenant_test_re_marketing"

    # Seed test project and unit
    project = RealEstateProject(
        id="proj_emerald_heights",
        tenant_id=tenant_id,
        name="Emerald Heights",
        code="EH-01",
        location="Indiranagar",
        city="Bengaluru",
        rera_number="PRM/KA/RERA/1251/310/PR/210101/003890",
        amenities=["Rooftop Infinity Pool", "State-of-the-art Gym", "EV Charging", "Squash Court"],
        total_units=120,
        available_units=45,
    )
    db.add(project)

    unit = RealEstateUnit(
        id="unit_b304",
        tenant_id=tenant_id,
        project_id=project.id,
        tower="Tower B",
        unit_number="B-304",
        unit_type="3BHK Luxury",
        carpet_sqft=1820.0,
        base_price=320000.0,
        status="available",
    )
    db.add(unit)
    db.commit()

    service = RealEstateMarketingService(db, tenant_id)
    projects = service.list_available_projects()
    assert len(projects) == 1
    assert projects[0]["name"] == "Emerald Heights"
    assert projects[0]["available_units"] == 1
    assert "3BHK Luxury" in projects[0]["unit_types"]

    # Generate grounded project campaign
    campaign = await service.generate_project_campaign(
        project_id=project.id,
        campaign_type="project_showcase",
        platform="linkedin",
        persist_post=True,
    )
    assert "Emerald Heights" in campaign["content"]
    assert "PRM/KA/RERA" in campaign["content"]
    assert campaign["compliance"]["passed"] is True
    assert campaign["post_id"] is not None

    # Verify persisted ContentPost in database
    post = db.query(ContentPost).filter(ContentPost.id == campaign["post_id"]).first()
    assert post is not None
    assert post.status == "draft"
    assert "Emerald Heights" in post.content

    # Generate unit spotlight campaign
    unit_campaign = await service.generate_project_campaign(
        project_id=project.id,
        campaign_type="unit_spotlight",
        unit_id=unit.id,
        platform="linkedin",
        persist_post=False,
    )
    assert "B-304" in unit_campaign["content"]
    assert "1820" in unit_campaign["content"]
    assert "$320,000" in unit_campaign["content"]

    db.close()
