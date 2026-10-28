# Bidirectional AI Collaboration — Repository Audit and Remediation

Audit date: 2026-10-28
Repository: https://github.com/alienhousenetworks/octaos
Audited ref: `main` at the start of this change
Status: source-level review; tests have not been executed in this remote-edit session.

## Summary

The repository already contains a substantial first implementation. This is not a greenfield feature. Existing components include:

- `app/services/collaboration/contracts.py`: Pydantic task/result contracts and recursive secret-key redaction.
- `app/services/collaboration/provider_registry.py`: provider catalogue, tenant credential lookup, capability filtering and configured limits.
- `app/services/collaboration/engine.py`: outbound model delegation, inbound employee delegation, task persistence, status polling and cancellation.
- `app/services/collaboration/orchestrator.py`: lineage/depth/child-count checks, task fingerprints and signed webhook dispatch.
- `app/services/collaboration/execution_bridge.py`: policy evaluation and tool execution bridge.
- `app/api/v1/endpoints/plugins.py`: provider listing, task submit/status/cancel and execution-bridge endpoints.
- `app/services/mcp/external_client.py` and `app/services/mcp/connectors/external_mcp.py`: generic outbound MCP client and tenant-scoped external MCP adapter.
- `frontend/src/components/views/system-mcp-view.tsx`: existing MCP UI already requests `/plugin/collaboration/providers`.
- `tests/mcp/test_bidirectional_collaboration.py` and `tests/mcp/test_universal_plugin_gateway.py`: existing test coverage.

The user-supplied earlier test transcript is not treated as proof that the current branch or live providers have been tested during this change.

## Confirmed issues from source review

### P0 — Execution bridge could bypass approval for admin credentials

In `app/services/collaboration/execution_bridge.py`, an admin credential overwrote a policy decision of `queue_approval` with `allow_auto`. This conflated permission to access the API with approval to perform a high-risk action. The bridge also allowed execution when no tenant-scoped `DelegationReceipt` existed, so the bridge was not strictly bound to a durable collaboration task.

**Remediation in this branch:** require a tenant-scoped receipt, reject credential/tenant mismatch, and never let the credential role erase a policy-engine approval requirement. Regression tests were added for both cases.

### P1 — Asynchronous tasks can remain queued without a visible worker handoff

In `AICollaborationEngine.submit_inbound_task`, `async_execution=True` persists the message as `queued` and returns. The inspected method does not enqueue a durable worker job or execute the task. No worker handoff is visible in that method. A queued record alone does not constitute asynchronous execution or restart recovery.

**Required next change:** integrate this path with the repository's canonical durable execution queue/runtime, identify the actual worker entry point, and test worker restart/retry/idempotency. Do not substitute an in-process `asyncio.create_task` for durable execution.

### P1 — Provider “connected” status overstates what is verified

In `AIProviderRegistry.get_connected_providers`, a decryptable non-placeholder API key sets `status="connected"` and `is_connected=True`. The `verify_health` parameter is not used in the inspected implementation. A valid-looking stored credential proves configuration, not successful authentication, current reachability, quota, or successful inference.

**Required next change:** expose separate configured, health-checked, and inference-verified states. Only label a provider reachable after an explicit, bounded health/inference check. Do not run a paid model call just to render a provider card.

### P1 — Provider eligibility and cost semantics need correction

The inspected `get_eligible_providers_for_task` requires `provider.cost_ceiling_usd >= max_cost`. If `max_cost` represents the task's maximum permitted spend, this reverses the intended comparison: a provider with a larger configured ceiling is not necessarily eligible, and a smaller provider ceiling can still safely serve a task. Define task budget versus provider account ceiling explicitly and enforce the minimum of the two at dispatch time.

### P1 — Inbound synchronous execution lacks visible deadline enforcement

The request contract has `timeout_seconds`, but the inspected synchronous inbound path calls `mcp_server.registry.call_tool` without applying that request timeout in the shown code. Verify the downstream dispatcher has an enforced timeout; otherwise add bounded execution and a recoverable timeout state.

### P1 — Webhook delivery is fire-and-forget in synchronous path

The inspected engine starts webhook delivery with `asyncio.create_task`. This is not durable delivery and can be lost on process shutdown. The fallback secret expression also deserves review: webhook signing must use a dedicated tenant-scoped secret, never a display/token preview. Move delivery to the durable queue/outbox and store delivery attempts/status.

### P1 — Result schema validation is incomplete

Outbound validation currently checks only the top-level `required` keys. It does not validate the complete JSON Schema, nested types, additional properties, or content size. Use a maintained JSON Schema validator with bounded payload size and return explicit validation evidence.

### P1 — Cancellation is state-only unless workers cooperate

The inspected `cancel_task` changes the database status but does not signal a running provider request or worker. Implement cancellation propagation in the canonical runtime and prevent late worker completion from overwriting a cancelled state.

### P2 — Audit/error handling needs tightening

The plugin endpoints return raw exception text in some error responses. Ensure external responses are sanitized while full details remain in protected logs. Confirm audit records are written for submission, result retrieval, cancellation, webhook attempts, provider failures and approval decisions.

### P2 — Media and URL inputs need SSRF controls

File magic-byte validation is useful but does not by itself protect URL ingestion or webhook delivery. Any server-side URL fetch needs HTTPS policy, DNS/IP validation, private/loopback/link-local address blocking, redirect revalidation, size/time limits and protection against DNS rebinding. Apply equivalent controls to caller-provided webhook URLs.

## Remediation made in this branch

- Updated `app/services/collaboration/execution_bridge.py` to require a durable tenant-scoped receipt, check tenant binding, and preserve approval requirements for admin credentials.
- Added regression tests in `tests/mcp/test_bidirectional_collaboration.py` for missing receipts and approval bypass.
- No claim is made that the new tests pass: this session edited files through the GitHub API and did not execute the repository's test runner.

## Acceptance criteria before production

1. Run focused collaboration and MCP tests, then the full backend suite.
2. Add a real configured-provider smoke test in a controlled environment; keep mock tests separately labelled.
3. Prove async tasks are durably enqueued and survive worker restart.
4. Prove task timeout/cancellation, idempotency, and webhook retries end-to-end.
5. Add complete schema validation and cost-budget enforcement.
6. Add SSRF tests for webhook and media URLs.
7. Run frontend typecheck/build and verify provider/task UI against real endpoint contracts.
8. Perform a multi-tenant security review and verify existing autonomous workflows remain unaffected.

## Important scope note

This branch is a targeted security remediation, not a claim that every collaboration gap above is already fixed. The durable async worker handoff and live provider health verification require integration with the actual runtime and deployment configuration; they should not be simulated or declared complete without evidence.


## Follow-up remediation (2026-10-28)

- **Async handoff:** committed inbound task/receipt rows are dispatched to the existing Celery `main-queue`; worker imports are registered in the existing Celery app. Failed enqueue is persisted as `DURABLE_HANDOFF_FAILED`, not left queued.
- **Worker lifecycle:** the worker reloads the credential with matching tenant scope, applies a bounded timeout, writes result/evidence to the existing collaboration records, and checks cancellation before finalizing. Cancellation also attempts to revoke the Celery task.
- **Provider status:** a decryptable credential is labelled `configured`, not `connected`; `is_connected` remains false until live reachability is actually established. Configured providers can be selected as candidates, but the real dispatch must succeed to prove connectivity.
- **Budget semantics:** task spend budget is no longer compared to the provider account ceiling. The dimensions are treated separately; provider account ceilings at or below zero are not a usable dispatch budget.
- **Output contract:** full JSON Schema Draft 2020-12 validation (including nested types, constraints, required properties and additional properties) plus a 1 MB response cap are applied to outbound and inbound results. The `jsonschema` dependency is declared.
- **Timeout/cancellation:** provider calls and employee calls are bounded. Synchronous timeout is persisted as `EXECUTION_TIMEOUT`; late worker completion does not overwrite a cancelled status.
- **Webhook delivery:** the process-local `asyncio.create_task` path was removed. Webhook delivery is a separate Celery task with retries so a callback retry does not rerun the employee action.
- **SSRF controls:** callback and input-reference URLs must be HTTPS, reject embedded credentials/non-default ports/local/private/link-local/reserved destinations, disable redirects, and bypass environment proxies. Every webhook retry revalidates the destination.
- **Tests added/updated:** provider configuration-vs-connectivity expectations, SSRF rejection cases, and nested JSON Schema validation cases.

**Verification caveat:** these changes were committed remotely through GitHub APIs. Tests have not been executed in a local runner in this session, and no passing CI result has been observed. DNS resolution is validated before requests but the implementation does not pin the resolved address to the socket, so production-grade DNS-rebinding resistance should be completed at the HTTP transport/network egress layer. Webhook delivery is queued durably after task completion; a broker outage at the exact moment of enqueue is logged and needs operational monitoring/reconciliation for guaranteed delivery.
