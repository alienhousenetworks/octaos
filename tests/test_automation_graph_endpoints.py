"""Integration tests for visual canvas graph endpoints."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.automations import AutomationWorkflow
from app.models.base import Tenant, User
from app.core.security import create_access_token
import uuid


@pytest.fixture
def client_and_auth():
    db = SessionLocal()
    tenant = db.query(Tenant).first()
    if not tenant:
        tenant = Tenant(id=f"tenant_{uuid.uuid4().hex[:8]}", name="Test Tenant")
        db.add(tenant)
        db.commit()

    user = db.query(User).filter_by(tenant_id=tenant.id).first()
    if not user:
        user = User(
            id=f"user_{uuid.uuid4().hex[:8]}",
            tenant_id=tenant.id,
            email=f"tester_{uuid.uuid4().hex[:6]}@octaos.org",
            role="admin",
            is_active=True,
        )
        db.add(user)
        db.commit()

    token = create_access_token(user.id)
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant.id}

    yield client, headers, db, tenant, user
    db.close()


def test_graph_get_and_save_workflow(client_and_auth):
    client, headers, db, tenant, user = client_and_auth

    # 1. Create a workflow
    create_payload = {
        "name": "Canvas Integration Flow",
        "category": "sales",
        "definition_ir": {
            "name": "Canvas Integration Flow",
            "slug": "canvas-integration-flow",
            "category": "sales",
            "trigger": {
                "type": "octaos_event",
                "event": "lead.qualified",
                "display_name": "OctaOS: Lead Qualified",
            },
            "steps": [
                {
                    "id": "slack_step",
                    "piece": "slack",
                    "action": "send_message",
                    "display_name": "Slack: Alert",
                    "parameters": {"channel": "#sales"},
                }
            ],
        },
    }
    create_res = client.post("/api/v1/automations", json=create_payload, headers=headers)
    assert create_res.status_code == 200, create_res.text
    wf_id = create_res.json()["id"]

    # 2. Get graph (should auto-convert from legacy IR)
    get_res = client.get(f"/api/v1/automations/{wf_id}/graph", headers=headers)
    assert get_res.status_code == 200, get_res.text
    graph_data = get_res.json()
    assert graph_data["workflow_id"] == wf_id
    assert len(graph_data["graph"]["nodes"]) == 2
    assert graph_data["validation"]["is_valid"] is True

    # 3. Save modified graph with an extra condition node
    modified_graph = graph_data["graph"]
    modified_graph["nodes"].append({
        "id": "hubspot_step",
        "type": "action",
        "name": "HubSpot: Deal",
        "version": "1.0.0",
        "position": {"x": 500, "y": 200},
        "tool_id": "hubspot:create_deal",
        "config": {"amount": 10000},
        "input_mappings": {},
        "credential_refs": [],
        "timeout_seconds": 120,
        "is_compensable": False,
        "requires_approval": False,
    })
    modified_graph["edges"].append({
        "id": "edge_slack_to_hubspot",
        "source": "slack_step",
        "source_handle": "output",
        "target": "hubspot_step",
        "target_handle": "input",
        "kind": "data",
    })

    save_res = client.put(f"/api/v1/automations/{wf_id}/graph", json=modified_graph, headers=headers)
    assert save_res.status_code == 200, save_res.text
    save_data = save_res.json()
    assert save_data["status"] == "saved"
    assert save_data["version"] >= 2
    assert save_data["validation"]["is_valid"] is True

    # 4. Publish workflow
    pub_res = client.post(f"/api/v1/automations/{wf_id}/publish", headers=headers)
    assert pub_res.status_code == 200, pub_res.text
    assert pub_res.json()["status"] == "published"
    assert pub_res.json()["workflow_status"] == "active"
