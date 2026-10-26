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

## Initial risk register

| ID | Risk | Severity | Evidence / next action |
|---|---|---|---|
| SEC-001 | Client-supplied tenant headers could establish request tenant context | Critical | Observed in original middleware. Patch removes header-derived context; add route-level integration tests and audit background jobs. |
| SEC-002 | Insecure default secret/database credentials can be loaded from settings | High | Observed in settings. Add production startup validation and deployment configuration checks. |
| ARCH-001 | Multiple orchestration/workflow paths may fragment state | High | Router surface is broad; map concrete services and consumers before consolidating. |
| REL-001 | Runtime recovery and external side-effect idempotency may differ by module | High | Existing runtime tests cover a subset; create capability-by-capability matrix and restart/failure tests. |
| OBS-001 | Health endpoint may expose raw exception details | Medium | Review endpoint response; return safe reason codes publicly and retain details in logs. |
| QA-001 | Full baseline is not recorded | High | Run backend tests, frontend build/lint, migration checks and CI; record actual outcomes. |

## Phase 00 remaining work

- [ ] Enumerate all API routes and map endpoint -> service -> model -> external side effect.
- [ ] Identify all runtime/orchestrator/automation engines and usage counts.
- [ ] Inventory Celery task registrations, scheduling and retry configuration.
- [ ] Map all OAuth and API connectors, scopes, token storage and webhook validation.
- [ ] Audit tenant isolation in every model/query path, background job and file/vector access path.
- [ ] Capture backend test results and failures.
- [ ] Capture frontend build/lint results and failures.
- [ ] Inspect Alembic heads and test upgrade/restore against disposable database.
- [ ] Publish migration order and compatibility test plan.

## Guardrails

No production deployment or destructive migration is authorised by this branch. Do not treat the presence of a router, class, test or configuration option as proof that a user-facing capability is production-ready.
