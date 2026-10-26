# OctaOS Phase 00 — Source Inventory and Risk Register

**Repository:** alienhousenetworks/octaos  
**Branch:** enterprise/phase-00-01-foundation  
**Audit status:** partial source inspection; no claim of full-suite execution.

## Confirmed source paths

| Area | Source | Initial finding |
|---|---|---|
| ASGI app and middleware | app/main.py | FastAPI app registers v1/v2 routers, tenant middleware, Prometheus middleware and CORS. |
| Tenant request context | app/core/middleware.py | Previous implementation accepted client tenant/org headers before attempting JWT claim fallback. This branch changes middleware so headers do not establish tenant context. |
| Authenticated identity | app/api/deps.py | get_current_user validates JWT, loads the user, checks active/verified status and binds tenant context from the user record. Further audit needed for all routes and context reset semantics. |
| Configuration | app/core/config.py | Contains development secret and database credential defaults; production fail-closed validation remains to be implemented and tested. |
| API surface | app/api/v1/api.py | Large router registration includes multiple domain modules, orchestrator, automations, MCP, integrations and RBAC. Full route-to-service inventory remains. |
| v2 health | app/api/v2/api.py | Health endpoint checks DB, Redis and best-effort Celery availability. Review output sanitisation and health/readiness semantics. |
| Runtime tests | tests/test_agent_runtime_kernel.py, tests/test_agent_runtime_protocol.py | Existing tests cover some idempotency, tool execution, evidence acceptance and output sanitisation. They do not prove platform-wide canonical runtime adoption. |
| Tenant tests | tests/test_tenant_isolation.py | Covers tenant-scoped analytics data. Request middleware spoofing regression coverage added separately. |
| Frontend | frontend/package.json | Next.js 16 / React 19 application; baseline build/lint has not yet been run in this audit. |
| Database migration config | alembic.ini | Alembic configured; migration head, upgrade path and restore procedure still need verification. |
| Startup schema mutation | app/main.py | Startup iterates over SQLAlchemy metadata to create missing tables and executes multiple ALTER TABLE statements outside a recorded Alembic release. Must be inventoried and moved to reviewed migrations before claiming controlled production releases. |

## Initial risk register

| ID | Risk | Severity | Evidence / next action |
|---|---|---|---|
| SEC-001 | Client-supplied tenant headers could establish request tenant context | Critical | Observed in original middleware. Patch removes header-derived context; add route-level integration tests and audit background jobs. |
| SEC-002 | Insecure default secret/database credentials can be loaded from settings | High | Observed in settings. Production/staging validation and startup guard added; confirm actual deployment environment values before rollout. |
| SEC-003 | Universal integration webhook route accepts unauthenticated POST payloads and dispatches provider actions | Critical | Initial patch requires timestamped HMAC using an encrypted provider-specific credential in production; requests without a configured secret fail closed. A tenant-admin provisioning API now stores signing secrets through the existing encrypted credential service, and inactive/unknown tenants are rejected. Native-provider compatibility and durable processing/retry semantics still require verification before rollout. Generic ingress now records an event ID in the existing WebhookEvent idempotency store after signature validation, but receipts are written before dispatch and do not yet distinguish processing, succeeded, or uncertain outcomes. |
| SEC-004 | Generic webhook challenge endpoint echoes challenge values without provider verification | High | Patch requires a configured per-provider webhook secret and matching verification token in production before echoing a challenge. A tenant-admin API supports a separately encrypted verification token. Confirm each provider's native challenge contract before rollout. |
| ARCH-001 | Multiple orchestration/workflow paths may fragment state | High | Router surface is broad; map concrete services and consumers before consolidating. |
| REL-001 | Runtime recovery and external side-effect idempotency may differ by module | High | Existing runtime tests cover a subset; create capability-by-capability matrix and restart/failure tests. |
| OBS-001 | Health endpoint may expose raw exception details | Medium | Initial patch replaces raw dependency exception text with safe status values and removes the unconditional enterprise_hardened claim; tests added. |
| DB-001 | Application startup performs schema mutation outside reviewed migrations | High | Observed in app/main.py. Inventory all inline DDL and replace incrementally with Alembic migrations; do not remove existing safeguards until migration parity is proven. |
| REL-002 | Database connectivity check logs failure but startup continues | High | Observed in startup_db_check. Decide readiness/startup policy explicitly; production should not accept traffic when required database dependencies are unavailable. |
| QA-001 | Full baseline is not recorded | High | Run backend tests, frontend build/lint, migration checks and CI; record actual outcomes. |

## Runtime inventory update

A targeted source-tree scan found multiple existing lifecycle/orchestration components. See [RUNTIME_INVENTORY.md](RUNTIME_INVENTORY.md) for the source-linked map and deferred selection decisions. [API_WORKER_TEST_MAP.md](API_WORKER_TEST_MAP.md) records the endpoint families, worker entry points and test-suite count. This confirms runtime consolidation must begin with compatibility mapping rather than adding a new engine.

## Phase 00 remaining work

- [ ] Enumerate all API routes and map endpoint -> service -> model -> external side effect.
- [ ] Identify all runtime/orchestrator/automation engines and usage counts.
- [ ] Inventory Celery task registrations, scheduling and retry configuration.
- [ ] Map all OAuth and API connectors, scopes, token storage and webhook validation.
- [x] Add timestamped HMAC verification and fail-closed behavior for the generic integration webhook ingress; add unit tests for valid, altered, stale and missing signatures.
- [x] Reuse the existing tenant/provider/event WebhookEvent uniqueness store for authenticated generic ingress and add stable fallback event keys.
- [ ] Add durable processing/succeeded/uncertain states with safe retry/reconciliation; current receipt is committed before dispatch.
- [ ] Add provider-native signature adapters.
- [x] Add tenant-admin API provisioning/rotation for encrypted per-provider webhook signing secrets and optional encrypted verification tokens.
- [ ] Add a user-facing integrations UI for secret setup and provider-native signing instructions.
- [ ] Validate challenge and signature compatibility with each real provider test account.
- [ ] Audit tenant isolation in every model/query path, background job and file/vector access path.
- [ ] Capture backend test results and failures.
- [ ] Capture frontend build/lint results and failures.
- [ ] Inspect Alembic heads and test upgrade/restore against disposable database.
- [ ] Publish migration order and compatibility test plan.

## Guardrails

No production deployment or destructive migration is authorised by this branch. Do not treat the presence of a router, class, test or configuration option as proof that a user-facing capability is production-ready.
