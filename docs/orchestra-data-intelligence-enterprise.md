# Orchestra Data Intelligence — Enterprise rollout

## Scope delivered in this branch

- Tenant-bound upload and run-history API under `/api/v1/data-intelligence`.
- Multiple uploads and ZIP-as-folder ingestion with path traversal/encrypted archive rejection, archive expansion limits, and file/row/byte bounds.
- CSV/TSV/JSON/JSONL profiles, plus text/PDF/DOCX/XLSX/XLSM/PPTX text extraction.
- Durable run/artifact metadata, source SHA-256 receipts, idempotency conflict detection, explicit extraction status, evidence-linked deterministic findings, JSON and Markdown exports.
- Frontend workspace at `/data-intelligence` with upload, recent runs, finding evidence, coverage, and export controls.

## Security and correctness contract

- Tenant identity is derived from the authenticated user; client-supplied tenant IDs are never accepted.
- Run lookup is always scoped by tenant. The idempotency key is tenant-scoped and reused with a different fingerprint returns HTTP 409.
- Upload bytes are processed in memory and are not persisted by this route. The database retains hashes, filenames, extraction summaries, profiles, findings, and reports; these may still contain sensitive metadata, so database access and retention policy remain required.
- The parser never labels an unavailable, failed, or empty extraction as a verified clean result.
- A SHA-256 is a content identity receipt, not proof that the source is true or authoritative.
- Findings are deterministic quality observations, not causal business claims. This first slice does not yet provide LLM narrative synthesis, connector ingestion, OCR for scanned pages, or multi-page image/chart interpretation.
- ZIPs are bounded and traversal paths rejected. Deploy behind request timeouts and reverse-proxy body limits as well as the application limits.

## Required deployment steps

1. Create/apply a schema migration for `data_analysis_runs` and `data_analysis_artifacts` before routing production traffic to these endpoints. The ORM models are registered with Alembic metadata.
2. Configure `DATA_INTELLIGENCE_MAX_FILES`, `DATA_INTELLIGENCE_MAX_FILE_BYTES`, `DATA_INTELLIGENCE_MAX_TOTAL_BYTES`, `DATA_INTELLIGENCE_MAX_ZIP_EXPANDED_BYTES`, and `DATA_INTELLIGENCE_MAX_ROWS` for your deployment.
3. Ensure the server environment has the optional document parsers already listed in `requirements.txt` installed.
4. Set `NEXT_PUBLIC_API_URL` to the backend API base URL. The frontend currently checks common local-storage access-token keys; align `authHeaders` with the canonical auth client used by the deployed app before production rollout.
5. Run the focused tests, full backend suite, lint, and frontend production build. This connector-driven implementation has not been executed in a checkout here, so CI is the required verification gate.
6. Validate tenant isolation, oversized uploads, corrupt documents, ZIP bombs, retry/idempotency, and export permissions in staging before production enablement.

## Follow-up work before declaring full enterprise production readiness

- Use Celery with durable queued/running/failed states and retry/resume semantics rather than performing all parsing in the request worker.
- Add a real migration linked to the repository's current Alembic head, plus rollback and staging migration validation.
- Add encrypted object storage with tenant-scoped retention/deletion if source-file reprocessing is required.
- Add OCR and page/slide/sheet coverage receipts; emit extraction coverage by page/sheet and distinguish text extraction from visual analysis.
- Add tenant quota/rate limiting, malware scanning, content-type sniffing, antivirus policy, retention controls, audit events, and structured metrics.
- Add connector adapters (CSV/Excel, databases, CRM, analytics providers) with explicit permissions, preview, provenance, and revocation.
- Add report versioning, signed evidence manifest, HTML/PDF exports, and human-approved LLM synthesis grounded exclusively in extracted evidence.
