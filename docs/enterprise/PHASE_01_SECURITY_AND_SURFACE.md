# Enterprise Runtime Hardening — Phase 01

**Status:** implementation in progress; not a release certification.
**Branch:** feat/enterprise-runtime-hardening
**Scope:** high-risk tool authorization, interface switching, and the industry-neutral product boundary.

## Changes in this phase

### High-risk tool approvals are action-bound

- Added action_fingerprint(), a deterministic SHA-256 digest over tenant, run, bot, tool, target, payload, and policy version.
- High-risk actions now fail closed unless the approval status is approved and the current action fingerprint exactly matches the fingerprint attached to the persisted approval.
- The agent tool dispatcher computes the current fingerprint on the server from the actual dispatch payload and compares it with the server-provided approved_action_binding.
- Missing or stale bindings produce explicit denial reasons rather than treating a generic approved flag as permission.
- Added regression tests for missing approval binding, changed recipient/payload, run/policy changes, rejection, tenant mismatch, missing grants, and inactive connections.

**Integration requirement:** the approval creation/decision path must persist and return the same fingerprint using the same canonicalization function. Until that integration is completed and verified end-to-end, high-risk dispatches without a server-supplied matching binding are intentionally denied. This is fail-closed behavior, not evidence that the full approval workflow is finished.

### AI Workspace / Classic switching

- Replaced full-page navigation in the interface toggle with Next.js app-router navigation.
- Route-derived mode selection remains authoritative for explicit /app/assistant, /app, and /app/home entry points.
- Tenant switching still reloads the application after replacing the session, as that is a separate authentication transition.

**Verification still required:** browser E2E coverage for direct links, refresh, back/forward, other Classic routes, tenant switching, and mobile navigation.

### Industry-neutral boundary

The previous merged change removed dedicated real-estate and property-oriented field-sales routers and navigation surfaces from the active application. It also removed the property campaign endpoint block and disabled legacy real-estate pack selection.

Historical Alembic migrations and dormant modules are intentionally retained until dependency, data-retention, and migration safety checks are complete. They are not registered as active general API routes. The mobile field-sales application, legacy service modules, test fixtures, and historical schema still exist in the repository and must not be represented as fully deleted. No production tables or customer records should be dropped as part of a code-only cleanup.

## Remaining enterprise gates

1. Wire the approval fingerprint into approval creation, edit/reapprove, expiry, revocation, and decision persistence; then test the actual dispatch endpoint end-to-end.
2. Audit all tool dispatch paths (general agents, Sales, Marketing, HR, MCP, workflows, webhooks) for bypasses around the canonical broker.
3. Complete durable-run parity between autonomous tasks, agent runs, workflow executions, and department orchestrators; avoid creating a second source of truth.
4. Add event outbox/replay and worker lease recovery only where existing infrastructure does not already satisfy the contract.
5. Add browser-level tests for workspace switching and permissions screens.
6. Finish the repository-wide real-estate source audit, remove dormant mobile/UI/service assets after confirming no runtime dependency, and preserve migration history and production data.
7. Run backend tests, frontend lint/typecheck/build, security tests, migrations, and controlled deployment smoke tests. No such run is implied by this document.

## Release rule

This phase is not enterprise-ready until the relevant checks pass and the approval path is connected end-to-end. A successful unit test or the presence of a model/endpoint alone is not sufficient evidence of production readiness.