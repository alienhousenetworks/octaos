# OctaOS HR Enterprise Hardening

## Scope of this implementation slice

This branch is the first implementation increment toward a unified enterprise HR operating system. It intentionally preserves the existing HR API and does not claim that the entire HR product is production-ready.

## Changes made

- Added fail-closed role checks to employee directory, organizational chart, policy, and workforce analytics routes.
- Restricted employee and policy writes to HR/admin roles.
- Replaced count-based employee-number generation with collision-resistant identifiers and handled database uniqueness conflicts as HTTP 409.
- Normalized employee email addresses and validated manager membership within the active tenant.
- Kept department creation and employee creation in one transaction.
- Removed the hardcoded 96.4% retention figure; the API now reports that retention is unavailable until historical data supports a real calculation.
- Added HR role gates to leave listing and approval, rejected unconfigured leave types instead of silently creating an assumed 20-day policy, validated leave-day amounts/date order, and prevented re-approving non-pending requests.
- Added tenant filters to employee/leave-type lookups, access checks for leave balances and attendance, and validation of attendance punch types.
- Added unit tests for access guard behavior and conservative agent risk classification.

## Known follow-up work before production

1. Review role names against the canonical RBAC role registry; avoid maintaining parallel role taxonomies long term.
2. Make leave approval and ledger deduction one atomic, concurrency-safe operation with a unique ledger reference constraint.
3. Enforce self-service ownership on leave submission and audit all attendance transitions, including duplicate clock-in/out and time-zone boundaries.
4. Fix roster optimization so it does not claim optimization when it only distributes employees round-robin; use configured constraints and draft-only output until validated.
5. Add route-level tests with a real test database, cross-tenant adversarial tests, migration checks, and provider sandbox tests.
6. Consolidate overlapping HR model families and orchestrators only after an inventory and migration plan.
7. Implement durable jobs, outbox delivery, idempotent provider actions, approval separation-of-duties, and independent side-effect verification.
8. Complete employee self-service, onboarding/offboarding, compensation/payroll integrations, performance management, and jurisdiction-configurable compliance.
9. Run the full backend test suite, frontend build, lint/type checks, and production-like end-to-end workflows before merging.

## Evidence standard

A class, route, button, or agent registration is not proof of a working feature. Mark capabilities as verified only after a test or real provider response proves the expected side effect. Unconfigured integrations and unavailable metrics must remain explicitly unavailable rather than being represented by sample values.
