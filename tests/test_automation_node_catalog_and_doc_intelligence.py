"""Integration and unit tests for automation node catalog, test execution, and document intelligence."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.base import Tenant, User
from app.core.security import create_access_token
from app.services.automation.node_registry import NodeRegistry
from app.services.automation.document_field_mapper import DocumentFieldMapper
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


def test_node_catalog_hierarchy_and_filtering(client_and_auth):
    client, headers, _, _, _ = client_and_auth

    # 1. Fetch full catalog
    res = client.get("/api/v1/automation-nodes/catalog?mode=all", headers=headers)
    assert res.status_code == 200, res.text
    catalog = res.json()
    assert isinstance(catalog, list)
    assert len(catalog) >= 7

    category_ids = {cat["id"] for cat in catalog}
    expected_categories = {
        "triggers",
        "control_flow",
        "document_intelligence",
        "data_transform",
        "connectivity",
        "ai_agents",
        "native_modules",
    }
    assert expected_categories.issubset(category_ids)

    # 2. Verify 3-level structure (Category -> Families -> Nodes)
    doc_cat = next(c for c in catalog if c["id"] == "document_intelligence")
    assert len(doc_cat["families"]) >= 2
    extract_fam = next(f for f in doc_cat["families"] if f["id"] == "doc_extraction")
    assert any(n["node_id"] == "octaos.document.submit" for n in extract_fam["nodes"])

    # 3. Filter by mode (document mode only)
    doc_mode_res = client.get("/api/v1/automation-nodes/catalog?mode=document", headers=headers)
    assert doc_mode_res.status_code == 200
    doc_mode_catalog = doc_mode_res.json()
    for cat in doc_mode_catalog:
        for fam in cat["families"]:
            for node in fam["nodes"]:
                assert node["mode"] in ("all", "document")


def test_node_details_and_isolated_execution(client_and_auth):
    client, headers, _, _, _ = client_and_auth

    # 1. Fetch node details
    node_id = "octaos.document.submit"
    res = client.get(f"/api/v1/automation-nodes/nodes/{node_id}", headers=headers)
    assert res.status_code == 200, res.text
    node_def = res.json()
    assert node_def["node_id"] == node_id
    assert node_def["name"] == "OctaOS Document Extractor"

    # 2. Test isolated node run
    test_payload = {
        "node_id": node_id,
        "config": {"department": "HR", "ocr_enabled": True},
        "input_payload": {"filename": "contract.pdf"},
    }
    test_res = client.post("/api/v1/automation-nodes/test", json=test_payload, headers=headers)
    assert test_res.status_code == 200, test_res.text
    result = test_res.json()
    assert result["status"] == "succeeded"
    assert result["node_id"] == node_id


def test_document_validation_endpoint(client_and_auth):
    client, headers, _, _, _ = client_and_auth

    # Test valid fields meeting minimum confidence
    val_payload = {
        "fields": {
            "document_type": "Master Services Agreement",
            "counterparty_name": "Acme Corp",
            "effective_date": "2026-01-01",
        },
        "required_fields": ["document_type", "counterparty_name"],
        "min_confidence": 0.75,
        "current_confidence": 0.95,
    }
    res = client.post("/api/v1/automation-documents/validate", json=val_payload, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["is_valid"] is True
    assert data["requires_human_review"] is False
    assert len(data["missing_required_fields"]) == 0

    # Test missing required field
    invalid_payload = {
        "fields": {
            "document_type": "Invoice",
        },
        "required_fields": ["document_type", "counterparty_name"],
        "min_confidence": 0.75,
        "current_confidence": 0.90,
    }
    invalid_res = client.post("/api/v1/automation-documents/validate", json=invalid_payload, headers=headers)
    assert invalid_res.status_code == 200
    invalid_data = invalid_res.json()
    assert invalid_data["is_valid"] is False
    assert invalid_data["requires_human_review"] is True
    assert "counterparty_name" in invalid_data["missing_required_fields"]


def test_document_field_mapper_validation_logic():
    # Low confidence triggers human review
    report = DocumentFieldMapper.validate_extracted_fields(
        fields={"title": "Offer Letter"},
        required_fields=["title"],
        min_confidence=0.85,
        current_confidence=0.60,
    )
    assert report["is_valid"] is False
    assert report["requires_human_review"] is True
    assert any("Confidence score" in f["reason"] for f in report["flagged_fields"])
