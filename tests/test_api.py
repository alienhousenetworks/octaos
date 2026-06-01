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
        
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_tenant_id] = override_get_current_tenant_id
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to NexusOS API"}

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
                "parameters": {"provider": "free_search", "query": "Bakeries in Boston", "count": 2}
            },
            {
                "department": "Sales",
                "action": "sales_outreach",
                "parameters": {"channel": "free_outreach", "subject": "Sweet Deal", "body_template": "Hello {name} from {company}"}
            },
            {
                "department": "Sales",
                "action": "schedule_meeting",
                "parameters": {"tool": "free_scheduling", "count": 1}
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
        json.dumps(outreach_response),  # Outreach 2
        json.dumps(meeting_response),   # Meeting reply 1
        json.dumps(meeting_response)    # Meeting reply 2
    ]

    # Execute the Orchestrator execute endpoint
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
    
    # Check status was updated through contacted to meeting_scheduled
    assert leads[0].status == "meeting_scheduled"
    assert leads[1].status == "meeting_scheduled"

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


