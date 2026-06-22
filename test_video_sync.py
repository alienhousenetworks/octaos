import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base, Tenant
from app.models.video import VideoProject
from app.services.agents.video import VideoAgent
import logging

logging.basicConfig(level=logging.DEBUG)

engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(bind=engine)
TestingSessionLocal = sessionmaker(bind=engine)
db = TestingSessionLocal()

tenant = Tenant(id="test_tenant_id", name="Test")
db.add(tenant)
project = VideoProject(id="test_project", tenant_id="test_tenant_id", title="Test Video", prompt="Make me a cool ad about sneakers", status="planning", duration_seconds=30)
db.add(project)
db.commit()

agent = VideoAgent(db, "test_tenant_id")
result = asyncio.run(agent.plan_video("test_project"))
print("RESULT:", result)
