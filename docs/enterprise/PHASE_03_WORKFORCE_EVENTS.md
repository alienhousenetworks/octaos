# Phase 03 — persistent workforce event stream

## Implemented in this increment

- Added a durable `workforce_events` table model, registered with the existing startup model discovery.
- Added an authenticated API to append user-originated events and read events in cursor order.
- Scoped all event reads and idempotency keys to the authenticated tenant.
- Enforced unique `(tenant_id, event_key)` so repeated client delivery is idempotent; reuse of a key with a different event type or payload returns HTTP 409.
- Added bounded JSON payloads (64 KiB), bounded page sizes (maximum 200), optional event/run filters, and cursor validation.
- Added focused regression tests for tenant-scoped lookup, duplicate behavior, payload limits, and cursor encoding.

## API

- `POST /api/v1/workforce/events` — append a user-originated event.
- `GET /api/v1/workforce/events?cursor=...&limit=100` — read events after a cursor. Responses include `items`, `next_cursor`, and `has_more`.

Both endpoints require an authenticated active user; the tenant is derived from that user's verified token context, not from a caller-supplied tenant header.

## Limitations and next work

This increment provides durable polling/replay, not a WebSocket/SSE transport. Existing agent/worker orchestrators are not yet automatically emitting events, and there is no reconnecting frontend consumer yet. The repository currently creates model tables at startup; a reviewed Alembic migration and PostgreSQL upgrade/restore tests are still required before production rollout. Event payloads should contain operational metadata, not secrets or full prompts by default. Retention, redaction, event schema versioning, and per-event authorization policies remain follow-up work.

## Verification

The enterprise foundation workflow now compiles the changed modules and runs the event-stream regression tests. A successful CI result and full application/migration tests are required before considering this phase complete.
