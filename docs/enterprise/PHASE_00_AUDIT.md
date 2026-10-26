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
| SEC-003 | Universal integration webhook route accepts unauthenticated POST payloads and dispatches provider actions | Critical | Observed in app/api/v1/endpoints/integrations.py: receive_integration_webhook accepts tenant_id from the URL, has no user dependency or signature check, and directly calls provider services. Add provider-native signature verification or a per-tenant secret with replay protection before production use. |
| SEC-004 | Generic webhook challenge endpoint echoes challenge values without provider verification | High | Observed in app/api/v1/endpoints/integrations.py: verify_webhook_challenge. Audit provider requirements and require challenge-token verification where applicable. |
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
- [ ] Secure the generic integration webhook ingress with provider-specific signature checks or tenant-scoped secret verification and replay protection; add tests for forged and replayed requests.
- [ ] Audit tenant isolation in every model/query path, background job and file/vector access path.
- [ ] Capture backend test results and failures.
- [ ] Capture frontend build/lint results and failures.
- [ ] Inspect Alembic heads and test upgrade/restore against disposable database.
- [ ] Publish migration order and compatibility test plan.

## Guardrails

No production deployment or destructive migration is authorised by this branch. Do not treat the presence of a router, class, test or configuration option as proof that a user-facing capability is production-ready.
