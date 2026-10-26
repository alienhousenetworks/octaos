# OctaOS API, Worker and Test Surface — Phase 00

**Source:** repository tree on main, inspected 2026-10-26.  
**Scope:** filename inventory only; route-to-service call graph and auth policy still require inspection.

## API endpoint modules

The v1 router registration includes the following endpoint modules. Presence in the router is not proof that every route is authenticated, tenant-safe, fully implemented, or production-ready.

- **Identity and administration:** auth, tenants, system_admin, rbac, audit, usage, enterprise, integrations.
- **Core workforce and coordination:** rooms, commands, coordination, manager, dashboard, llm, autonomous_work.
- **Automation and workflow:** automations, automation_nodes, automation_documents, schedules, data_collection.
- **Sales and CRM:** leads, sales_crm, sales_inbox, sales_manager, sales_os, sales_platform, sales_inbound_webhooks, deal_rooms, sales_real_estate, field_sales.
- **Marketing and media:** marketing, videos, buffer_oauth, meta_oauth, linkedin_oauth, heygen, google.
- **HR and people operations:** hr, hr_people, hr_workforce, hr_copilot, hr_enterprise, hr_compensation_read, hr_lifecycle, hr_workflow, candidate_portal.
- **Support and knowledge:** support, knowledge_connectors.
- **Executive and data systems:** ceo, ceo_v5, federated_learning.

Additional routers are registered through the versioned API structure, including a v2 health endpoint. See app/api/v1/api.py and app/main.py.

## Worker surface

- app/worker/tasks.py is the discovered central worker task module.
- app/core/celery_app.py configures Redis as the broker by default, named queues including a dead-letter queue, routing rules, scheduled jobs, and a task-failure signal that attempts DLQ routing.
- app/services/autonomous_runtime/worker.py defines the octaos.execute_autonomous_task entry point, which reloads an AutonomousTask by task ID and tenant ID before dispatch.

**Required follow-up:** inventory every registered task name, schedule, retry policy, idempotency strategy, tenant propagation, outbox/reconciliation path, and DLQ replay policy. Confirm scheduled tasks are registered and worker/broker health is observable without exposing broker URLs.

## Model families requiring mapping

The source tree includes separate model families for agent runtime, autonomous work, flow engine, automation graphs, enterprise workflow checkpoints/DLQ, executive workflow events/approvals/outbox, HR, Sales workflow, Real Estate, Field Sales, MCP, and general workflows.

The next audit must identify which model is authoritative for each business run, how records relate across families, and which tables are tenant-scoped with enforced constraints/indexes.

## Test surface

The repository tree contains 147 Python test files at the time of inspection. This is a source-tree count, not a statement that all tests pass or are executed by CI.

Existing focused tests cover runtime protocol, autonomous idempotency, tool registry, workflow governance, entitlements, tenant-scoped analytics, and department workflows. A complete test inventory must map each suite to CI workflows and identify gaps for:
- forged tenant/organization context
- authentication and permission bypass
- background job tenant propagation
- run recovery after worker restart
- concurrent idempotency collisions
- approval expiry/revocation and exact-payload binding
- external action timeout/reconciliation
- migrations from a prior production schema
- frontend build, typecheck, lint and critical user journeys

## Phase 00 completion criteria

This file is only the initial source surface map. Phase 00 remains open until endpoint-level authentication/tenant policies, service/model call paths, task registration, connector behavior, migration history, and baseline test results are recorded.
