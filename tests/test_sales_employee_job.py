"""Sales AI jobs must research or reuse real leads and draft, never invent a contact."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base, Tenant
from app.models.verticals import BusinessProfile, Lead
from app.services.sales.contact_quality import correct_sender_signature
from app.services.sales.employee_job import run_sales_employee_job


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Tenant(id="ahn", name="Alien House Networks"))
    session.add(BusinessProfile(
        tenant_id="ahn",
        company_name="Alien House Networks",
        website="https://alienhousenetworks.com",
    ))
    session.commit()
    yield session
    session.close()


def test_signature_uses_sender_website_instead_of_prospect_site():
    body = correct_sender_signature(
        "Hello Webenza team.\n\nhttps://webenza.com",
        prospect_hosts=["webenza.com", "info@webenza.com"],
        sender_website="https://alienhousenetworks.com",
    )
    assert "webenza.com" not in body
    assert body.endswith("https://alienhousenetworks.com")


@pytest.mark.asyncio
async def test_sales_job_drafts_existing_leads_and_skips_placeholders(db_session):
    real = Lead(
        tenant_id="ahn",
        name="Business Development",
        email="info@webenza.com",
        company="Webenza",
        status="captured",
        data={"tags": ["AHN ICP"]},
    )
    already = Lead(
        tenant_id="ahn",
        name="Marketing Collaborations",
        email="social@discoverpilgrim.com",
        company="Pilgrim",
        status="captured",
        data={"tags": ["AHN ICP"], "draft_subject": "Kept", "draft_body": "Leave this draft alone."},
    )
    placeholder = Lead(
        tenant_id="ahn",
        name="Inbound Lead",
        email="lead@example.com",
        company="Unknown Corp",
        status="captured",
    )
    db_session.add_all([real, already, placeholder])
    db_session.commit()

    async def drafter(lead, instructions):
        assert "Alien House Networks" in instructions
        return f"Hello {lead.company}.\nhttps://{lead.email.split('@')[1]}"

    async def researcher(*_args, **_kwargs):
        raise AssertionError("web research is not needed when real leads are already on file")

    result = await run_sales_employee_job(
        db_session,
        "ahn",
        task_type="outreach_draft",
        params={"tag": "AHN ICP"},
        instructions="Draft emails for the AHN ICP leads",
        drafter=drafter,
        researcher=researcher,
    )

    db_session.refresh(real)
    db_session.refresh(already)
    db_session.refresh(placeholder)
    assert result["sent"] is False
    assert result["created_count"] == 0
    assert result["drafted_count"] == 1
    assert result["skipped_existing_drafts"] == 1
    assert real.data["draft_body"].endswith("https://alienhousenetworks.com")
    assert "webenza.com" not in real.data["draft_body"]
    assert already.data["draft_body"] == "Leave this draft alone."
    assert placeholder.email == "lead@example.com"
    assert not (placeholder.data or {}).get("draft_body")
    assert db_session.query(Lead).filter(Lead.email == "lead@example.com").count() == 1


@pytest.mark.asyncio
async def test_sales_job_researches_when_no_real_lead_exists(db_session):
    async def researcher(db, tenant_id, params):
        assert params["provider"] == "web_search"
        lead = Lead(
            tenant_id=tenant_id,
            name="Aparna Tadikonda",
            email="aparna.tadikonda@interactiveavenues.com",
            company="Interactive Avenues",
            status="captured",
            source="WEB_SEARCH: agencies",
        )
        invented = Lead(
            tenant_id=tenant_id,
            name="Inbound Lead",
            email="lead@example.com",
            company="Unknown Corp",
            status="captured",
        )
        db.add_all([lead, invented])
        db.commit()
        return {"status": "success", "generated_leads": 1, "lead_ids": [lead.id, invented.id]}

    async def drafter(lead, _instructions):
        return f"Hello {lead.name} at {lead.company}."

    result = await run_sales_employee_job(
        db_session,
        "ahn",
        task_type="execute_task",
        params={},
        instructions="",
        drafter=drafter,
        researcher=researcher,
    )

    drafted = db_session.query(Lead).filter(Lead.email == "aparna.tadikonda@interactiveavenues.com").one()
    invented = db_session.query(Lead).filter(Lead.email == "lead@example.com").one()
    assert result["sent"] is False
    assert result["created_count"] == 1
    assert result["drafted_count"] == 1
    assert drafted.data["draft_body"].startswith("Hello Aparna")
    assert not (invented.data or {}).get("draft_body")


@pytest.mark.asyncio
async def test_sales_job_creates_nothing_when_research_finds_nobody(db_session):
    async def researcher(_db, _tenant_id, _params):
        return {"status": "error", "message": "No verifiable contacts.", "lead_ids": []}

    result = await run_sales_employee_job(
        db_session,
        "ahn",
        task_type="qualify_leads",
        params={},
        instructions="",
        researcher=researcher,
        drafter=lambda *_args: None,
    )
    assert result["status"] == "needs_real_contact"
    assert result["created_count"] == 0
    assert result["sent"] is False
    assert db_session.query(Lead).count() == 0
