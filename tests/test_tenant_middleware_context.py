from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.middleware import TenantMiddleware
from app.models.base import tenant_context, org_context


def _app():
    app = FastAPI()
    app.add_middleware(TenantMiddleware)

    @app.get("/context")
    def read_context():
        return {
            "tenant_id": tenant_context.get(),
            "organization_id": org_context.get(),
        }

    return app


def test_client_tenant_headers_do_not_establish_tenant_context():
    client = TestClient(_app())

    response = client.get(
        "/context",
        headers={
            "X-Tenant-ID": "victim-tenant",
            "X-Organization-ID": "victim-organization",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"tenant_id": None, "organization_id": None}


def test_context_is_reset_after_request():
    client = TestClient(_app())

    client.get(
        "/context",
        headers={"X-Tenant-ID": "untrusted-tenant"},
    )

    assert tenant_context.get() is None
    assert org_context.get() is None
