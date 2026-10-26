# OctaOS enterprise runtime implementation — phased delivery

## Scope and operating rule

This plan brings OctaOS toward a secure, observable, reliable multi-tenant AI workforce runtime, using OpenMausBot as a reference for agent harnesses, event streams, permissions, connectors, triggers, and reusable team templates. OctaOS remains the business system of record: Sales, Marketing, HR, Support, Real Estate, approvals, billing, reporting, and tenant administration stay domain-owned.

**Do not mark a capability complete because a model, route, screen, or database table exists.** A phase is complete only when its acceptance tests pass in CI and the failure cases are demonstrated. This document records the plan and known source-level risks; it is not a claim that the entire codebase has been exhaustively audited or that production readiness has been established.

## Baseline source observations

Reviewed selected source files on the default branch, including `app/main.py`, `app/core/config.py`, `app/core/security.py`, `app/services/autonomous_runtime/engine.py`, and `requirements.txt`.

- The application has a FastAPI API surface, SQLAlchemy/Alembic dependencies, a tenant middleware, v1/v2 routers, an autonomous task lifecycle service, and workflow/agent modules.
- `app/main.py` performs database checks, seeds, table creation, and ad-hoc schema changes at application startup. Move schema changes to reviewed Alembic migrations and make deployment fail clearly when migration state is invalid; keep any required bootstrap data explicitly idempotent.
- `app/core/security.py` previously fell back to unsalted SHA-256 password hashes if bcrypt could not be imported. That fallback is removed in this change. Production must install the pinned bcrypt dependency. Existing SHA-256 password records, if any, need a controlled reset/re-enrollment plan rather than a fast-hash compatibility path.
- `app/services/autonomous_runtime/engine.py` provides task states, transition validation, event emission, idempotency lookup, and injected handlers. This source-level presence does not establish atomic concurrency protection, durable worker recovery, or universal use by every execution entry point; those are Phase 2 verification targets.
- Tenant-scoped helpers and middleware are present, but isolation must be tested across HTTP routes, workers, connector callbacks, file/artifact access, workflow execution, and admin operations.

## Delivery phases and gates

### Phase 0 — repository baseline and inventory
- [x] Identify major API, security, runtime, workflow, and frontend entry points.
- [x] Record source-level risks and the acceptance gates below.
- [ ] Build a complete route → service → model → frontend → test inventory.
- [ ] Run the current test suite and record a baseline (not run by this remote repository edit).
**Gate:** a reproducible inventory, test baseline, and prioritized risk register.

### Phase 1 — security and deployment foundation
- [x] Remove insecure SHA-256 password-hash fallback.
- [x] Add password-hash regression tests.
- [ ] Validate password-reset/re-enrollment handling for any legacy hashes.
- [ ] Audit secret encryption/key rotation and remove unsafe plaintext-secret compatibility paths only after data migration planning.
- [ ] Replace startup DDL with Alembic-only schema upgrades and test upgrade/rollback on a production-like database.
- [ ] Test cross-tenant IDOR, role/permission enforcement, session/token expiry, and secrets redaction.
**Gate:** security regression tests pass; migration and tenant-isolation tests pass; no production security downgrade on missing dependencies.

### Phase 2 — one durable execution runtime
- [ ] Trace all task entry points and consolidate them behind one lifecycle/policy boundary.
- [ ] Add durable leases, heartbeat/expiry, bounded retries, cancellation, checkpoints, and worker recovery.
- [ ] Persist task state and audit events transactionally; use an outbox for publishing events after commit.
- [ ] Enforce idempotency at the database boundary and reconcile uncertain external side effects.
**Gate:** worker-kill/restart recovers acknowledged work; concurrent duplicate submissions cannot create duplicate protected side effects; task and event state remain consistent.

### Phase 3 — common agent harness
- [ ] Normalize provider adapters and runtime events; stream sanitized progress to the UI.
- [ ] Add agent profiles/versions, context and artifact references, delegation, usage/cost limits, and cancellation.
- [ ] Never expose private chain-of-thought; show actionable progress, tool calls, outcomes, and evidence.
**Gate:** two providers pass the same contract tests; failure, timeout, cancellation, and verification are represented consistently.

### Phase 4 — versioned visual workflow engine
- [ ] Define versioned node/edge schemas and typed input/output contracts.
- [ ] Support validation, test runs, branching, retries/timeouts, error paths, parallel work, subflows, publish/rollback.
- [ ] Pin each execution to an immutable workflow version.
**Gate:** deterministic fixtures, invalid-graph rejection, and reproducible historical runs pass.

### Phase 5 — permissions, connectors, and computer-use boundary
- [ ] Enforce authorization on the server for every tool call, independent of frontend visibility.
- [ ] Add tenant-scoped OAuth connections, token refresh/revocation, webhook signature verification, and connector health.
- [ ] Isolate browser/computer tasks and require approvals for high-risk external side effects.
- [ ] Expose narrow, permissioned MCP tools with tenant identity and audit context.
**Gate:** direct API/tool invocation cannot bypass policy; revoked access stops new actions; approval is checked at execution time.

### Phase 6 — reliable schedules and event triggers
- [ ] Persist trigger receipts, deduplicate webhook/event deliveries, checkpoint long runs, and define overlap policies.
- [ ] Add dead-letter inspection, replay safety, pause/resume, missed-run handling, and observability.
**Gate:** duplicate, delayed, missing, and out-of-order triggers have documented tested behavior.

### Phase 7 — portable teams and industry packs
- [ ] Package agent/team definitions, workflow versions, prompt templates, tool requirements, and tests.
- [ ] Exclude secrets, tenant data, conversations, and run history from exports.
- [ ] Preview and validate imports; default external connections off and schedules paused.
**Gate:** a pack can be installed into a second tenant without data leakage or accidental external actions.

### Phase 8 — SaaS operations and pilot
- [ ] Enforce plan entitlements, quotas, usage metering, and cost reconciliation server-side.
- [ ] Add traces, actionable alerts, tenant-level operational views, backup/restore and upgrade drills.
- [ ] Pilot one Sales and one Marketing workflow with real connectors, human approvals, and independently verified outcomes.
**Gate:** agreed reliability, security, cost, and product outcome thresholds are met in a production-like environment.

## Shared test matrix

| Area | Required evidence |
|---|---|
| Tenant isolation | Cross-tenant reads/writes/artifacts/tool calls denied in API and worker paths |
| Crash recovery | Kill worker after task acceptance; task is recovered without losing event history |
| Idempotency | Duplicate requests/webhooks do not repeat protected side effects |
| Approval | High-risk action blocked until an authorized, current approval is recorded |
| Revocation | Revoked OAuth/token/role blocks subsequent actions |
| Provider failure | Timeouts, 429s, invalid output, and provider outages produce recoverable states |
| Workflow versioning | A run remains pinned to its published workflow version |
| Data migration | Upgrade from prior schema and restore from backup are exercised |
| Evidence | A task is not marked succeeded until its acceptance criteria are verified |
| Cost limits | Per-task and per-tenant budget stops are enforced server-side |

## Product differentiation to preserve

Use the shared runtime for Sales AI, Marketing Campaign OS, HR, Support, and Real Estate. Each domain service remains responsible for business validation, transactional writes, permissions, and source-of-truth records. The common runtime supplies execution lifecycle, events, approvals, connectors, budgets, evidence, and auditability. Report actual business outcomes only when the required data source is connected and measurement is configured.

## Delivery reporting format

For each phase report: changed files/PR, tests run and results, unresolved risks, acceptance-gate status, and the next phase to start. Never report an unrun test as passing or a planned capability as implemented.
