# Sales AI: end-to-end reliability foundation

## Added in this change

### Source verification

- `app/services/sales_os/source_verification.py` validates HTTP(S) source URLs, resolves and pins the TCP connection to a globally routable IP, preserves hostname-based TLS SNI/certificate validation, blocks redirects, limits response size/content type, fingerprints retrieved text with SHA-256, and requires a proposed quote to occur in the normalized source text.
- Quote verification is a deterministic gate. Generated buying signals, summaries, or model confidence cannot replace a source quote. The server must configure a high-entropy `SALES_EVIDENCE_SIGNING_KEY`; the HMAC receipt is invalid without it, and outbound dispatch remains blocked.
- Source-fetch failures return explicit reasons and do not become positive evidence.
- **Deployment note:** keep outbound egress controls at the infrastructure layer as defense in depth. The fetcher pins the resolved destination at the socket layer, but it is not a browser: it does not execute JavaScript, follow redirects, or decode compressed responses. Those outcomes are intentionally treated as unverified.

### Durable lifecycle ledger

The new SQLAlchemy tables `sales_workflow_runs` and `sales_workflow_steps` provide tenant-scoped run/step persistence, uniqueness for tenant idempotency keys, stage tracking, attempt counts, result/error payloads, and explicit state transitions. The lifecycle stages cover discovery, source verification, account enrichment, contact verification, qualification, personalization, approval, delivery, reply handling, meeting confirmation, and CRM reconciliation.

The V3 workflow now creates/claims a tenant-scoped run using an API-supplied idempotency key, records stage transitions and outcomes, persists the run ID in workflow status, and returns the run ID with terminal results. A repeated key returns the existing terminal result or active-run status rather than starting the same campaign again. Search V4 discovery jobs, cadence/outbox delivery, inbox/reply handling, meeting booking, and CRM reconciliation are not yet all unified under this same run ledger; integrate those boundaries before claiming full end-to-end resumability. A completed step is terminal and cannot be reopened accidentally. Failed/blocked steps can be retried only through an explicit transition.

## Evidence states and policy

- `exact_quote_match`: normalized quote appears in the fetched source body.
- `quote_not_found_in_source`: proposed quote does not appear; do not qualify a material claim from it.
- `source_fetch_failed`, `http_status_*`, `redirect_not_followed`, `unsupported_content_type`, and `source_too_large`: source is unavailable for verification, not evidence of absence.
- Every verification returns retrieval time and a SHA-256 text fingerprint when text was available.

## Remaining integration gates

1. Provision and rotate `SALES_EVIDENCE_SIGNING_KEY` through the deployment secret manager; without it, signed receipts cannot authorize sending.
2. Wire `create_or_get_run` and step transitions into the existing V3 workflow, cadence/outbox worker, reply handlers, calendar confirmation, and CRM sync.
3. Add migration/rollout steps for both new tables if production does not create tables from `Base.metadata`.
4. Add provider-backed integration tests with tenant-owned credentials; unit tests cannot prove external deliverability, opt-in, inbox sync, or calendar receipts.
5. Validate the pinned fetcher under the deployment's network egress policy and add integration tests for TLS failures, oversized/chunked responses, and mixed public/private DNS answers.
6. Measure labeled lead/contact outcomes before changing scoring weights or claiming a source coverage percentage.

## Production truth

This change provides verification primitives and durable workflow infrastructure. It does not claim that all existing sales paths have been switched to the ledger or that live delivery, replies, and meeting booking have been validated.
