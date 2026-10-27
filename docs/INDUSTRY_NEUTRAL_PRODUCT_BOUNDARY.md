# OctaOS industry-neutral product boundary

## Product decision

OctaOS is an industry-neutral AI Workforce Operating System. The shared platform provides bots, workflows, memory, connectors, approvals, permissions, tenant isolation, evidence, analytics, and durable execution. Industry-specific behavior belongs in optional, tenant-configured packs and must never be a hard dependency of the core experience.

## Changes in this branch

- Removed dedicated real-estate and property field-sales routers from active API registration.
- Removed property campaign endpoints from the general Marketing API.
- Removed the real-estate campaign dialog and its project-specific frontend contract.
- Removed real-estate / property-specific Sales navigation entries and search keywords.
- Removed real-estate and field-sales model imports from the package-wide model registry and startup schema-seeding import list. Direct legacy model modules and migration files remain in source history for compatibility review.

## Compatibility and data safety

This is an API/UI deactivation, not a destructive database migration. Existing database tables, historical migrations, and tenant records must not be deleted as part of this step. Do not drop tables or columns until production usage is inventoried, data is backed up, a reversible migration plan is reviewed, and existing customers' data has been reconciled.

## Still required before claiming complete removal

1. Search all app and frontend references for dedicated real-estate, property inventory, RERA, project/unit booking, property visits, and cost-sheet workflows.
2. Remove or generalize remaining route handlers, service modules, jobs, mobile-app assets, marketplace entries, seed data, prompt templates, and tests that assume real estate.
3. Keep reusable field operations generic only after replacing property-specific project/unit schemas with configurable records and validating the workflow against multiple unrelated industries.
4. Replace industry-specific examples in product documentation and onboarding.
5. Run backend tests, frontend lint/typecheck/build, migration checks, and route/OpenAPI regression tests.
6. Deploy behind a reversible release boundary and verify existing tenants can still use the general Sales, Marketing, HR, Support, workflow, and AI workforce features.

## Verification policy

A removed navigation item or unregistered router is not proof that every real-estate reference has been removed from the repository. This document deliberately separates the implemented surface changes from the remaining full-repository audit.
