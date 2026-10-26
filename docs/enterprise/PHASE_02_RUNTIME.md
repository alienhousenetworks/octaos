# Phase 02 — durable runtime hardening

## Implemented in this increment

- Tenant-scope workflow idempotency lookups so a matching client key in another tenant cannot return that tenant's checkpoint.
- Store new idempotency keys as stable tenant-namespaced SHA-256 values; retain tenant-scoped lookup of legacy raw keys for compatibility.
- Validate checkpoint status transitions and reject backwards step movement.
- Make dead-letter replay report queue submission rather than falsely marking the task resolved immediately after enqueue.
- Bound dead-letter listing page size and sanitize replay dispatch errors returned to callers.
- Add focused regression tests and include them in the enterprise foundation workflow.

## Not yet complete

This is an incremental hardening step, not the full canonical runtime. Existing checkpoint rows have no unique constraint on (tenant_id, run_id); the global uniqueness constraint on the legacy idempotency_key column remains in the database. New keys are tenant-namespaced to avoid new cross-tenant collisions, but a reviewed schema migration is still needed to formalize the constraint and reconcile legacy rows.

DeadLetterService still has legacy call paths that can omit tenant_id; those callers must be inventoried and migrated before claiming complete tenant isolation for DLQ operations. A replay remains in the replaying state until a worker/reconciler confirms the outcome; a durable dispatch/outcome reconciliation contract is still required. This PR does not claim restart recovery or external side-effect exactly-once semantics.

## Verification

GitHub Actions runs the focused enterprise foundation tests, including the new durable-workflow regressions. The full backend suite, frontend build/lint, PostgreSQL migration/restore, concurrency tests, and failure-injection suite remain release gates.
