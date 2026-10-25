# Autonomous Campaign Studio implementation status

## Implemented in this branch

- Adds a dedicated `/app/campaigns/studio` workspace with a restrained neutral enterprise surface system.
- Adds Overview, Content Studio, AI Influencer Studio, Artifacts, Calendar and Performance sections while preserving the existing campaign planner.
- Connects campaign overview/content/calendar to the existing tenant-scoped marketing posts API and queues campaign work through the existing background worker.
- Adds tenant-owned virtual influencer profile persistence and listing. Generated personas must be fictional adults, include the synthetic-persona disclosure, and remain review-gated. A review endpoint supports approve, request-changes and reject decisions; approval is for content review, not auto-publishing.
- Adds tenant-scoped campaign artifact and immutable version tables with SHA-256 content/source hashes.
- Adds artifact create/list/detail APIs, version creation with expected-version conflict checks, review bound to exact version/hash, and JSON export of a selected immutable version.
- Adds an artifact JSON editor that creates a new version and resets approval state.
- Connects Buffer status/OAuth entry points and the existing analytics endpoint.
- Adds tests for virtual-influencer brief validation and deterministic artifact content hashing.

## Explicitly not complete

- Export is JSON only. PDF/DOCX/PPTX generation, a rich document editor, object-storage asset pipeline, automatic artifact-generation triggers, and verified external evidence ingestion remain to be implemented.
- Calendar is read-only. Drag/drop scheduling, provider reconciliation, durable publishing recovery and duplicate-send end-to-end tests remain outstanding.
- Performance still displays the backend analytics payload rather than a normalized chart dashboard with evidence-backed learning panels.
- Full browser tests, local production build, and live database migration were not run in this chat. Review GitHub Actions on the latest PR head before merge.
- No deployment or production migration has been run.

## Integrity and safety policy

- Tenant-owned profile and artifact queries are tenant-filtered.
- New artifact versions reset review state to draft.
- Reviews must reference the exact version and matching SHA-256 content/source hash.
- Export downloads a selected immutable version and returns a checksum header.
- A queued campaign is not a completed campaign; a reviewed persona is not permission to publish; a connected provider is not proof that every channel is supported; and unavailable metrics are not zero.
