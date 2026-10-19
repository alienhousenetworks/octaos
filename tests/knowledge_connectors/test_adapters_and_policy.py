"""Integration tests for ConnectorService, PolicyEngine, Adapters, and Isolation."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base, Tenant
from app.models import flow_engine, knowledge_connectors
from app.services.knowledge_connectors.service import ConnectorService
from app.services.knowledge_connectors.contracts import (
    ConnectorInvocation,
    ExecutionContext,
)
from app.services.knowledge_connectors.policy import ConnectorPolicyEngine
from app.services.knowledge_connectors.secrets import ConnectorSecretVault
from app.services.knowledge_connectors.adapters.postgres import PostgresAdapter
from app.services.knowledge_connectors.cache import ConnectorCacheManager


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    # Create required tables
    tables = [Base.metadata.tables[t] for t in [
        "tenants", "agents", "knowledge_connectors", "connector_secret_references",
        "connector_config_versions", "connector_permissions", "connector_executions",
        "connector_schema_versions", "connector_audit_events", "connector_cache_entries"
    ]]
    Base.metadata.create_all(engine, tables=tables)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed test tenants
    t1 = Tenant(id="tenant_alpha", name="Alpha Corp", subdomain="alpha")
    t2 = Tenant(id="tenant_beta", name="Beta Corp", subdomain="beta")
    session.add_all([t1, t2])
    session.commit()

    yield session
    session.close()


def test_connector_creation_and_secret_vault(db_session):
    # 1. Create connector
    connector = ConnectorService.create_connector(
        db=db_session,
        tenant_id="tenant_alpha",
        name="Customer CRM API",
        slug="customer_crm",
        connector_type="rest_api",
        description="Production customer data",
    )
    assert connector.id is not None
    assert connector.state == "draft"

    # 2. Store encrypted credentials
    secret_payload = {
        "auth_type": "bearer",
        "bearer_token": "sk-secret-live-token-12345",
    }
    ConnectorService.store_secrets(
        db=db_session,
        connector_id=connector.id,
        tenant_id="tenant_alpha",
        secret_payload=secret_payload,
    )

    # 3. Retrieve decrypted credentials
    decrypted = ConnectorSecretVault.retrieve_secrets(db_session, connector.id)
    assert decrypted["bearer_token"] == "sk-secret-live-token-12345"


def test_tenant_boundary_isolation(db_session):
    connector = ConnectorService.create_connector(
        db=db_session,
        tenant_id="tenant_alpha",
        name="Alpha Private DB",
        slug="alpha_db",
        connector_type="postgres",
    )
    context_beta = ExecutionContext(
        tenant_id="tenant_beta",
        acting_agent_id="agent_sales_beta",
        department="sales",
        request_id="req_test_01",
    )

    # Beta tenant should NOT be able to access Alpha connector
    with pytest.raises(Exception):
        ConnectorPolicyEngine.evaluate(
            db=db_session,
            connector=connector,
            context=context_beta,
            operation="read",
        )


def test_policy_department_and_field_grants(db_session):
    connector = ConnectorService.create_connector(
        db=db_session,
        tenant_id="tenant_alpha",
        name="Payroll API",
        slug="payroll_api",
        connector_type="rest_api",
    )
    connector.state = "active"
    db_session.commit()

    # Grant permission only to HR department, deny ssn and bank_account
    ConnectorService.set_permission(
        db=db_session,
        connector_id=connector.id,
        tenant_id="tenant_alpha",
        department="hr",
        denied_fields=["ssn", "bank_account"],
    )

    # Test Sales AI trying to access Payroll API
    context_sales = ExecutionContext(
        tenant_id="tenant_alpha",
        acting_agent_id="agent_sales",
        department="sales",
        request_id="req_02",
    )
    decision_sales = ConnectorPolicyEngine.evaluate(
        db=db_session,
        connector=connector,
        context=context_sales,
        operation="read",
    )
    assert decision_sales.allowed is False
    assert "no grant" in decision_sales.reason

    # Test HR AI accessing Payroll API
    context_hr = ExecutionContext(
        tenant_id="tenant_alpha",
        acting_agent_id="agent_hr",
        department="hr",
        request_id="req_03",
    )
    decision_hr = ConnectorPolicyEngine.evaluate(
        db=db_session,
        connector=connector,
        context=context_hr,
        operation="read",
    )
    assert decision_hr.allowed is True
    assert "ssn" in decision_hr.denied_fields


@pytest.mark.asyncio
async def test_postgres_adapter_rejects_sql_injection():
    adapter = PostgresAdapter()
    context = ExecutionContext(
        tenant_id="tenant_alpha",
        acting_agent_id="agent_sales",
        department="sales",
        request_id="req_sql_01",
    )
    config = {
        "allowed_query_templates": [
            "DROP TABLE customers;",
            "DELETE FROM users WHERE 1=1;",
        ]
    }
    secrets = {"connection_string": "sqlite:///:memory:"}
    invocation = ConnectorInvocation(
        connector_id="conn_sql",
        operation="read",
        params={"template_index": 0},
    )

    result = await adapter.execute(context, config, secrets, invocation)
    assert result.status == "denied"
    assert result.safe_error_code == "SQL_INJECTION_OR_WRITE_DETECTED"
