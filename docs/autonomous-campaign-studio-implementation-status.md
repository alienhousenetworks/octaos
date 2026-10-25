# Autonomous Campaign Studio implementation status

## Included in this branch

- Adds a dedicated `/app/campaigns/studio` workspace with a restrained neutral enterprise surface system, consistent borders, typography, spacing and one primary accent.
- Adds Overview, Content Studio, AI Influencer Studio, Artifacts, Calendar and Performance sections.
- Connects campaign overview/content/calendar to the existing tenant-scoped marketing posts API.
- Queues campaigns through the existing `/marketing/campaign` worker API and reports the returned job identifier rather than claiming completion.
- Reads the existing analytics dashboard without fabricating metric values.
- Connects Buffer status and OAuth through the registered `/marketing/connectors/buffer/*` routes.
- Adds a virtual-influencer brief endpoint that uses the existing tenant AI gateway and existing safe brief validator. It requires a fictional adult persona, synthetic disclosure and human review; it never publishes.
- Adds validation tests for required persona fields, disclosure and review status.
- Adds a link from the existing campaign planner into the new studio.

## Known gaps; do not treat these as implemented

- Virtual influencer briefs are generated on request but are not yet stored in a dedicated persistent persona library. The response explicitly reports `persistence: not_persisted`.
- The Artifacts section is an honest workspace entry point, not a complete versioned artifact backend. Durable artifact/version/source/review/export APIs and migrations are still required.
- Calendar is read-only in this change. Drag/drop scheduling and rescheduling are not implemented here.
- Performance currently displays the backend analytics payload for transparency; a normalized metric visualization and learning-insight evidence panel remain to be built.
- Provider capability diagnostics, publishing reconciliation, durable orchestration recovery and full end-to-end browser tests require a further integration pass.
- This branch has not been run through a local frontend build or backend test suite in this environment. CI results must be reviewed before merge.

## Verification policy

A queued job is not a completed campaign; a generated brief is not an approved persona; a Buffer credential is not proof that every channel can publish; and a missing metric is not zero. Preserve those distinctions in UI and API responses.
