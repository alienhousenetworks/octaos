import pytest
import asgiref.sync
import asyncio
from concurrent.futures import ThreadPoolExecutor

_original_async_to_sync = asgiref.sync.async_to_sync

def custom_async_to_sync(async_fn):
    class SafeAsyncToSync:
        def __init__(self, fn):
            self.fn = fn
        def __call__(self, *args, **kwargs):
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                coro = self.fn(*args, **kwargs)
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(asyncio.run, coro)
                    return future.result()
            else:
                return _original_async_to_sync(self.fn)(*args, **kwargs)
    return SafeAsyncToSync(async_fn)

asgiref.sync.async_to_sync = custom_async_to_sync

try:
    import app.worker.tasks
    app.worker.tasks.async_to_sync = custom_async_to_sync
except ImportError:
    pass

try:
    import app.services.notifications.sales_alerts
    app.services.notifications.sales_alerts.async_to_sync = custom_async_to_sync
except ImportError:
    pass

try:
    import app.services.social.publish_helpers
    app.services.social.publish_helpers.async_to_sync = custom_async_to_sync
except ImportError:
    pass

try:
    import app.api.v1.endpoints.marketing
    app.api.v1.endpoints.marketing.async_to_sync = custom_async_to_sync
except ImportError:
    pass

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.session import SessionLocal
from app.models.base import Base, APICredential
from app.models.verticals import Lead
from app.api.deps import get_db, get_current_tenant_id
import uuid
import json
from unittest.mock import patch, AsyncMock

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# To allow headers to dictate tenant_id in tests
tenant_id_override_store = {"tenant_id": None}

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
            
    def override_get_current_tenant_id():
        return tenant_id_override_store["tenant_id"] or "test-tenant-id"
        
    def override_get_current_user():
        from app.models.base import User
        return User(
            id="test-user-id",
            email="test@example.com",
            name="Test Human Agent",
            tenant_id=tenant_id_override_store["tenant_id"] or "test-tenant-id",
            role="admin",
            is_verified=True,
            is_active=True
        )

    from app.api.deps import get_current_user
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_tenant_id] = override_get_current_tenant_id
    app.dependency_overrides[get_current_user] = override_get_current_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to OctaOS API"}

def test_create_tenant(client):
    subdomain = f"test-{uuid.uuid4()}"
    response = client.post("/api/v1/tenants/", json={"name": "Test Co", "subdomain": subdomain})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Co"
    assert "id" in data

def test_create_lead(client):
    subdomain = f"test-{uuid.uuid4()}"
    tenant_response = client.post("/api/v1/tenants/", json={"name": "Test Co", "subdomain": subdomain})
    tenant_id = tenant_response.json()["id"]
    
    tenant_id_override_store["tenant_id"] = tenant_id
    
    response = client.post(
        "/api/v1/leads/",
        json={"name": "John Doe", "email": "john@example.com", "company": "Doe Inc", "source": "Google Maps"},
        headers={"X-Tenant-ID": tenant_id}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "John Doe"
    assert data["tenant_id"] == tenant_id

@pytest.mark.asyncio
@patch("app.services.llm_gateway.LLMGateway.complete")
async def test_sales_and_orchestrator_flow(mock_complete, client, db):
    import os
    os.environ["ALLOW_SALES_REPLY_SIMULATION"] = "true"
    # Setup tenant and credentials
    subdomain = f"test-{uuid.uuid4()}"
    tenant_resp = client.post("/api/v1/tenants/", json={"name": "Test Co", "subdomain": subdomain})
    tenant_id = tenant_resp.json()["id"]
    tenant_id_override_store["tenant_id"] = tenant_id

    # Add Anthropic Primary Key
    cred_ai = APICredential(tenant_id=tenant_id, provider="anthropic", encrypted_key="sk-ant-test-key")
    db.add(cred_ai)
    db.commit()

    # Define mock complete return values:
    # 1. Orchestrator planning response
    # 2. Sales lead generation response (JSON array of leads)
    # 3. Outreach email subject/body
    # 4. Meeting simulation interested response
    orchestrator_plan = {
        "tasks": [
            {
                "department": "Sales",
                "action": "generate_leads",
                "parameters": {"provider": "apollo", "query": "Bakeries in Boston", "count": 2}
            },
            {
                "department": "Sales",
                "action": "sales_outreach",
                "parameters": {"channel": "smtp", "subject": "Sweet Deal", "body_template": "Hello {name} from {company}"}
            },
            {
                "department": "Sales",
                "action": "schedule_meeting",
                "parameters": {"tool": "google_calendar", "count": 1}
            }
        ]
    }
    
    simulated_leads = [
        {"name": "Alice Baker", "email": "alice@bostonbakes.com", "phone": "+1-555-888-9999", "company": "Boston Bakes"},
        {"name": "Charlie Crust", "email": "charlie@crusty.com", "phone": "+1-555-777-6666", "company": "Crusty Loaves"}
    ]
    
    outreach_response = {
        "subject": "Collab with Boston Bakes",
        "body": "Hello Alice, let's chat about growing Crusty Loaves..."
    }
    
    meeting_response = {
        "interested": True,
        "reply_message": "Yes, let's meet on Friday at 2:00 PM EST.",
        "suggested_time": "Friday at 2:00 PM EST"
    }

    # Setup the mock to return these values in sequence
    mock_complete.side_effect = [
        json.dumps(orchestrator_plan), # Orchestrator plan
        json.dumps(simulated_leads),    # Lead gen
        json.dumps(outreach_response),  # Outreach 1
        json.dumps(outreach_response)   # Outreach 2
    ]

    # Execute the Orchestrator execute endpoint
    with patch("app.services.agents.sales.SalesAgent._fetch_real_leads", new_callable=AsyncMock) as mock_fetch, \
         patch("app.services.agents.sales.send_smtp_email") as mock_smtp, \
         patch("app.services.agents.sales.book_meeting_for_lead") as mock_book:
        mock_fetch.return_value = simulated_leads
        mock_smtp.return_value = True
        mock_book.return_value = True
        
        # Add dummy credentials so auth checks pass
        cred_apollo = APICredential(tenant_id=tenant_id, provider="apollo", encrypted_key="sk-apollo-test-key")
        cred_smtp = APICredential(tenant_id=tenant_id, provider="smtp", encrypted_key="smtp://user:pass@host:25")
        cred_google = APICredential(tenant_id=tenant_id, provider="google_calendar", encrypted_key="fake_google_token")
        db.add_all([cred_apollo, cred_smtp, cred_google])
        db.commit()

        resp = client.post("/api/v1/commands/execute", json={"prompt": "Find 2 Boston bakeries using free sources, email them, and fix a meeting."})
    if resp.status_code != 200:
        print("FAIL DETAIL:", resp.json())
    assert resp.status_code == 200
    data = resp.json()
    assert "plan" in data
    assert len(data["plan"]["tasks"]) == 3
    
    # Check that leads were added to DB
    leads = db.query(Lead).filter(Lead.tenant_id == tenant_id).all()
    assert len(leads) == 2
    assert leads[0].name == "Alice Baker"
    assert leads[1].name == "Charlie Crust"
    
    # Check status was updated to contacted (awaiting real reply)
    assert leads[0].status == "contacted"
    assert leads[1].status == "contacted"

@pytest.mark.asyncio
@patch("app.services.llm_gateway.LLMGateway.complete")
async def test_hr_agent_flow(mock_complete, client, db):
    from app.models.verticals import Candidate
    
    # Setup tenant and credentials
    subdomain = f"test-{uuid.uuid4()}"
    tenant_resp = client.post("/api/v1/tenants/", json={"name": "Acme HR Co", "subdomain": subdomain})
    tenant_id = tenant_resp.json()["id"]
    tenant_id_override_store["tenant_id"] = tenant_id

    # Configure anthropic credential
    cred_ai = APICredential(tenant_id=tenant_id, provider="anthropic", encrypted_key="sk-ant-test-key")
    db.add(cred_ai)
    db.commit()

    # Define LLM mock responses
    # 1. Sourcing response: 2 realistic candidate profiles
    simulated_candidates = [
        {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "skills": ["React", "TypeScript"],
            "experience_summary": "5 years frontend development",
            "match_score": 90,
            "requirements_match": "Matches core requirements",
            "salary_expectation": "$120,000/year"
        },
        {
            "name": "Bob Smith",
            "email": "bob@example.com",
            "skills": ["Python", "FastAPI"],
            "experience_summary": "3 years backend development",
            "match_score": 85,
            "requirements_match": "Solid backend skills",
            "salary_expectation": "$100,000/year"
        }
    ]
    
    outreach_response = {
        "subject": "Opportunity: Frontend Developer",
        "body": "Hello Jane, you look like a great fit!"
    }
    
    interview_response = {
        "interested": True,
        "reply_message": "Yes, let's chat next Monday at 10 AM.",
        "suggested_time": "next Monday at 10 AM"
    }

    mock_complete.side_effect = [
        json.dumps(simulated_candidates),
        json.dumps(outreach_response),
        json.dumps(interview_response)
    ]

    # 1. Test Candidate Sourcing Endpoint
    source_resp = client.post(
        "/api/v1/hr/source",
        json={"role": "Frontend Developer", "requirements": "React, TypeScript", "salary": "$120,000/year", "count": 2, "platforms": ["linkedin"]}
    )
    assert source_resp.status_code == 200
    assert source_resp.json()["sourced_count"] == 2

    # Verify candidates are added to DB
    candidates = db.query(Candidate).filter(Candidate.tenant_id == tenant_id).all()
    assert len(candidates) == 2
    assert candidates[0].name == "Jane Doe"
    assert candidates[0].status == "sourced"
    
    # 2. Test Read Candidates Endpoint
    read_resp = client.get("/api/v1/hr/")
    assert read_resp.status_code == 200
    assert len(read_resp.json()) == 2

    # Get a specific candidate's ID
    jane_cand = [c for c in candidates if c.name == "Jane Doe"][0]

    # 3. Test Candidate Outreach Endpoint
    outreach_resp = client.post(
        f"/api/v1/hr/{jane_cand.id}/outreach",
        json={"channel": "free_outreach", "subject": "Opportunity: {role}", "body_template": "Hi {name}"}
    )
    assert outreach_resp.status_code == 200
    assert outreach_resp.json()["sent_count"] == 1
    
    # Refresh candidate status
    db.refresh(jane_cand)
    assert jane_cand.status == "screened"
    assert jane_cand.scorecard["outreach_channel"] == "free_outreach"

    # 4. Test Schedule Interview Endpoint
    interview_resp = client.post(
        f"/api/v1/hr/{jane_cand.id}/interview",
        json={"tool": "free_scheduling"}
    )
    assert interview_resp.status_code == 200
    assert interview_resp.json()["booked_interviews"] == 1
    
    db.refresh(jane_cand)
    assert jane_cand.status == "interviewed"
    assert jane_cand.scorecard["meeting_time"] == "next Monday at 10 AM"
    assert "meeting_link" in jane_cand.scorecard

    # 5. Test Orchestrator flow for HR Sourcing & Hiring
    orchestrator_plan = {
        "tasks": [
            {
                "department": "HR",
                "action": "source_candidates",
                "parameters": {"role": "Python Backend Engineer", "requirements": "Python, FastAPI", "salary": "$110k/yr", "count": 1}
            }
        ]
    }
    
    # Sequence: Orchestrator plan, then sourcing list
    mock_complete.side_effect = [
        json.dumps(orchestrator_plan),
        json.dumps([{
            "name": "Alice Pythonist",
            "email": "alice@pythonist.com",
            "skills": ["Python", "FastAPI"],
            "experience_summary": "4 years writing APIs",
            "match_score": 92,
            "requirements_match": "Excellent fit",
            "salary_expectation": "$110k/yr"
        }])
    ]
    
    orch_resp = client.post(
        "/api/v1/commands/execute",
        json={"prompt": "Find a Python Backend Engineer with budget $110k/yr"}
    )
    assert orch_resp.status_code == 200
    assert len(orch_resp.json()["plan"]["tasks"]) == 1
    
    # Check that candidates total is now 3
    total_candidates = db.query(Candidate).filter(Candidate.tenant_id == tenant_id).all()
    assert len(total_candidates) == 3
    alice_cand = [c for c in total_candidates if c.name == "Alice Pythonist"][0]
    assert alice_cand.role == "Python Backend Engineer"
    assert alice_cand.status == "sourced"

def test_marketplace_install_and_uninstall(client, db):
    from app.models.teams import InstalledApp
    
    subdomain = f"test-{uuid.uuid4()}"
    tenant_resp = client.post("/api/v1/tenants/", json={"name": "Test Co", "subdomain": subdomain})
    tenant_id = tenant_resp.json()["id"]
    tenant_id_override_store["tenant_id"] = tenant_id

    # 1. Verify initially no apps are installed
    installed_resp = client.get("/api/v1/dashboard/marketplace/installed")
    assert installed_resp.status_code == 200
    assert len(installed_resp.json()) == 0

    # 2. Install a pack
    install_resp = client.post(
        "/api/v1/dashboard/marketplace/install",
        json={"app_name": "SaaS Outreach System", "config": {}}
    )
    assert install_resp.status_code == 200
    assert install_resp.json() == {"message": "SaaS Outreach System installed successfully"}

    # 3. Verify it is listed in installed
    installed_resp = client.get("/api/v1/dashboard/marketplace/installed")
    assert installed_resp.status_code == 200
    installed_apps = installed_resp.json()
    assert len(installed_apps) == 1
    assert installed_apps[0]["app_name"] == "SaaS Outreach System"

    # 4. Uninstall the pack
    uninstall_resp = client.post(
        "/api/v1/dashboard/marketplace/uninstall",
        json={"app_name": "SaaS Outreach System"}
    )
    assert uninstall_resp.status_code == 200
    assert uninstall_resp.json() == {"message": "SaaS Outreach System uninstalled successfully"}

    # 5. Verify it is no longer listed
    installed_resp = client.get("/api/v1/dashboard/marketplace/installed")
    assert installed_resp.status_code == 200
    assert len(installed_resp.json()) == 0


def test_manual_post_and_media_upload(client, db):
    from app.models.verticals import ContentPost
    
    subdomain = f"test-{uuid.uuid4()}"
    tenant_resp = client.post("/api/v1/tenants/", json={"name": "Test Co", "subdomain": subdomain})
    tenant_id = tenant_resp.json()["id"]
    tenant_id_override_store["tenant_id"] = tenant_id

    # 1. Test media upload endpoint
    upload_resp = client.post(
        "/api/v1/marketing/upload-media",
        files={"file": ("test.jpg", b"fake-image-bytes", "image/jpeg")}
    )
    assert upload_resp.status_code == 200
    upload_data = upload_resp.json()
    assert "url" in upload_data
    assert "/media/upload_" in upload_data["url"]

    # 2. Test manual post creation endpoint
    create_resp = client.post(
        "/api/v1/marketing/posts/create",
        json={
            "platform": "linkedin",
            "content": "Manually created post content",
            "image_url": upload_data["url"],
            "image_prompt": "Prompt for image",
            "image_prompt_enabled": True,
            "video_prompt": "Prompt for video",
            "video_prompt_enabled": False,
            "is_manual_media": True,
            "day": 5
        }
    )
    assert create_resp.status_code == 200
    post_data = create_resp.json()
    assert post_data["content"] == "Manually created post content"
    assert post_data["platform"] == "linkedin"
    assert post_data["image_url"] == upload_data["url"]
    assert post_data["image_prompt"] == "Prompt for image"
    assert post_data["image_prompt_enabled"] is True
    assert post_data["video_prompt"] == "Prompt for video"
    assert post_data["video_prompt_enabled"] is False
    assert post_data["is_manual_media"] is True
    assert post_data["day"] == 5

    # 3. Test post update endpoint
    update_resp = client.put(
        f"/api/v1/marketing/posts/{post_data['id']}",
        json={
            "platform": "linkedin",
            "content": "Updated post content",
            "image_url": post_data["image_url"],
            "video_url": "http://localhost:8000/media/some_video.mp4",
            "image_prompt": "Updated image prompt",
            "image_prompt_enabled": False,
            "video_prompt": "Updated video prompt",
            "video_prompt_enabled": True,
            "is_manual_media": True,
            "day": 5
        }
    )
    assert update_resp.status_code == 200
    updated_post = db.query(ContentPost).filter(ContentPost.id == post_data["id"]).first()
    assert updated_post.content == "Updated post content"
    assert updated_post.video_url == "http://localhost:8000/media/some_video.mp4"
    assert updated_post.image_prompt == "Updated image prompt"
    assert updated_post.image_prompt_enabled is False
    assert updated_post.video_prompt == "Updated video prompt"
    assert updated_post.video_prompt_enabled is True
    assert updated_post.is_manual_media is True

    # 4. Test custom scheduled_at on creation and approval preservation
    custom_scheduled_str = "2026-06-10T12:00:00Z"
    custom_create_resp = client.post(
        "/api/v1/marketing/posts/create",
        json={
            "platform": "instagram",
            "content": "Custom scheduled post",
            "scheduled_at": custom_scheduled_str,
            "day": 1
        }
    )
    assert custom_create_resp.status_code == 200
    custom_post_data = custom_create_resp.json()
    assert custom_post_data["scheduled_at"].startswith("2026-06-10T12:00:00")

    # Approve this post and check that custom scheduled_at is preserved
    approve_resp = client.post(f"/api/v1/marketing/posts/{custom_post_data['id']}/approve")
    assert approve_resp.status_code == 200
    approved_custom_post = approve_resp.json()
    assert approved_custom_post["scheduled_at"].startswith("2026-06-10T12:00:00")

    # Delete all other draft/pending posts to make bulk schedule testing deterministic
    db.query(ContentPost).filter(ContentPost.id != custom_post_data["id"]).delete()
    db.commit()

    # Create two more draft posts (to make a total of 3 posts: one approved, two drafts)
    post2_resp = client.post(
        "/api/v1/marketing/posts/create",
        json={
            "platform": "facebook",
            "content": "Draft post 2",
            "day": 2
        }
    )
    post3_resp = client.post(
        "/api/v1/marketing/posts/create",
        json={
            "platform": "linkedin",
            "content": "Draft post 3",
            "day": 3
        }
    )
    assert post2_resp.status_code == 200
    assert post3_resp.status_code == 200

    # 5. Test bulk schedule endpoint
    bulk_resp = client.post(
        "/api/v1/marketing/posts/bulk-schedule",
        json={
            "start_date": "2026-06-03T00:00:00Z",
            "end_date": "2026-06-05T00:00:00Z",
            "posting_time": "10:30"
        }
    )
    assert bulk_resp.status_code == 200
    assert "Successfully bulk scheduled" in bulk_resp.json()["message"]

    # Verify that the 3 posts are scheduled exactly at 2026-06-03 10:30, 2026-06-04 10:30, and 2026-06-05 10:30 (UTC)
    posts_in_db = db.query(ContentPost).order_by(ContentPost.day.asc()).all()
    assert len(posts_in_db) == 3

    # Post 1 (Day 1)
    assert posts_in_db[0].scheduled_at.hour == 10
    assert posts_in_db[0].scheduled_at.minute == 30
    assert posts_in_db[0].scheduled_at.day == 3
    assert posts_in_db[0].approval_status == "approved"

    # Post 2 (Day 2)
    assert posts_in_db[1].scheduled_at.hour == 10
    assert posts_in_db[1].scheduled_at.minute == 30
    assert posts_in_db[1].scheduled_at.day == 4
    assert posts_in_db[1].approval_status == "approved"

    # Post 3 (Day 3)
    assert posts_in_db[2].scheduled_at.hour == 10
    assert posts_in_db[2].scheduled_at.minute == 30
    assert posts_in_db[2].scheduled_at.day == 5
    assert posts_in_db[2].approval_status == "approved"


@patch("app.services.llm_gateway.LLMGateway.complete")
def test_suggest_prompt(mock_complete, client, db):
    mock_complete.return_value = "A gorgeous sunrise over a coffee shop, modern style"

    subdomain = f"test-{uuid.uuid4()}"
    tenant_resp = client.post("/api/v1/tenants/", json={"name": "Test Co", "subdomain": subdomain})
    tenant_id = tenant_resp.json()["id"]
    tenant_id_override_store["tenant_id"] = tenant_id

    resp = client.post(
        "/api/v1/marketing/suggest-prompt",
        json={
            "content": "Start your morning with a fresh brew! #coffee",
            "media_type": "image"
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "prompt" in data
    assert data["prompt"] == "A gorgeous sunrise over a coffee shop, modern style"
    mock_complete.assert_called_once()


def test_sales_crm_endpoints(client, db):
    # 1. Setup tenant
    subdomain = f"test-{uuid.uuid4()}"
    tenant_resp = client.post("/api/v1/tenants/", json={"name": "Test Sales Co", "subdomain": subdomain})
    tenant_id = tenant_resp.json()["id"]
    tenant_id_override_store["tenant_id"] = tenant_id

    # 2. Create a lead
    create_resp = client.post(
        "/api/v1/leads/",
        json={
            "name": "Bruce Wayne", 
            "email": "bruce@waynecorp.com", 
            "company": "Wayne Enterprises", 
            "source": "manual",
            "priority": "high",
            "personal_email": "batman@gmail.com",
            "company_email": "ceo@waynecorp.com",
            "mobile_no": "123-456",
            "company_contact_no": "999-999",
            "need_of_what": "AI Defense Systems",
            "how_much": "$1M+",
            "why": "Safety",
            "target_context": "Gotham City"
        }
    )
    assert create_resp.status_code == 200
    lead_data = create_resp.json()
    lead_id = lead_data["id"]

    # 3. Read leads with filter
    read_resp = client.get(
        "/api/v1/leads/",
        params={"search": "Bruce", "priority": "high", "status": "captured"}
    )
    assert read_resp.status_code == 200
    results = read_resp.json()
    assert len(results) == 1
    assert results[0]["name"] == "Bruce Wayne"
    assert results[0]["personal_email"] == "batman@gmail.com"

    # 4. PATCH lead to change priority and personal_email
    patch_resp = client.patch(
        f"/api/v1/leads/{lead_id}",
        json={"priority": "low", "personal_email": "new_bat@gmail.com"}
    )
    assert patch_resp.status_code == 200
    patched_data = patch_resp.json()
    assert patched_data["priority"] == "low"
    assert patched_data["personal_email"] == "new_bat@gmail.com"

    # 5. POST to schedule meeting
    meet_resp = client.post(f"/api/v1/leads/{lead_id}/schedule_meeting")
    assert meet_resp.status_code == 200
    meet_data = meet_resp.json()
    assert "meeting_link" in meet_data
    assert "meeting_time" in meet_data

    # Check status changed in db
    db_lead = db.query(Lead).filter(Lead.id == lead_id).first()
    assert db_lead.status == "meeting_scheduled"


def test_leads_upload_and_note(client, db):
    # 1. Setup tenant
    subdomain = f"test-{uuid.uuid4()}"
    tenant_resp = client.post("/api/v1/tenants/", json={"name": "Test Sales Upload Co", "subdomain": subdomain})
    tenant_id = tenant_resp.json()["id"]
    tenant_id_override_store["tenant_id"] = tenant_id

    # 2. Upload CSV file
    csv_content = (
        "Name,Company,Email,Phone,Source,Priority,Personal Email,Company Email,Mobile Number,Company Contact Number,Need,Value,Pain Points,Context\n"
        "Clark Kent,Daily Planet,clark@planet.com,111-222,metro,high,clark@gmail.com,reporter@planet.com,111-222,111-222,AI Writing,$50k,Fast reporting,Metropolis\n"
    )
    
    upload_resp = client.post(
        "/api/v1/leads/upload",
        files={"file": ("leads.csv", csv_content.encode("utf-8"), "text/csv")},
        data={"handle_with_ai": "false"}
    )
    assert upload_resp.status_code == 200
    assert "Successfully uploaded" in upload_resp.json()["message"]

    # Read leads from DB to verify Clark Kent exists
    db_leads = db.query(Lead).filter(Lead.tenant_id == tenant_id).all()
    assert len(db_leads) == 1
    lead = db_leads[0]
    assert lead.name == "Clark Kent"
    assert lead.company == "Daily Planet"
    assert lead.email == "clark@planet.com"
    assert lead.personal_email == "clark@gmail.com"
    assert lead.company_email == "reporter@planet.com"
    assert lead.need_of_what == "AI Writing"
    assert lead.how_much == "$50k"
    assert lead.why == "Fast reporting"
    assert lead.target_context == "Metropolis"
    assert lead.priority == "high"

    # 3. Add timeline note (human update)
    note_resp = client.post(
        f"/api/v1/leads/{lead.id}/timeline-note",
        json={
            "content": "Followed up with Clark via phone.",
            "channel": "call",
            "direction": "outbound"
        }
    )
    assert note_resp.status_code == 200
    updated_lead = note_resp.json()
    conv = updated_lead["data"]["conversation"]
    assert len(conv) == 1
    assert conv[0]["content"] == "Followed up with Clark via phone."
    assert conv[0]["channel"] == "call"
    assert conv[0]["direction"] == "outbound"


def test_leads_upload_robustness(client, db):
    # 1. Setup tenant
    subdomain = f"test-{uuid.uuid4()}"
    tenant_resp = client.post("/api/v1/tenants/", json={"name": "Test Sales Robust Co", "subdomain": subdomain})
    tenant_id = tenant_resp.json()["id"]
    tenant_id_override_store["tenant_id"] = tenant_id

    # 2. Upload CSV file with BOM, casing/spacing header mismatches, enclosing quotes
    csv_content = (
        "\ufeff\"Name\",\"Company_Name\",\"Email Address\",\"Mobile-Number\",\"Personal_Email\",\"Need Of What\",\"how_much\",\"Pain Points\",\"Target Context\"\n"
        "\"Bruce Wayne\",\"Wayne Enterprises\",\"bruce@wayne.com\",\"222-333\",\"bruce.personal@gmail.com\",\"Batmobile Upgrade\",\"$1M\",\"Joker activity\",\"Gotham City\"\n"
    )

    upload_resp = client.post(
        "/api/v1/leads/upload",
        files={"file": ("leads_robust.csv", csv_content.encode("utf-8"), "text/csv")},
        data={"handle_with_ai": "false"}
    )
    assert upload_resp.status_code == 200
    assert "Successfully uploaded" in upload_resp.json()["message"]

    # Verify Wayne exists in DB and is mapped correctly
    db_leads = db.query(Lead).filter(Lead.tenant_id == tenant_id).all()
    assert len(db_leads) == 1
    lead = db_leads[0]
    assert lead.name == "Bruce Wayne"
    assert lead.company == "Wayne Enterprises"
    assert lead.email == "bruce@wayne.com"
    assert lead.personal_email == "bruce.personal@gmail.com"
    assert lead.need_of_what == "Batmobile Upgrade"
    assert lead.how_much == "$1M"
    assert lead.why == "Joker activity"
    assert lead.target_context == "Gotham City"


def test_knowledge_endpoints(client, db):
    subdomain = f"test-{uuid.uuid4()}"
    tenant_resp = client.post("/api/v1/tenants/", json={"name": "Test Co", "subdomain": subdomain})
    tenant_id = tenant_resp.json()["id"]
    tenant_id_override_store["tenant_id"] = tenant_id

    # Test POST /knowledge (text input)
    post_resp = client.post(
        "/api/v1/commands/knowledge",
        json={"department": "Marketing", "doc_type": "Brand Guidelines", "content": "Our brand color is violet."}
    )
    assert post_resp.status_code == 200

    # Test GET /knowledge
    get_resp = client.get("/api/v1/commands/knowledge")
    assert get_resp.status_code == 200
    docs = get_resp.json()
    assert len(docs) == 1
    assert docs[0]["department"] == "Marketing"
    assert docs[0]["content"] == "Our brand color is violet."
    doc_id = docs[0]["id"]

    # Test POST /knowledge/upload with raw text file
    txt_file_content = b"This is text file content for knowledge."
    upload_txt_resp = client.post(
        "/api/v1/commands/knowledge/upload",
        files={"file": ("guide.txt", txt_file_content, "text/plain")},
        data={"department": "Sales", "doc_type": "Pricing"}
    )
    assert upload_txt_resp.status_code == 200
    assert "Successfully parsed and added document" in upload_txt_resp.json()["message"]

    # Verify both documents exist now
    get_resp2 = client.get("/api/v1/commands/knowledge")
    docs2 = get_resp2.json()
    assert len(docs2) == 2
    sales_doc = [d for d in docs2 if d["department"] == "Sales"][0]
    assert sales_doc["content"] == "Source Document: guide.txt\n\nThis is text file content for knowledge."

    # Test DELETE /knowledge/{doc_id}
    del_resp = client.delete(f"/api/v1/commands/knowledge/{doc_id}")
    assert del_resp.status_code == 200

    # Verify one document is deleted
    get_resp3 = client.get("/api/v1/commands/knowledge")
    docs3 = get_resp3.json()
    assert len(docs3) == 1
    assert docs3[0]["id"] == sales_doc["id"]


def test_otp_auth_flows(client, db):
    from app.models.base import User
    email = "test-otp-user@example.com"
    password = "secretpassword"
    
    # 1. Initiate Signup
    signup_init_resp = client.post(
        "/api/v1/auth/signup/initiate",
        json={
            "name": "OTP Tester",
            "email": email,
            "phone_no": "+1234567890",
            "company": "OTP Test Corp",
            "company_website": "https://otptest.com",
            "company_email": "info@otptest.com",
            "company_address": "123 Test St",
            "password": password
        }
    )
    assert signup_init_resp.status_code == 200
    assert "Verification OTP sent successfully" in signup_init_resp.json()["message"]
    
    # Verify user exists but is not verified
    user_in_db = db.query(User).filter(User.email == email).first()
    assert user_in_db is not None
    assert user_in_db.is_verified is False
    assert user_in_db.otp is not None
    
    # 2. Resend Signup OTP
    resend_resp = client.post(
        "/api/v1/auth/signup/resend-otp",
        json={"email": email}
    )
    assert resend_resp.status_code == 200
    
    # 3. Verify Signup with magic OTP 123455 (in dev mode)
    verify_resp = client.post(
        "/api/v1/auth/signup/verify",
        json={"email": email, "otp": "123455"}
    )
    assert verify_resp.status_code == 200
    assert "access_token" in verify_resp.json()
    db.refresh(user_in_db)
    assert user_in_db.is_verified is True
    
    # 4. Initiate Login (OTP flow — no password triggers OTP)
    login_init_resp = client.post(
        "/api/v1/auth/login/initiate",
        json={"email": email}
    )
    assert login_init_resp.status_code == 200
    assert login_init_resp.json()["otp_required"] is True
    
    # 5. Verify Login with magic OTP
    login_verify_resp = client.post(
        "/api/v1/auth/login/verify",
        json={"email": email, "otp": "123455"}
    )
    assert login_verify_resp.status_code == 200
    assert "access_token" in login_verify_resp.json()




