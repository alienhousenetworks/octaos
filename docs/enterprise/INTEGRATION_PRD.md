# OctaOS Enterprise Integration PRD

**Status:** Active implementation plan  
**Repository:** alienhousenetworks/octaos  
**Base branch:** main  
**Migration strategy:** incremental, compatibility-first; no big-bang rewrite.

## Product outcome

OctaOS must provide a tenant-safe, durable and observable AI workforce platform where users can delegate business goals, supervise agent work, approve consequential actions, recover interrupted workflows and inspect evidence for reported outcomes.

## Non-negotiable principles

1. Preserve working department capabilities and public API contracts unless a versioned migration is approved.
2. Use one canonical execution runtime for newly migrated workflows; adapt legacy paths before retiring them.
3. Derive tenant scope from validated identity and membership, never from client-supplied tenant headers alone.
4. Persist run/task/approval state and recover after worker or process restart.
5. Treat external side effects as at-least-once delivery risks; use idempotency, deduplication and reconciliation.
6. Distinguish proposed, approved, submitted, delivered and verified outcomes.
7. Never turn missing credentials, unavailable APIs, simulations or errors into successful live outcomes.
8. Keep domain logic in Sales, Marketing, Support, HR, Operations, Finance, Field Sales and Real Estate modules while sharing runtime, governance and observability.
9. Make migrations additive and staged; provide regression tests and rollback plans.
10. Release only against demonstrated acceptance gates.

## Phase plan

### Phase 00 — repository and compatibility baseline
- Map API routers, services, agents, workflow engines, Celery tasks, integrations, database models, migrations and frontend entry points.
- Inventory current runtime candidates and identify which are canonical, legacy, or domain-specific.
- Record baseline backend tests, frontend build/lint, migration status and CI results.
- Classify capabilities: tested, implemented/unverified, partial, planned, unavailable.
- Deliver source-linked inventory, risk register, dependency map and phased tickets.

**Exit:** every proposed migration has an identified source path, consumer impact and test strategy.

### Phase 01 — secure foundation
- Make authenticated identity the authority for tenant context; ignore/reject spoofed tenant headers.
- Fail closed on insecure production secret configuration.
- Audit permissions, tenant filters, file/knowledge access, background tasks, webhook verification and credential storage.
- Add cross-tenant regression tests.

**Exit:** tenant-spoofing tests pass and production startup cannot silently use insecure defaults.

### Phase 02 — canonical durable runtime
- Define versioned run/task/event/tool/approval/result contracts.
- Persist lifecycle state, checkpoints, retry budgets, deadlines, cancellation and resume.
- Add idempotency keys and reconciliation for external side effects.
- Wrap existing execution paths with compatibility adapters.
- Migrate one workflow at a time; retire old paths only after parity.

**Exit:** restart/retry tests prove recoverability without blind duplicate side effects.

### Phase 03 — workforce UI and event stream
- Use stable run/task IDs and typed events.
- Rehydrate UI state after refresh/reconnect.
- Show queued, running, waiting-for-approval, failed, cancelled, completed and verified states distinctly.
- Provide authorised retry, resume, cancel and escalation actions.

**Exit:** UI state matches persisted server state after reconnect and failures.

### Phase 04 — provider and tool contracts
- Standardise input/output schemas, timeouts, budget limits, permission scopes and failure semantics.
- Validate tool results and distinguish model proposals from executed actions.
- Track usage and cost by tenant/run.

**Exit:** a test workflow invokes an authorised tool and reports real results or explicit failure.

### Phase 05 — integrations and approvals
- Reuse existing OAuth/API connectors through shared connection/action contracts.
- Add connection health, scopes, token refresh, rate limits, approval gates, action records and reconciliation.
- Capture provider identifiers and verification evidence.

**Exit:** real test-account action, rejection, failure and timeout paths are covered.

### Phase 06 — flagship real workflow
- Select the best existing workflow after discovery; candidate is social publishing.
- Review exact destination, account, payload and schedule before approval.
- Execute through a real connector, persist provider references and verify when supported.
- Test disconnect, approval rejection, timeout, retry and duplicate submission.

**Exit:** end-to-end workflow and recovery tests pass; no fake live success.

### Phase 07 — evidence, memory and audit
- Separate business records, run state, conversation history and reusable memory.
- Add source references, versioned prompts/workflows and attributable audit events.
- Label measured, inferred, simulated and unavailable data.

**Exit:** operators can reconstruct what happened, under whose authority and from what evidence.

### Phase 08 — department migration
Migrate Sales, Marketing, Support, HR, Operations, Field Sales, Real Estate, Finance and executive reporting incrementally. Preserve domain-specific business logic and apply the shared security, durability, evidence and recovery gates to every module.

**Exit:** each module has passing domain acceptance and platform regression tests.

### Phase 09 — capability packs, MCP and entitlements
- Version capability manifests, dependencies and permissions.
- Enforce plan limits and tool scopes on the backend.
- Support safe install, upgrade, rollback and admin visibility.

**Exit:** installed capabilities cannot bypass tenant, role or entitlement checks.

### Phase 10 — enterprise release
- Validate backup/restore, migrations, deployment rollback, alerts, traces, queue health and incident procedures.
- Run security, load, failure-injection and regression suites.
- Publish a release report and known-limitations register.

**Exit:** no unresolved critical security/data-integrity defects; SLOs are measured and demonstrated before being promised.

## Acceptance states

- proposed: model or agent recommendation only.
- awaiting_approval: action is blocked until authorised approval.
- submitted: provider accepted the request or returned a submission reference.
- delivered: destination/provider indicates delivery where such status exists.
- verified: outcome checked against an authoritative provider/business-system source.
- failed, unavailable, simulated: never reported as verified success.

## Phase reporting

For every phase, record changed files, APIs and migrations; tests actually run; pass/fail results; known limitations; deployment/rollback notes; and the exit-gate decision. Continue to the next phase automatically only when the current gate passes. Production deployments, destructive migrations and consequential external actions require appropriate authorisation.
