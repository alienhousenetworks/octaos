# Industry-neutral Sales and Marketing core

## Decision

The general Sales and Marketing experience must not require a predefined industry pack. OctaOS should infer a business's terminology, audience, offers, content themes, and workflow needs from tenant-provided evidence and configuration.

## Implemented in this branch

- General Campaigns UI no longer shows the industry-pack selector or a real-estate Property Hub entry point.
- Campaigns UI no longer imports the real-estate campaign dialog or industry-pack UI component.
- AI Virtual Influencer, campaign planning, scheduling, analytics, and ordinary campaign views remain available.
- Sales and Marketing pack listing functions return no packs to the general product.
- Core terminology is neutral even if a legacy tenant profile still contains an old pack ID.
- General marketing helpers no longer inject industry-specific content pillars, compliance rules, visual tokens, or calendar events.
- Regression tests cover neutral defaults and ensure legacy IDs do not change general defaults.

## Isolation boundary

Legacy pack definitions and explicit real-estate service code remain in the repository for compatibility with existing specialist code and tenant data. They are not exposed as general Sales/Marketing defaults by these registry functions. Do not delete the underlying definitions until the remaining API routes, prompt builders, database fields, jobs, and tests have been traced and migrated; deleting them prematurely could break existing records or a specialist service.

## Required follow-up before merge

1. Trace and deprecate or remove API routes that activate a pack, while preserving tenant data and backwards-compatible reads.
2. Audit Sales frontend routes and prompt builders for direct pack lookups that bypass the registry defaults.
3. Audit every general campaign prompt and background job for direct pack catalog imports.
4. Run backend tests and frontend lint/typecheck/build in CI.
5. Add cross-business integration tests using tenant-supplied context, verifying no real-estate stages, terminology, inventory assumptions, or compliance labels leak into unrelated businesses.
6. Only then remove unused legacy catalog modules and any pack-specific database columns through a migration.

## Data integrity

This change does not delete tenant records, campaigns, posts, leads, or pipeline history. Existing stored pack IDs may remain until the migration is explicitly planned and tested.
