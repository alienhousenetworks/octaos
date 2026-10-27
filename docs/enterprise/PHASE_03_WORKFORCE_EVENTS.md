# Phase 03 — persistent workforce event stream

## Implemented in this increment

- Added a durable `workforce_events` table model, registered with the existing startup model discovery.
- Added an authenticated API to append user-originated events and read events in cursor order.
- Scoped all event reads and idempotency keys to the authenticated tenant.
- Enforced unique `(tenant_id, event_key)` so repeated client delivery is idempotent; reuse of a key with a different event type or payload returns HTTP 409.
- Added bounded JSON payloads (64 KiB), bounded page sizes (maximum 200), optional event/run filters, and cursor validation.
- Added focused regression tests for tenant-scoped lookup, duplicate behavior, payload limits, cursor encoding, and runtime event mirroring.
- Mirrored autonomous task lifecycle events into the shared event log in the same database transaction as the internal task event. Public payloads exclude task goals, full context, model output, and fields that look like credentials or private reasoning.
- Added an Alembic migration and registered the model in migration metadata.
- Added a global-header activity panel that polls every five seconds, reconnects after transient failures, resumes from a cursor, and displays only bounded operational metadata.

## API

- `POST /api/v1/workforce/events` — append a user-originated event.
- `GET /api/v1/workforce/events?cursor=...&limit=100` — read events after a cursor. Responses include `items`, `next_cursor`, and `has_more`.
- `GET /api/v1/workforce/events?latest=true&limit=100` — fetch the newest page for a UI initial load; subsequent polling uses `next_cursor`.

Both endpoints require an authenticated active user; the tenant is derived from that user's verified token context, not from a caller-supplied tenant header.

## Limitations and next work

The activity panel uses durable polling/replay, not WebSocket/SSE. The autonomous task lifecycle is wired to the common event log, but other department orchestrators and provider-level token/tool events are not yet bridged. The migration has been authored but must be exercised against supported PostgreSQL versions and the repository’s full Alembic head graph before production rollout. Retention, formal schema versioning, event redaction policy, and per-event authorization policies remain follow-up work.

## Verification

The enterprise foundation workflow now compiles the runtime bridge and migration and runs the focused event-stream tests. Frontend quality CI typechecks and builds the activity panel. A successful run of both workflows plus PostgreSQL migration/recovery testing is required before considering this phase complete.
