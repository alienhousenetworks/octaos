# Orchestra Data Intelligence Foundation

This branch introduces deterministic trust primitives for the planned end-to-end data-intelligence workflow. It is intentionally additive and does not yet claim that database ingestion, OAuth, durable run orchestration, PDF report export, or a production code sandbox are complete.

## What is implemented

- **Validated task DAGs** (ValidatedPlan): strict schemas, duplicate/missing dependency checks, cycle rejection, and deterministic topological ordering. Planner output is treated as untrusted input.
- **Actual-record profiling** (profile_records): row/column counts, null counts/fractions, distinct values, duplicate-row count, safe numeric summaries, dataset hash, and explicit empty-input status. A hard row limit prevents accidental unbounded profiling.
- **Evidence references** (EvidenceRef, EvidenceLedger): source kind, locator, observation timestamp, optional SHA-256, collision protection, and finding-to-evidence validation.
- **Finding validation** (validate_findings): rejects duplicate finding IDs and findings that cite evidence not present in the ledger.
- **Regression tests**: graph validation, profiling, empty inputs, size limits, evidence grounding, and stable hashing.

## Integration contract

1. Resolve authenticated principal and tenant using OctaOS's canonical auth/RBAC dependencies before constructing a run.
2. Resolve data sources through Knowledge Connectors or existing application services; do not accept connection credentials from prompts.
3. Apply authorization and row/query limits before passing records to profile_records.
4. Persist runs, datasets, evidence, and findings using the repository's existing ORM/Alembic conventions. The in-memory EvidenceLedger is a primitive, not durable storage.
5. Only mark a finding verified after its referenced evidence exists and its deterministic computation or sandbox execution has completed. Model-generated prose is not evidence.
6. Run generated Python only in a separate, restricted execution service. This module deliberately does not execute code.
7. Use asynchronous durable jobs for long-running extraction and analysis; expose truthful states (queued, running, partial, failed, succeeded) and preserve errors.

## Release gates before production enablement

- Remove privileged default identity/tenant values from orchestration entry points and bind each run to authenticated tenant context.
- Remove synthetic success responses from production agent/model failures.
- Reconcile route dependencies with the existing canonical auth stack before exposing new endpoints.
- Add database-enforced read-only connector sessions, query timeouts, schema allowlists, and SSRF-safe API connector policies.
- Add isolated execution infrastructure; never use unrestricted Python exec() in the web process.
- Persist evidence and run state transactionally, and add tenant-isolation tests for every read/write endpoint.
- Benchmark OCR/vision against labeled multilingual, handwritten, and multi-page fixtures before advertising support.

## Test

Run the repository's configured pytest command with tests/test_orchestra_data_intelligence_core.py. These tests exercise only the pure primitives and do not require external model credentials or production data.
