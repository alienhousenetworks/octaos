from app.services.ai_gateway.routing import AIRoutingEngine
from app.api.v1.endpoints.llm import plan_ai_task, PlanTaskRequest
from unittest.mock import MagicMock

class MockAPICredential:
    def __init__(self, provider):
        self.provider = provider

# Mock dependencies
mock_db = MagicMock()
mock_db.query().filter().all.return_value = [
    MockAPICredential("gemini"),
    MockAPICredential("hunter"),
    MockAPICredential("apollo")
]

req = PlanTaskRequest(complexity="high", realtime=False, bulk=False, provider=None, model=None)
print(plan_ai_task(req=req, db=mock_db, tenant_id="tenant"))
