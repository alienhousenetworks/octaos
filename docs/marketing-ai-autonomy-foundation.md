# Marketing AI Autonomy Foundation

## Scope of this implementation

This branch hardens the existing Marketing AI flow without replacing the campaign orchestrator, creative generation adapters, social publisher, or analytics service.

### Changes in code

- `app/services/marketing/autonomy/decision_engine.py`
  - ranks supplied calendar and news candidates using explicit relevance, freshness, confidence, velocity, persistence, and risk fields;
  - retains source URL, observation time, score, and whether a source URL was supplied;
  - treats undated news as stale/unknown rather than fresh;
  - schedules using an account timezone and optional account-specific preferred hours, returning UTC timestamps for database persistence;
  - uses documented fallback hours only when measured account-specific hours are not supplied.

- `app/services/marketing/context_radar/trend_synthesizer.py`
  - selects from all available calendar/news candidates instead of blindly using the first calendar event;
  - supplies the selected context score and source to the generation prompt;
  - tells the model to treat source text as untrusted data and forbids unsupported statistics, outcomes, awards, guarantees, product capabilities, and claims of virality;
  - marks an LLM-failure fallback as `fallback_requires_review` and avoids generic invented performance claims.

- `app/services/agents/marketing.py`
  - supports `timezone` or `account_timezone` in task parameters;
  - supports `preferred_posting_hours` as a platform-to-local-hour map;
  - prevents a fallback-generated brief from auto-approving or entering the scheduled state;
  - returns context score, source URL, and generation status for traceability.

### Explicit boundaries

This is a safety and decision-quality foundation, not a claim that every channel or media provider is production-ready. It does not add new provider credentials, bypass provider permissions, invent analytics, or automatically publish without the existing approval/status path. Instagram, Facebook, and LinkedIn publishing remain constrained by the connected account, granted scopes, media format, platform policy, and current adapter support.

## Autonomy policy to preserve

1. Missing critical brand/product facts: ask for intake or create a review-required draft; do not fabricate.
2. Trend without a source or reliable timestamp: do not describe it as verified-current or viral.
3. Unsupported claim: remove it or require evidence before publication.
4. LLM, image, or video provider failure: mark the output as fallback/unavailable and require review; never silently promote a fallback to approved.
5. Expired credentials, missing scopes, rate limits, or platform rejection: preserve the failure reason and request reconnection/retry rather than claiming success.
6. Spend, audience, channel, or campaign scope changes: enforce the tenant's explicit permissions and approval policy.
7. Analytics unavailable: represent it as unavailable, not a zero-performance observation.
8. All execution must remain tenant-scoped, auditable, idempotent, and permission-checked.

## Next implementation increments

1. Unify the 15-agent Campaign OS and autonomous pulse around shared contracts and explicit gates, preserving existing behavior behind compatibility tests.
2. Add a recovery worker/operator interface that reclaims interrupted ledger runs and retries only safe, idempotent stages.
3. Add evidence-backed brand claims and source freshness to the creative review contract.
4. Add asset provenance, generation settings, visual/audio QA, and bounded revision loops for image/video.
5. Add durable virtual-influencer identity consistency, rights/disclosure checks, and a separate workflow for real-person influencer discovery.
6. Harden each social connector with permission diagnostics, publish idempotency, post-publication verification, and explicit capability matrices.
7. Learn posting-time recommendations only from sufficient account-specific analytics; keep the fallback heuristic labeled as a fallback.
8. Add versioned industry packs for regulated and non-regulated industries, with per-pack claim rules, source requirements, KPIs, and approval thresholds.

## Verification

Run the new pure-function tests and the existing marketing evaluation suite in the repository's normal CI environment:

```bash
pytest -q tests/marketing/test_autonomy_decision_engine.py
pytest -q tests/evaluation_harness/test_campaign_15_agents_orchestration.py
```

The GitHub-connected editing environment does not execute the repository's full test suite, so passing tests must be confirmed by CI before merging.
