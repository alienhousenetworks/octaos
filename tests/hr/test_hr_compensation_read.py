from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import deps
from app.api.v1.endpoints import hr_compensation_read


class QueryStub:
    def __init__(self):
        self.filters = []

    def filter(self, *expressions, **kwargs):
        self.filters.extend(expressions)
        return self

    def order_by(self, *args, **kwargs):
        return self

    def offset(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def all(self):
        return []


class DBStub:
    def __init__(self):
        self.query_result = QueryStub()
        self.queried_model = None

    def query(self, model):
        self.queried_model = model
        return self.query_result


def make_client(db, user):
    app = FastAPI()
    app.include_router(hr_compensation_read.router, prefix="/hr/enterprise/compensation")
    app.dependency_overrides[deps.get_db] = lambda: db
    app.dependency_overrides[deps.get_current_tenant_id] = lambda: "tenant-a"
    app.dependency_overrides[deps.get_current_user] = lambda: user
    return TestClient(app)


def test_compensation_proposals_are_tenant_scoped_and_employee_scoped(monkeypatch):
    db = DBStub()
    monkeypatch.setattr(hr_compensation_read, "user_has_perm", lambda *_args, **_kwargs: False)
    client = make_client(db, SimpleNamespace(
        id="employee-user", role="member", is_system_admin=False, is_superuser=False
    ))

    response = client.get("/hr/enterprise/compensation/proposals")

    assert response.status_code == 200
    assert response.json() == []
    # One predicate limits the query to the active tenant; another limits a
    # non-HR user to proposals they personally requested.
    assert len(db.query_result.filters) == 2


def test_compensation_proposal_status_filter_rejects_unknown_values(monkeypatch):
    db = DBStub()
    monkeypatch.setattr(hr_compensation_read, "user_has_perm", lambda *_args, **_kwargs: False)
    client = make_client(db, SimpleNamespace(
        id="employee-user", role="member", is_system_admin=False, is_superuser=False
    ))

    response = client.get("/hr/enterprise/compensation/proposals?status=made_up")

    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid compensation proposal status."
