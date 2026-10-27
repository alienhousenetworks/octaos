from types import SimpleNamespace
from unittest.mock import MagicMock

from app.models.autonomous_work import AutonomousTaskEvent
from app.models.workforce_events import WorkforceEvent
from app.services.autonomous_runtime.engine import AutonomousRuntime


def test_autonomous_task_event_is_mirrored_without_private_payload():
    db = MagicMock()
    runtime = AutonomousRuntime(db)
    task = SimpleNamespace(
        id="task-123",
        tenant_id="tenant-a",
        title="Prepare weekly report",
        status="running",
    )

    runtime.emit(
        task,
        "state_transition",
        "Task moved to running",
        actor_type="system",
        payload={
            "from": "queued",
            "to": "running",
            "api_token": "do-not-publish",
            "count": 2,
        },
    )

    added = [call.args[0] for call in db.add.call_args_list]
    internal = next(item for item in added if isinstance(item, AutonomousTaskEvent))
    public = next(item for item in added if isinstance(item, WorkforceEvent))

    assert internal.tenant_id == "tenant-a"
    assert public.tenant_id == "tenant-a"
    assert public.run_id == "task-123"
    assert public.source == "autonomous_runtime"
    assert public.event_type == "task.state_transition"
    assert public.payload["task_id"] == "task-123"
    assert public.payload["details"]["from"] == "queued"
    assert public.payload["details"]["count"] == 2
    assert "api_token" not in public.payload["details"]
    db.commit.assert_not_called()
