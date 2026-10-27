from unittest.mock import MagicMock

import pytest

from app.models.agent_runtime import ExecutionIdentity
from app.services.agent_runtime.execution_identity import register_execution_identity


def test_execution_identity_registration_is_idempotent_for_same_source():
    db = MagicMock()
    existing = MagicMock(spec=ExecutionIdentity)
    existing.canonical_execution_id = "canonical-1"
    existing.metadata_json = {}
    db.query.return_value.filter.return_value.first.return_value = existing

    result = register_execution_identity(
        db, tenant_id="tenant-a", source_kind="workflow_run",
        source_id="run-1", canonical_execution_id="canonical-1",
    )

    assert result is existing
    db.add.assert_not_called()


def test_execution_identity_rejects_relinking_source_to_another_canonical_run():
    db = MagicMock()
    existing = MagicMock(spec=ExecutionIdentity)
    existing.canonical_execution_id = "canonical-1"
    existing.metadata_json = {}
    db.query.return_value.filter.return_value.first.return_value = existing

    with pytest.raises(ValueError, match="EXECUTION_IDENTITY_CONFLICT"):
        register_execution_identity(
            db, tenant_id="tenant-a", source_kind="workflow_run",
            source_id="run-1", canonical_execution_id="canonical-2",
        )


def test_execution_identity_requires_tenant_and_source_identity():
    db = MagicMock()
    with pytest.raises(ValueError):
        register_execution_identity(
            db, tenant_id="", source_kind="agent_run", source_id="run-1",
        )
