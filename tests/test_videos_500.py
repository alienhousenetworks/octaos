import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.api import deps
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base, Tenant

from app.models.teams import AITeam, InstalledApp, AgentMetric
from app.models.agents import ActivityLog, KnowledgeDocument
from app.models.verticals import ContentPost, Lead, Candidate, Contract, Transaction, Ticket, TicketMessage, AgentMeeting, BusinessProfile
from app.models.workflows import Workflow, WorkflowTask
from app.models.video import VideoProject, VideoAsset, VideoRender

from sqlalchemy.pool import StaticPool
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Base.metadata.create_all(bind=engine)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Seed test tenant
with TestingSessionLocal() as s:
    if not s.query(Tenant).filter_by(id="test_tenant_id").first():
        s.add(Tenant(id="test_tenant_id", name="Test Tenant", is_active=True))
        s.commit()

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def override_get_current_tenant_id():
    return "test_tenant_id"

app.dependency_overrides[deps.get_db] = override_get_db
app.dependency_overrides[deps.get_current_tenant_id] = override_get_current_tenant_id

client = TestClient(app)

response = client.post("/api/v1/videos/create", json={"prompt": "Make me a video", "title": "Test Video"})
print("CREATE Status:", response.status_code)
print("CREATE Response:", response.text)

response = client.get("/api/v1/videos/")
print("GET ALL Status:", response.status_code)
print("GET ALL Response:", response.text)

