# OctaOS Runtime Inventory — Phase 00

**Branch:** enterprise/phase-00-01-foundation  
**Method:** GitHub source tree inspection plus targeted source-file review.  
**Status:** preliminary inventory, not a complete call-graph or execution audit.

## Confirmed runtime / orchestration candidates

| Component | Source | Existing responsibility / evidence | Integration decision |
|---|---|---|---|
| Agent runtime | app/services/agents/runtime.py | Resolves agent definitions/versions, checks subscription entitlements, calls AI gateway adapter, writes execution events. Class docstring describes it as canonical for system/custom/team/marketplace agents. | Keep as the existing agent/provider execution adapter; audit how runs/tasks are persisted and whether every execution path uses it. |
| Provider-neutral protocol | app/services/agent_runtime/protocol.py | Defines AgentRequest, AgentOutcome, typed AgentEvent values and sanitisation of public event payloads. | Reuse as a contract candidate; add versioning and consistency tests before broad adoption. |
| AI gateway adapter | app/services/agent_runtime/gateway_adapter.py | Maps the existing AI gateway into the provider-neutral agent contract and checks tenant ID equality. | Keep and harden; do not replace the existing provider gateway without evidence of a gap. |
| Autonomous task runtime | app/services/autonomous_runtime/engine.py | Has a task lifecycle state machine, transition validation, tenant-scoped task records, events, handler injection and idempotency conflict handling. | Strong candidate for durable business-work lifecycle; compare its model/state transitions with existing run/task systems before selecting canonical ownership. |
| Autonomous worker | app/services/autonomous_runtime/worker.py | Celery task loads an AutonomousTask by task ID and tenant ID, then calls the autonomous runtime. | Keep as a worker adapter; audit retry, queue, registration and restart/reconciliation semantics. |
| Durable workflow checkpoints / DLQ | app/services/durable_workflows.py | Persists WorkflowCheckpoint state and has a DeadLetterService. | Reuse recovery/DLQ capabilities where suitable; prevent a second independent run-state authority. |
| Sales orchestration | app/services/sales_os/runtime/orchestrator.py | Existing SalesOrchestrator tests cover run lifecycle, idempotency, handoffs and completion against AgentRun/AgentTask-related models. | Preserve Sales domain behaviour; wrap it behind shared runtime contracts and map its state model. |
| General agent/flow engine | app/services/agents/workflow_engine.py; app/models/flow_engine.py | Existing agent definitions/versions, execution events and approval request records are used by AgentRuntime. | Keep domain/editor compatibility; map flow run IDs and events to canonical run/task references. |
| Visual automation engine | app/services/automation/compiler.py; app/services/automation/factory.py; app/services/automation/event_bridge.py | Automation graph compilation, node registry, adapters and event bridge are present in the source tree. | Preserve visual workflow definitions; adapt execution and event contracts incrementally. |
| HR workflow engine | app/services/hr/workflow/engine.py | HR-specific workflow engine exists separately. | Keep HR rules and document workflow semantics; migrate execution boundary, not HR domain logic. |
| Marketing orchestrators | app/services/marketing/campaign_os/orchestrator.py; app/services/marketing/visual_creative/orchestrator.py | Domain-specific campaign and creative orchestration paths exist. | Preserve marketing domain plans; route task lifecycle, permissions, approvals and evidence through common contracts. |
| Executive orchestrator | app/octa_orchestrator/orchestrator/manager.py and app/services/executive_os/ceo_interactive_orchestrator.py | Separate executive orchestration package and service paths exist. | Audit actual callers before deciding whether either is a user-facing runtime, an analysis subsystem, or legacy. |
| Approval service | app/core/approval_service.py | Approval requests hash the exact payload; decisions are tenant-scoped and described as staging side effects in an outbox after final approval. | Reuse this governance foundation; audit approver authority, expiry, payload revalidation and outbox delivery/reconciliation. |
| Event ledger | app/core/event_ledger.py | Appends hash-chained workflow events within the caller transaction, uses a PostgreSQL advisory lock for sequence coordination, and exposes integrity verification. | Reuse as an audit-ledger candidate; validate uniqueness/locking semantics and avoid confusing an audit ledger with the live UI event transport. |
| Governed tool registry | app/core/tool_registry.py; app/services/ai_gateway/tool_registry.py; app/services/sales_os/runtime/tool_registry.py | Multiple registries exist for governed tools, AI gateway tools, and Sales tools. | Inventory each registry's callers and permission semantics; introduce adapters/federation first, then consolidate only where capabilities overlap. |
| MCP capability layer | app/services/mcp/registry/capability_registry.py; app/services/mcp/execution/dispatcher.py; app/services/mcp/server.py | MCP registry, dispatcher, server and transport modules exist. | Reuse as a transport/capability interface; enforce the same tenant, permission, approval and audit policy as UI/API execution. |

## Key architecture conclusion

OctaOS already has useful enterprise building blocks. The risk is **fragmented ownership of lifecycle state, events, approvals, and tool permissions**, not an absence of runtime code.

Do not select a canonical runtime based only on a class name or a README claim. Select it by comparing:

1. Durable run and child-task state with tenant-scoped constraints.
2. Validated state transitions and terminal-state guarantees.
3. Idempotency under concurrent creation and retries.
4. Checkpoint/restart recovery and dead-letter replay.
5. Approval payload binding and outbox atomicity.
6. Tool permission enforcement and tenant identity propagation.
7. Event sequence, replay, sanitisation and audit integrity.
8. Current callers and compatibility cost across departments.
9. Test coverage and actual CI outcomes.

## Proposed target boundaries

- **Canonical work lifecycle:** one owner for run/task identity, status, retry/cancel/resume and parent-child relationships.
- **Agent execution:** reuse AgentRuntime + provider-neutral protocol + AI gateway adapter.
- **Domain workflow definitions:** Sales, Marketing, HR, Support, Real Estate, Field Sales and automation graphs remain domain-owned.
- **Governance:** one consistent permission/entitlement/approval policy boundary.
- **Events:** durable audit ledger and UI delivery/replay are related but distinct responsibilities.
- **Workers:** Celery tasks execute canonical work by stable IDs and always reload tenant-scoped records from durable storage.
- **External side effects:** approval-bound payloads, idempotency keys, provider receipts and reconciliation; never infer success from a worker returning without an exception.

## Decisions deferred until evidence is gathered

- Whether AutonomousTask or AgentRun/AgentTask should own canonical business-work identity.
- Whether WorkflowCheckpoint becomes a checkpoint table under the canonical run ID or is retained behind an adapter.
- Which tool registry is authoritative and which registries are adapters.
- Whether the event ledger is the authoritative audit record for all workflows or only governed workflows.
- Which domain engines can be migrated by adapter and which need explicit lifecycle refactoring.

These decisions require call-graph inspection, schema/index review, concurrency tests, recovery tests, and current CI results.
