# Sales AI: end-to-end reliability foundation

## Added in this change

### Source verification

- `app/services/sales_os/source_verification.py` validates HTTP(S) source URLs, blocks local/private/reserved destinations, rejects redirects, limits response size/content type, fingerprints retrieved text with SHA-256, and requires a proposed quote to occur in the normalized source text.
- Quote verification is a deterministic gate. Generated buying signals, summaries, or model confidence cannot replace a source quote.
- Source-fetch failures return explicit reasons and do not become positive evidence.
- **Deployment note:** DNS preflight alone is not a complete defense against DNS rebinding. Before exposing arbitrary URL fetching to untrusted tenants, pin the resolved destination at the transport/socket layer and enforce network egress policy. Keep this worker behind that control.

### Durable lifecycle ledger

The new SQLAlchemy tables `sales_workflow_runs` and `sales_workflow_steps` provide tenant-scoped run/step persistence, uniqueness for tenant idempotency keys, stage tracking, attempt counts, result/error payloads, and explicit state transitions. The lifecycle stages cover discovery, source verification, account enrichment, contact verification, qualification, personalization, approval, delivery, reply handling, meeting confirmation, and CRM reconciliation.

The ledger intentionally does not pretend that legacy V3 and Search V4 are already routed through it. Integration must happen at each real workflow boundary; use the ledger around side effects before enabling retries. A completed step is terminal and cannot be reopened accidentally. Failed/blocked steps can be retried only through an explicit transition.

## Evidence states and policy

- `exact_quote_match`: normalized quote appears in the fetched source body.
- `quote_not_found_in_source`: proposed quote does not appear; do not qualify a material claim from it.
- `source_fetch_failed`, `http_status_*`, `redirect_not_followed`, `unsupported_content_type`, and `source_too_large`: source is unavailable for verification, not evidence of absence.
- Every verification returns retrieval time and a SHA-256 text fingerprint when text was available.

## Remaining integration gates

1. Wire `fetch_and_verify_source` into the canonical discovery-to-qualification boundary and persist its receipt with the lead dossier.
2. Wire `create_or_get_run` and step transitions into the existing V3 workflow, cadence/outbox worker, reply handlers, calendar confirmation, and CRM sync.
3. Add migration/rollout steps for both new tables if production does not create tables from `Base.metadata`.
4. Add provider-backed integration tests with tenant-owned credentials; unit tests cannot prove external deliverability, opt-in, inbox sync, or calendar receipts.
5. Add DNS-pinned HTTP transport / outbound egress controls before enabling arbitrary source fetching for untrusted tenants.
6. Measure labeled lead/contact outcomes before changing scoring weights or claiming a source coverage percentage.

## Production truth

This change provides verification primitives and durable workflow infrastructure. It does not claim that all existing sales paths have been switched to the ledger or that live delivery, replies, and meeting booking have been validated.
