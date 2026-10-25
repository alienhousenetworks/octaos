from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import deps
from app.api.v1.endpoints import hr_enterprise
from app.models.hr_core import EmployeeProfile


class QueryStub:
    def __init__(self, first_result=None):
        self.first_result = first_result

    def filter_by(self, **kwargs):
        self.filters = kwargs
        return self

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.first_result

    def all(self):
        return []

    def order_by(self, *args, **kwargs):
        return self

    def offset(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self


class DBStub:
    def __init__(self, first_result=None):
        self.first_result = first_result
        self.added = []

    def query(self, model):
        return QueryStub(self.first_result if model is EmployeeProfile else None)

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        pass

    def refresh(self, obj):
        pass

    def rollback(self):
        pass


def make_client(db, user):
    app = FastAPI()
    app.include_router(hr_enterprise.router, prefix="/hr/enterprise")
    app.dependency_overrides[deps.get_db] = lambda: db
    app.dependency_overrides[deps.get_current_tenant_id] = lambda: "tenant-a"
    app.dependency_overrides[deps.get_current_user] = lambda: user
    return TestClient(app)


def test_service_request_cannot_reference_employee_from_another_tenant():
    db = DBStub(first_result=None)
    client = make_client(db, SimpleNamespace(
        id="user-1", role="member", is_system_admin=False, is_superuser=False,
        user_permissions=[], groups=[]
    ))
    response = client.post("/hr/enterprise/service-requests", json={
        "employee_id": "employee-from-tenant-b",
        "category": "benefits",
        "subject": "Benefits question",
        "description": "Please explain the benefits enrollment process."
    })
    assert response.status_code == 404
    assert response.json()["detail"] == "Employee not found."
    assert db.added == []


def test_hr_performance_write_requires_canonical_permission():
    db = DBStub()
    client = make_client(db, SimpleNamespace(
        id="user-2", role="hr_manager", is_system_admin=False, is_superuser=False,
        user_permissions=[], groups=[]
    ))
    response = client.post("/hr/enterprise/performance-reviews", json={
        "employee_id": "employee-1", "cycle": "2026-H2", "goals": []
    })
    assert response.status_code == 403
    assert "hr.manage_performance" in response.json()["detail"]
    assert db.added == []


def test_hr_performance_write_with_permission_is_tenant_scoped():
    db = DBStub(first_result=None)
    client = make_client(db, SimpleNamespace(
        id="hr-1", role="member", is_system_admin=False, is_superuser=False,
        user_permissions=[SimpleNamespace(codename="hr.manage_performance")], groups=[]
    ))
    response = client.post("/hr/enterprise/performance-reviews", json={
        "employee_id": "employee-from-tenant-b", "cycle": "2026-H2", "goals": []
    })
    assert response.status_code == 404
    assert db.added == []
