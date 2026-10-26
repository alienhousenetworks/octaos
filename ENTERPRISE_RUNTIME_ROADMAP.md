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
- [x] Handle concurrent idempotency-key conflicts by returning the existing tenant-scoped task (regression test added; CI execution still pending).
- [ ] Reconcile uncertain external side effects.
**Gate:** worker-kill/restart recovers acknowledged work; concurrent duplicate submissions cannot create duplicate protected side effects; task and event state remain consistent.

### Phase 3 — common agent harness
- [x] Add provider-neutral request/outcome/event contracts and sanitized public event serialization.
- [x] Add conservative acceptance verification requiring evidence by default.
- [ ] Wire provider adapters and the UI/SSE stream to this contract; add profiles, delegation, budgets, and cancellation.
**Gate:** two live providers pass the same contract tests; failure, timeout, cancellation, and verification are represented consistently. Current work adds the contract, not proof of live provider integration.

### Phase 4 — versioned visual workflow engine
- [x] Add a side-effect-free graph validator for node types, required config, graph shape, cycles, dangling/duplicate edges, and embedded secrets.
- [ ] Integrate validation into every workflow save/publish/run path and enforce typed input/output contracts.
- [ ] Add test runs, branching, retries/timeouts, error paths, parallel work, subflows, publish/rollback, and immutable run-version pinning.
**Gate:** deterministic fixtures, invalid-graph rejection, and reproducible historical runs pass. Validation helper integration remains pending.

### Phase 5 — permissions, connectors, and computer-use boundary
- [x] Add reusable server-side tool authorization checks for tenant match, active connection, explicit tool grants, and high-risk approval.
- [x] Add timestamped HMAC-SHA256 webhook signature verification with constant-time comparison.
- [ ] Integrate these helpers with the relevant non-MCP tool/connector execution paths; test credential revocation and webhook provider-specific signatures.
- [ ] Complete browser/computer isolation and approval enforcement for every high-risk side effect.
- [ ] Continue using the existing governed MCP dispatcher and verify all actions/approval states with integration tests.
**Gate:** direct API/tool invocation cannot bypass policy; revoked access stops new actions; approval is checked at execution time. Helpers are not a substitute for end-to-end integration tests.

### Phase 6 — reliable schedules and event triggers
- [x] Add trigger-to-task dispatch with stable, bounded idempotency keys backed by the existing tenant/idempotency database uniqueness constraint.
- [ ] Wire schedule/webhook entry points to the dispatcher; add trigger receipts independent of task retention, checkpoints, overlap policies, dead-letter inspection, pause/resume, missed-run handling, and replay controls.
**Gate:** duplicate, delayed, missing, and out-of-order triggers have documented tested behavior. The helper creates a queued task; it does not itself run or acknowledge provider-specific triggers.

### Phase 7 — portable teams and industry packs
- [x] Add portable pack manifest creation/validation with semantic versions and recursive rejection of secret-like and tenant-specific fields.
- [x] Add install-preview defaults with external connections disabled, schedules paused, reauthorization, validation, and admin review required.
- [ ] Integrate with the existing package/installation APIs, validate all workflow definitions on import, and implement rollback/compatibility checks.
**Gate:** a pack can be installed into a second tenant without data leakage or accidental external actions. The current helper is not yet wired into marketplace APIs.

### Phase 8 — SaaS operations and pilot
- [x] Add reusable server-side plan entitlement, provider allowlist, concurrency, task quota, and monthly budget admission checks.
- [ ] Load entitlements from the persisted subscription/tenant plan and call the guard at every execution entry point; add durable usage idempotency and reconciliation.
- [ ] Add traces, actionable alerts, tenant-level operational views, backup/restore and upgrade drills.
- [ ] Pilot one Sales and one Marketing workflow with real connectors, human approvals, and independently verified outcomes.
**Gate:** agreed reliability, security, cost, and product outcome thresholds are met in a production-like environment. Admission primitives alone do not constitute billing integration.

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

## Additional implementation artifacts on the working branch

- `app/services/agent_runtime/protocol.py`: normalized request/outcome/event contract and sanitized public event serialization.
- `app/services/workflow_governance/validator.py`: static workflow graph validation.
- `app/services/runtime_governance/tool_policy.py`: server-side tool policy and timestamped webhook HMAC verification.
- `app/services/runtime_governance/triggers.py`: stable trigger delivery keys and idempotent queued-task creation.
- `app/services/runtime_governance/portable_packs.py`: tenant-safe portable pack manifests and safe install preview.
- `app/services/runtime_governance/entitlements.py`: plan/provider/quota/budget admission primitives.
- Regression tests were added for these utilities. They have not been run in a checked-out environment in this session, and the end-to-end integration gates above remain open.


## Integration pass — 2026-10-26

This pass wires the earlier Phases 3–8 primitives into selected existing execution paths. It is not a production-readiness declaration.

- **Agent harness / UI events:** the existing AI gateway is adapted to the common AgentRequest / AgentOutcome contract. Provider-reported usage is carried through a callback; normalized, redacted run events are persisted in ExecutionEvent. The Agent Console consumes the tenant-scoped SSE endpoint at /api/v1/autonomous-work/agent-runs/{run_id}/events/stream.
- **Workflow versions:** new automation creation validates and snapshots the graph; graph draft saves reject invalid graphs; publish checks the immutable version snapshot; manual runs require a validated published snapshot and record its version/hash in execution metadata.
- **Tool boundary:** the ToolRegistry rejects calls without server-created grant context, tenant identity, or explicit tool grant. High-risk policy is evaluated at dispatch time. MCP continues to use its existing governed dispatcher.
- **Schedules / recovery:** the scheduled-trigger poller leases due rows under FOR UPDATE SKIP LOCKED, retries failed dispatches, and deactivates successful one-time schedules. This reduces concurrent overlap and missed-run loss; a crash after external enqueue can still cause duplicate delivery until a durable outbox/receipt with downstream idempotency is introduced.
- **Portable packages:** marketplace installation runs the legacy manifest through the portable-pack validator, rejects missing required tools and secret-like configuration, scopes package lookup to platform-wide or same-tenant packages, and creates new installs paused with schedules/connections disabled and admin review required.
- **Subscription / usage:** agent execution checks subscription status, agent entitlement, action quota and optional provider allowlist. The provider allowlist is passed into the gateway so failover cannot silently escape it. The runtime uses provider-reported token/cost values when available and updates existing subscription usage counters. Invoice reconciliation, concurrency reservation across workers, and exact preflight cost reservation remain separate gates.
- **Regression tests:** focused tests cover contract redaction, direct tool-dispatch authorization, tenant mismatch, high-risk approval, and the existing governance helper tests. GitHub Actions is the source of truth for this branch's current test status.

### Remaining acceptance gates

1. Run full backend/frontend suites against the supported dependency lock and production-like PostgreSQL/Redis configuration.
2. Add migration-backed durable trigger receipts/outbox with provider event IDs, replay controls, and downstream idempotency for enqueue-crash recovery.
3. Prove tenant isolation using two real tenants across agents, tool connections, event streams, packages, workflow versions, and usage reports.
4. Exercise worker kill/restart, stale schedule leases, dead-letter replay, and duplicate webhook delivery.
5. Validate package rollback/compatibility and activation approvals in the real marketplace UI.
6. Reconcile gateway ProviderUsage, UsageEvent, subscription counters, and provider invoices with idempotent ledger adjustments.
7. Run provider smoke tests with real credentials in a controlled staging tenant; no live provider credentials are used by the focused CI suite.
