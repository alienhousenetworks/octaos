# Sales AI Evidence-First Execution (v1)

## What changed

This change tightens the legacy V3 workflow and broadens Search V4 query coverage without removing existing provider connectors.

### Deterministic outbound gate

`app/services/sales_os/quality_gates.py` implements `assess_outreach_readiness`. The V3 workflow now requires all of the following before dispatch is attempted:

- `sales_ai_auto_send_enabled=true` in the tenant's `APICredential(provider="sales").settings`.
- `outbound_permission_state="granted"`.
- The discovered contact status is `READY`.
- A real contact name (placeholder labels such as `Decision Maker` are rejected).
- An email or phone route.
- An evidence URL and at least one supporting quote, buying signal, pain point, news item, or hiring signal.
- No suppression or do-not-contact flag on the candidate.

If any gate fails, the workflow stores the lead/draft and a list of blockers rather than attempting delivery. A failed LLM draft no longer falls back to generic copy. Missing pain points no longer become the fabricated-looking phrase "operational bottlenecks", and missing scores are not silently replaced with 50. An LLM-generated pain-point list by itself does not satisfy the evidence gate; the record needs a sourced excerpt/buying signal or a news/hiring item with its own valid source URL.

Email and WhatsApp permissions are separate. WhatsApp dispatch additionally requires `whatsapp_permission_state="granted"` and recipient-specific consent metadata on the lead (`whatsapp_opt_in=true`, `whatsapp_opt_in_source`, and `whatsapp_opt_in_at`). A tenant-wide setting cannot authorize messages to every phone number. The central touch dispatcher re-checks authorization for email/WhatsApp, automated LinkedIn requires the same tenant authorization, and outbox no longer sends email directly when its tenant-scoped lead record is missing. Future cadence touches are not staged unless the first authorized touch actually succeeds.

These settings are explicit opt-ins. Leaving them unset blocks automatic dispatch by default; this is intentional. Tenant configuration must reflect actual permission and applicable law, not just a desire to send messages.

## Discovery persistence

Direct lead sourcing now preserves useful account-level discoveries even when no contact is available. Such records receive `needs_contact_research`, score remains unknown, and the data payload records source URL, evidence excerpt, retrieval time, and the fact that contact verification is still unknown. They are queued for enrichment rather than silently discarded.

A discovery provider's returned contact is not, by itself, proof of deliverability or current employment.

## Search coverage

Search V4's planner now builds a bounded set of query tasks covering multiple configured industries, geographies, and buyer roles. It covers each dimension before filling in additional combinations, then adds distributed news and hiring searches and credential-gated public social searches. The plan is bounded to 12 ICP combinations before source-specific task expansion and remains subject to provider availability, duplicate-query filtering, and budget reservation.

Search V4 also performs up to three bounded adaptive expansion rounds, using newly discovered explicit requests, hiring signals, trigger events, and company domains to propose follow-up web searches and first-party company-page fetches. Each round is persisted before execution and stops when no new tasks are proposed, the budget prevents expansion, cancellation is requested, or the round ceiling is reached. This improves breadth; it does **not** guarantee that every page on the internet was searched. The source catalogue is not a guarantee that a provider is active. Provider tasks still report unavailable, missing-credential, blocked, or failed states honestly.

## Verification

New tests:

- `tests/test_sales_quality_gates.py`: default-off sending, permission gates, evidence requirements, contact identity, suppression.
- Expanded `tests/test_search_v4.py`: multiple industry/geography/buyer-role coverage.

GitHub Actions workflow `.github/workflows/sales-ai-quality.yml` runs these tests on relevant pull requests and branch pushes.

## Remaining work before production

This patch is a safety and discovery-quality foundation, not the complete autonomous sales workforce. Still required:

1. Run and pass CI; exercise integration tests against the actual database and workers.
2. Replace legacy contact status `READY` with an explicit verification object backed by tiered syntax, deliverability, employment, suppression and channel permission checks.
3. Persist Search V4 records/evidence as canonical Sales CRM evidence rather than only returning a search batch.
4. Unify V3, direct discovery, Search V4, SalesPipeline and cadence under one durable run/task lifecycle.
5. Add explicit UI for source readiness, search coverage, evidence dossiers, blockers, approvals and actual provider receipts.
6. Add idempotent outbox dispatch and reconciliation tests for worker crashes/retries.
7. Evaluate scoring and personalization against labeled real outcomes before tuning weights.
8. Conduct a controlled live-provider test with tenant-authorized credentials and verify actual delivery receipts.

No live provider delivery or production deployment is claimed by this patch.
