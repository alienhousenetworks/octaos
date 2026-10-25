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
- Added a tenant-scoped employment status endpoint with explicit allowed transitions; leave status and termination are intentionally excluded because they require their own governed workflows.
- Made leave approval update the request and append its ledger deduction in one transaction, with row locking where supported and retry/idempotency checks. A database-level unique ledger-reference constraint is still required to guarantee cross-database race safety.
- Enforced attendance punch transitions (no clock-out before clock-in, duplicate clock-in/out rejection) and removed fabricated roster optimization scores; roster generation is explicitly labeled a baseline draft until real constraints are modeled.
- Added route-level permission and cross-tenant tests, alongside HR risk-classifier tests. Tests and CI have not yet been executed/verified from this branch.
- Moved HR API authorization to the canonical OctaOS RBAC permission codenames (for example `hr.view_employees`, `hr.manage_leave`, `hr.manage_workforce`), and extended the standard HR group permission catalogue.
- Added timezone-aware attendance punches, an append-only punch audit event, and a tenant-scoped audit-history endpoint.
- Added a partial unique index for non-null leave-ledger references, plus a guarded schema rollout script that stops if legacy duplicate references must be reconciled.
- Added explicit staffing-demand and employee-availability records. The roster optimizer now greedily assigns employees only when declared availability and role/skill constraints match, avoids overlapping assignments, reports unmet demand, and computes coverage from actual assignments rather than a fabricated score.
- Added HR self-service request tickets, performance-review drafts/submission/employee acknowledgement, compensation proposals with separation-of-duties approval (without pretending payroll was updated), and verified onboarding/offboarding checklists with independent case finalization.

## Known follow-up work before production

1. Review role names against the canonical RBAC role registry; avoid maintaining parallel role taxonomies long term.
2. Run `python scripts/migrate_hr_enterprise_schema.py` after a backup. It preflights duplicate ledger references and creates the new HR tables/index; reconcile reported duplicate references before retrying.
3. Run the new route-level tests and add integration tests against the deployment database for self-service ownership, concurrent leave approval, and attendance time-zone boundaries.
4. Extend scheduling with jurisdiction-specific labor law, minimum rest periods, maximum weekly hours, cost/budget constraints, and solver-backed optimization. Current scheduling checks only configured demand, declared availability/unavailability, role/skill match, and overlaps.
5. Add route-level tests with a real test database, cross-tenant adversarial tests, migration checks, and provider sandbox tests.
6. Consolidate overlapping HR model families and orchestrators only after an inventory and migration plan.
7. Implement durable jobs, outbox delivery, idempotent provider actions, approval separation-of-duties, and independent side-effect verification.
8. Connect compensation approvals to a real payroll provider with reconciliation, add review-cycle analytics and richer employee self-service, and implement jurisdiction-configurable compliance.
9. Run the full backend test suite, frontend build, lint/type checks, and production-like end-to-end workflows before merging.

## Evidence standard

A class, route, button, or agent registration is not proof of a working feature. Mark capabilities as verified only after a test or real provider response proves the expected side effect. Unconfigured integrations and unavailable metrics must remain explicitly unavailable rather than being represented by sample values.
