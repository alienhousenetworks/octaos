# Collaborative AI Workforce — implementation contract

## Product behavior
- The bot-first assistant is the default entry point; the legacy dashboard remains available at /app/home and through the Classic UI switch.
- Specialist bot routes remain domain-owned. The shared assistant submits goals to the existing orchestration API rather than replacing Sales, Marketing, HR, Support, or existing workflow services.
- The central knowledge hub is the tenant-scoped source for reusable company facts. Existing KnowledgeDocument, knowledge connector, and knowledge ACL mechanisms must be reused where possible.

## Agent-to-agent collaboration contract
Every inter-agent request must carry tenant ID and requesting principal from authenticated server context (never trusted from model output); parent task/run ID, correlation ID, request and response IDs; requesting agent, target agent/capability, intent, structured input schema, deadline and priority; data classification and permission decision; state (queued, accepted, running, waiting_for_data, completed, failed, cancelled, or timed_out); evidence/source references, sanitized result, error category and timestamps.

Agents may delegate only capabilities available to the tenant and authorized principal. A receiving agent cannot elevate privileges, override policy, or execute external side effects merely because another agent requested them. High-risk actions must be independently authorized at execution time.

## Knowledge lifecycle
- Distinguish task context from reusable company knowledge.
- Facts should include source, source authority, observed/verified timestamps, validity/freshness, classification, approval-for-external-use, tenant scope, version and change history.
- Freshness checks should be event-driven when providers support change notifications, scheduled where appropriate, and on-demand before consequential actions.
- If a source is unreachable, report unknown/unavailable; never imply freshness was verified.
- When a knowledge gap remains, ask a targeted question in the current conversation. Save the answer only to the correct scope, and require review/approval for policy or authoritative changes.
- On updates, invalidate relevant cached retrieval and flag dependent plans for revalidation.

## Cross-agent execution
Use the existing durable runtime/work graph where possible. Parent tasks own child task references and dependencies. Persist accepted work before acknowledging it; use idempotency keys and transactional outbox/event delivery; checkpoint waiting states; support cancellation, bounded retry and restart recovery. Agent responses should be structured and evidence-bearing, not just free-form prose.

## UI contract
- New default route: /app/assistant.
- /app/home remains the classic overview/dashboard and is reachable via the profile menu Switch to Classic UI.
- Classic dashboard offers Switch to New UI.
- The assistant exposes live processing, request failures, structured execution responses and no fabricated success states.
- Keep existing bot-specific pages, knowledge, approvals, integrations, HR, sales, marketing and analytics accessible.

## Acceptance gates
1. Unauthenticated users are redirected to login by the existing workspace guard.
2. Assistant calls the authenticated orchestration API; errors are displayed as errors.
3. Classic/new UI switching preserves the same tenant data and existing routes.
4. Tenant isolation is tested for knowledge retrieval, agent messages, child tasks, and integration calls.
5. Duplicate inter-agent requests cannot duplicate protected side effects.
6. Knowledge conflicts, stale sources, and unavailable connectors are surfaced, not guessed.
7. Human approvals and provider permissions are enforced on the server.
8. Existing HR, Sales, Marketing, Support and dashboard regression suites pass.

## Implementation status
This contract describes required behavior, not proof that every backend collaboration, sync, OAuth, and recovery capability already exists. Source-level implementation and CI evidence must be recorded per acceptance gate.
