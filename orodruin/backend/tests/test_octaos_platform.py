import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test-secret-key"

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


client = TestClient(app)


def _register_and_token(subdomain: str, email: str) -> str:
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "tenant_name": f"Tenant {subdomain}",
            "subdomain": subdomain,
            "email": email,
            "password": "StrongPassword123!",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


def test_health_and_fixed_ai_config():
    assert client.get("/health").status_code == 200
    token = _register_and_token("acme", "admin@acme.test")
    cfg = client.get("/api/v1/agents/ai-config", headers={"Authorization": f"Bearer {token}"})
    assert cfg.status_code == 200
    body = cfg.json()
    assert body["provider"] == "local"
    assert body["text_model"] == "qwen3.5-4b"
    assert body["external_llm_enabled"] is False


def test_tenant_isolation_and_intelligence_pipeline():
    t1 = _register_and_token("alpha", "ceo@alpha.test")
    t2 = _register_and_token("beta", "ceo@beta.test")

    # Tenant 1 researches a company with coordinates for Orodruin map overlay
    r = client.post(
        "/api/v1/intelligence/companies/research",
        headers={"Authorization": f"Bearer {t1}"},
        json={"name": "CyberShield Corp", "domain": "cybershield.example", "industry": "Cybersecurity", "country": "US", "lat": 37.77, "lon": -122.41},
    )
    assert r.status_code == 200
    comp = r.json()
    assert comp["name"] == "CyberShield Corp"
    assert comp["classification"] in ("DERIVED", "MEASURED")

    # Tenant 2 must NOT see Tenant 1's companies
    t2_list = client.get("/api/v1/intelligence/companies", headers={"Authorization": f"Bearer {t2}"})
    assert t2_list.status_code == 200
    assert t2_list.json() == []

    # Map overlay returns GeoJSON Feature for Tenant 1
    overlay = client.get("/api/v1/intelligence/map-overlay", headers={"Authorization": f"Bearer {t1}"})
    assert overlay.status_code == 200
    assert len(overlay.json()["features"]) == 1

    # Lead discovery never fabricates unverified contact emails
    leads = client.post(
        "/api/v1/intelligence/leads/discover",
        headers={"Authorization": f"Bearer {t1}"},
        json={"topic": "cloud security", "region": "US", "company_profile_id": comp["id"], "count": 2},
    )
    assert leads.status_code == 200
    for lead in leads.json():
        assert lead["contact_verified"] is False
        assert lead["contact_email"] is None


def test_end_to_end_orchestrator_content_and_learning_loop():
    token = _register_and_token("gamma", "ops@gamma.test")
    headers = {"Authorization": f"Bearer {token}"}

    # Execute unified agent orchestration (intelligence -> leads -> strategy -> workflow -> learning)
    exe = client.post(
        "/api/v1/agents/execute",
        headers=headers,
        json={"goal": "Expand cloud security sales in Europe", "company_name": "EuroSecure", "topic": "cloud security", "region": "DE"},
    )
    assert exe.status_code == 200, exe.text
    data = exe.json()
    assert data["leads_discovered"] >= 1
    assert data["strategy_brief"]["id"]

    # Generate & approve marketing content asset
    asset = client.post(
        "/api/v1/business/content/generate",
        headers=headers,
        json={"asset_type": "image", "prompt": "Dark futuristic enterprise cybersecurity shield visual"},
    )
    assert asset.status_code == 200
    asset_id = asset.json()["id"]
    assert client.post(f"/api/v1/business/content/{asset_id}/approve", headers=headers).json()["status"] == "approved"

    # Verify LearningLoop recorded the decision & outcome
    summary = client.get("/api/v1/learning/summary", headers=headers).json()
    assert summary["total_decisions"] >= 1
    assert summary["evaluated_decisions"] >= 1
    assert summary["overall_success_rate"] == 1.0
