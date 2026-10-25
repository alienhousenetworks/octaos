# OctaOS Autonomous Work Runtime v1

## What this slice adds

- Tenant-scoped persistent task records with an explicit lifecycle.
- Append-only task event records for creation, state transitions, and approvals.
- Idempotent task creation when a caller supplies an idempotency key.
- A common runtime entry point for business-specific execution adapters.
- Explicit verification semantics: an adapter must return `verified: true` and non-empty evidence before a task can be marked `succeeded`.
- Safe failure behavior: if no adapter is registered for a task type, the task becomes `blocked` with `EXECUTOR_NOT_CONFIGURED`; the platform does not claim work was performed.
- Tenant-scoped API routes for creating, listing, inspecting, cancelling tasks, reading event history, and deciding an existing approval request.

## API

All routes are under `/api/v1/autonomous-work` and require an authenticated user.

- `POST /tasks` — create a durable task.
- `GET /tasks` — list tasks visible to the caller.
- `GET /tasks/{task_id}` — inspect task state.
- `GET /tasks/{task_id}/events` — inspect the task event ledger.
- `POST /tasks/{task_id}/cancel` — cancel non-terminal work.
- `POST /tasks/{task_id}/approvals/{approval_id}/decision` — approve/reject a pending approval.

Example request:

```json
{
  "title": "Prepare weekly sales operations report",
  "goal": "Review this week's pipeline changes, identify stalled deals, and prepare a report with evidence.",
  "autonomy_level": "supervised",
  "risk_level": "standard",
  "acceptance_criteria": [
    "Report includes source records and dates",
    "Unknown values are explicitly marked unknown"
  ],
  "context": {
    "task_type": "sales_weekly_report"
  },
  "idempotency_key": "sales-weekly-report-2026-10-26"
}
```

Creating a task persists it; it does not claim that execution has started. A worker can be dispatched with `octaos.execute_autonomous_task.delay(task_id, tenant_id)`. Until a real execution adapter is registered for the requested `context.task_type`, the worker explicitly blocks the task. This is intentional and prevents fake-success behavior.

## Registering an execution adapter

Adapters should be wired by application startup code and should:
1. Enforce tenant scope in every database query and provider request.
2. Use the central model gateway and authorized integration credentials.
3. Apply idempotency to external writes.
4. Request a durable approval before high-risk or externally visible actions.
5. Return an output plus evidence that can be independently checked.
6. Never return `verified: true` without evidence.

Expected result contract:

```python
{
    "output": {"summary": "Report prepared"},
    "verified": True,
    "evidence": [
        {"type": "database_record", "id": "record-id", "observed_at": "ISO-8601"}
    ],
    "verification": {"method": "re-read-after-write", "passed": True}
}
```

## Important deployment note

This repository creates some SQLAlchemy tables during application startup, but deployments should use a reviewed Alembic migration before production rollout. Ensure the model module is imported before metadata creation, then add a migration for these four tables and indexes. Do not rely on a live production restart to make schema changes.

## Remaining work for the complete product

This is the first runtime slice, not the finished autonomous workforce. Follow-on work must wire the worker to registered adapters; add transactional outbox dispatch; make approval creation part of the execution contract; add model-planned multi-step DAGs and checkpoints; add sandboxed browser/terminal/file executors; build OAuth integration discovery and authorization; implement central model-role routing; add evaluation datasets and runtime metrics; and connect the task monitor UI.
