# Sales AI workflow and frontend readiness audit

Audit date: 2026-10-25  
Repository: `alienhousenetworks/octaos`

This document separates implemented workflow behavior from capabilities that still require integration or live-provider verification. The Sales home UI should guide users through the actual sequence without implying that a configured provider, generated draft, or proposed meeting is proof of a completed action.

## User journey

1. **Configure the business and ICP** — the tenant's Business Profile supplies company/website, service, target industries and countries, budget, USP, offer details, and additional targeting instructions. These inputs inform discovery and personalization.
2. **Discover accounts and contacts** — Search V4 plans bounded combinations of industries, geographies, and buyer roles, with bounded adaptive expansion. Existing provider adapters include Apollo, Hunter, Google Places, and credential-dependent Apify/source paths. Optional providers are not guaranteed to be configured or available.
3. **Enrich and verify** — weak or missing contact data can be sent through enrichment. Preserve useful account-level discoveries that have no verified contact and label them for contact research. A provider result alone does not establish deliverability or current employment.
4. **Qualify and score** — use business-fit, pain, intent, industry, growth, and contact context where present. Unknown values must stay unknown; don't invent a score or buying signal to fill gaps. The documented historical V3 weighting is budget 25%, pain 25%, intent 20%, industry 15%, growth 10%, contact 5%; validate current runtime use before presenting it as a guaranteed universal formula.
5. **Research and personalize** — use available company context such as sourced news/jobs, verified lead fields, the tenant's offer/USP, and learned messaging strategy. A generated claim or LLM confidence alone is not evidence.
6. **Prepare outreach** — produce a lead-specific draft and show its evidence and readiness blockers. Draft generation is not sending.
7. **Authorize delivery** — the central dispatcher rechecks tenant scope, outbound authorization, contact readiness, suppression/do-not-contact, and source verification. Automatic sending is disabled unless the tenant explicitly enables it. WhatsApp also needs recipient-specific opt-in evidence. Missing requirements must block delivery.
8. **Follow up** — cadence/outbox paths must not start follow-ups when the first authorized touch did not succeed. The intended historical cadence is Day 1 email, Day 3 LinkedIn, Day 5 email, Day 8 WhatsApp, Day 12 human call task; channel support and permission must be confirmed for each actual touch.
9. **Receive and classify replies** — inbound email/webhook/poll paths match a reply to a lead, record the conversation, and classify intent. Declines/unsubscribes must not trigger automated persuasion; uncertain or question replies should be handled through the configured review policy.
10. **Book and confirm meetings** — only a real calendar event receipt should be shown as booked. Booking requires a timezone-aware time, calendar availability, and an actual Google Calendar/Meet confirmation; never fabricate a meeting link or mark a lead booked based only on generated text.
11. **Reconcile and learn** — reconcile actual provider receipts and CRM state. LearningLoop can use recorded replies, meetings, conversions, and negative outcomes; do not display simulated learning or revenue as actual results.

## Current implementation status based on repository documentation and open/merged change descriptions

### Implemented foundations

- Search V4 planning across configured industry/geography/buyer-role dimensions and up to three bounded adaptive expansion rounds.
- Source verification with URL checks, pinned public-IP connections, redirect blocking, bounded response handling, SHA-256 fingerprints, and exact quote matching.
- Signed evidence receipts using the server-only `SALES_EVIDENCE_SIGNING_KEY`; the central outbound gate rejects absent/invalid/stale or mismatched evidence.
- Tenant-scoped durable V3 run/step ledger, request idempotency, stage tracking, attempt counts, and explicit state transitions.
- Central dispatch authorization for outbound channels, suppression and tenant checks; WhatsApp recipient-specific opt-in requirements.
- Sales settings UI/API controls that default to disabled/unknown; outreach draft status is distinct from actual sent status.
- Meeting booking requires a concrete timezone-aware time and a real calendar receipt; fabricated meeting links and hardcoded revenue increments were removed.
- Focused Sales quality/dispatcher and Search V4 tests were reported passing in GitHub Actions run #122 for PR #5, with the exact covered suite described in that PR.

### Known gaps; do not label Sales AI end-to-end production-ready yet

- Search V4 jobs, cadence/outbox delivery, inbox/reply handling, calendar confirmation, and CRM reconciliation are **not yet all unified under the same durable run ledger**.
- Real provider credentials, current-employment checks, email deliverability, inbound webhook/poll flows, calendar booking, and external send receipts need tenant-authorized integration tests.
- Production deployment must provision `SALES_EVIDENCE_SIGNING_KEY` in the server-side secret manager; never put it in frontend configuration or commit the value.
- Production schema rollout must verify that the two ledger tables have a reviewed migration on the actual Alembic head.
- Source retrieval does not execute JavaScript or follow redirects; unsupported sources must remain unverified.
- Provider readiness/configuration is not proof of live health, exhaustive internet coverage, successful delivery, or booked meetings.
- The detailed legacy agent-flow document contains historical descriptions (including a qualification shortcut and older status behavior). Treat the current evidence-first gates and newer reliability notes as authoritative where they conflict.

## Frontend interaction model

Keep the top-level Sales home focused on four sequential actions:

1. **Define target market** → Business Profile, ICP, offer and channel policy.
2. **Find and research prospects** → search brief, provider availability, coverage, source evidence and missing-contact queue.
3. **Review and qualify leads** → CRM list, lead dossier, qualification rationale, source citations, suppression and readiness blockers.
4. **Engage and book** → outreach drafts/approval queue, delivery receipts, unified inbox, reply classification, calendar connection and confirmed meetings.

Keep AI agents, campaign sequencing, workflows, sales intelligence, analytics and industry packs available as secondary tools. Avoid presenting agent animations as live execution unless they are driven by persisted run/step data. Every integration screen should distinguish **Not configured**, **Configured**, **Unavailable**, **Needs authorization**, and **Verified by a live receipt**.

## UX and data-truth acceptance criteria

- One restrained visual system: graphite/neutral surfaces with muted indigo as the only accent; status should not depend on a rainbow of colors.
- No fake KPI defaults, default lead scores, invented source coverage, invented meeting links, or hardcoded revenue.
- Empty, loading, unavailable, blocked, partial, and successful states must be distinct and actionable.
- Show why a prospect was selected, which source supports each material claim, when it was retrieved, and what remains unverified.
- Display each workflow run's actual status, stage, last update, attempts, blockers, and provider receipt when the API exposes them. Never infer success from a request being accepted.
- Keep channel permissions, WhatsApp opt-in, suppression, evidence validity, and human approvals visible before enabling automation.
- Preserve tenant scoping, existing routes, and current backend contracts. Do not add UI controls that imply unsupported backend actions.
- Validate with TypeScript/production build, authenticated API smoke tests, and browser/E2E coverage for the full user journey.

## Change made in this iteration

The Sales home has been redesigned as a guided prospect-to-meeting entry point. It uses the existing navigation callbacks, displays only the current loaded lead count, provides direct routes to targeting, prospecting, CRM, inbox, agents, campaigns, workflows, intelligence and analytics, and explicitly explains that drafts, provider configuration, and proposed meetings are not verified outcomes.

This is a frontend usability improvement, not a claim that all backend lifecycle gaps or live-provider checks have been completed.
