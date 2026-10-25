# Marketing AI Autonomy Foundation — implementation notes

This branch preserves the existing Campaign OS, Trend Synthesizer, Visual Creative
Orchestrator, publisher, and analytics service while adding evidence-aware autonomy
controls and a virtual-influencer brief workflow.

## Shared decision policy
`app/services/marketing/autonomy/policy.py` makes the schedule decision explicit:
fallback generation, low confidence, source-less news, weak context, required media
failure, or a tenant-level approval requirement route the draft to human review.
This is not a legal compliance certification and does not bypass platform scopes.

## Virtual influencer workflow
`app/services/marketing/virtual_influencer.py` creates a structured fictional adult
persona brief from supplied brand facts. It rejects incomplete responses and requires
synthetic-persona disclosure. The current integration is a draft/review workflow; it
does not claim a durable influencer registry, likeness rights management, provider
availability, or automatic publishing.

## Remaining production prerequisites
- Configure and validate image/video provider credentials and model availability.
- Verify connected social-account scopes and platform-specific publishing requirements.
- Run the focused tests and the existing Campaign OS regression suite in the repo's
  supported environment.
- Add persistent run/step execution records and migration-backed retry/idempotency
  before describing the complete marketing workflow as crash-resumable.
- Add tenant-configurable approval policies to persisted settings rather than trusting
  per-request parameters alone.
- Calibrate context and confidence thresholds against real account outcomes; defaults
  are heuristics, not measured performance claims.
