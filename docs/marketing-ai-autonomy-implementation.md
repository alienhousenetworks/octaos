# Marketing AI Autonomy — implementation and operational notes

This branch preserves the existing Campaign OS, Trend Synthesizer, Visual Creative
Orchestrator, publisher, and analytics service while adding evidence-aware decisions
and durable execution tracking.

## Durable execution ledger
- `MarketingExecution` stores tenant-scoped run identity, request hash, state, attempts,
  current stage, safe request/result payloads, errors, and timestamps.
- `MarketingExecutionStep` stores stage attempts, input/output summaries, state, and
  failure details.
- `MarketingExecutionLedger` enforces tenant-scoped lookups and idempotency-key reuse
  checks; a key cannot be reused with a different request payload.
- Migration `d7e8f9a0b1c2` creates the execution tables and indexes.
- Campaign OS DAG stages and autonomous marketing pulse outcomes are written to the
  ledger. Supply a stable `idempotency_key` (or a durable Campaign OS `job_id`) when
  the caller may retry the same request.

The ledger is persistence and recovery metadata, not a distributed queue or full
workflow engine. It does not itself restart workers, guarantee exactly-once external
publishing, or make third-party side effects transactional. Resume behavior must be
coordinated with the caller/worker, and provider-side idempotency is still required
where available. Failed/incomplete runs remain visible for recovery rather than
being silently reported as completed.

## Shared scheduling policy
`app/services/marketing/autonomy/policy.py` routes fallback generation, low
confidence, source-less news, weak context, missing required media, tenant-requested
review, and unsupported publisher adapters to human review. It is a conservative
operational gate, not a legal/compliance certification.

## Virtual influencer workflow
`app/services/marketing/virtual_influencer.py` creates an original fictional adult
persona brief using supplied brand facts. It requires synthetic-persona disclosure
and saves content as a review-only draft with an approval request. It does not claim
a separate durable persona registry, likeness-rights management, or automatic
publishing.

## Analytics and creative safety
- Copy prompts can use tenant-specific stored performance-learning patterns as data,
  not instructions.
- Failed Facebook/Instagram insight fetches do not replace prior metrics with
  fabricated zeros when both provider paths are unavailable.
- Trend prompts treat external context as untrusted data and prohibit invented claims.
- Readiness scores are heuristics, not calibrated probabilities.

## Production prerequisites
- Apply the Alembic migration in the target environment after checking the actual
  database revision and migration graph.
- Configure and validate image/video provider credentials and platform account scopes.
- Run the focused tests and the Campaign OS regression suite in CI.
- Add operator tooling for inspecting/retrying failed ledger runs and reconcile
  interrupted stage states.
- Verify end-to-end behavior against real connected accounts before enabling auto-publish.
