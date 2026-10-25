# OctaOS — AI Employee Workspace

OctaOS is an AI-enabled business operations platform intended to coordinate work across Sales, Marketing, Customer Support, People & HR, Finance, and Operations. It combines a web workspace, API services, background jobs, external integrations, and configurable AI providers.

> **Documentation accuracy:** This README describes the architecture and workflows documented for the project. Integration availability depends on the code path, credentials, provider permissions, tenant configuration, and deployment. A connector listed below is not a claim that it is enabled in every environment. Verify the implementation and deployment before treating any workflow as production-ready.

## Contents

- [Product overview](#product-overview)
- [Architecture](#architecture)
- [Repository map](#repository-map)
- [How a request moves through OctaOS](#how-a-request-moves-through-octaos)
- [Feature areas and workflows](#feature-areas-and-workflows)
- [Agent orchestration](#agent-orchestration)
- [Connectors and providers](#connectors-and-providers)
- [Configuration](#configuration)
- [Local development](#local-development)
- [Operations and troubleshooting](#operations-and-troubleshooting)
- [Security and production checklist](#security-and-production-checklist)
- [Documentation and contribution guide](#documentation-and-contribution-guide)

## Product overview

OctaOS is designed around AI employees and task workflows rather than a single chatbot. Users can initiate work from a department workspace or the Orchestrator, supply business context and connected tools, review proposed actions, and track execution.

Core product areas described by the project include:

- **Orchestrator AI:** a conversational entry point for routing multi-step requests to the appropriate department capabilities.
- **Sales:** prospect sourcing, lead enrichment, qualification, prioritization, outreach preparation, inbox/reply handling, and follow-up coordination.
- **Marketing and Campaign Planner:** campaign planning, content generation, creative workflows, social-channel publishing, and performance-oriented iteration.
- **Support:** knowledge-assisted responses across supported messaging and email channels, with human handoff.
- **People & HR:** recruiting and HR workflow support, candidate/document handling, and configurable process automation where implemented.
- **Operations and analytics:** cross-department task coordination, execution status, reporting, and operational workflows.
- **Knowledge and configuration:** business documents, prompts, provider credentials, channel settings, and integration configuration.

Exact screens and capabilities depend on the current frontend and backend implementation. Use the source code and API schema as the final authority for feature availability.

## Architecture

The project README documents this high-level stack:

| Layer | Technology / responsibility |
| --- | --- |
| Web client | Next.js frontend (as documented in the existing setup instructions) |
| API | Python and FastAPI |
| Background execution | Celery workers and scheduled Celery Beat tasks |
| Relational persistence | PostgreSQL |
| Queue and cache | Redis |
| AI providers | Provider adapters configured by environment or workspace settings |
| API discovery | FastAPI/OpenAPI at `/docs` |
| Schema changes | Alembic migrations |

### Logical request lifecycle

1. **User intent** — a user starts a task in a department UI or Orchestrator chat.
2. **Context assembly** — the application gathers permitted tenant, workspace, knowledge-base, configuration, and task context.
3. **Planning and routing** — orchestration selects the relevant workflow or capability. The exact agent graph is feature-specific.
4. **Provider/tool calls** — configured model providers and available integrations are called where required.
5. **Execution** — synchronous work runs in the API request; long-running or scheduled work can be delegated to background jobs.
6. **Persistence and status** — task outputs and supported status information are saved and surfaced to the UI.
7. **Review or handoff** — actions that require human judgment, external authorization, or approval should be reviewed before irreversible execution.
8. **Follow-up** — scheduled tasks, inbox polling, webhooks, or user actions can continue the workflow when configured.

Not every feature necessarily uses every stage. Inspect the relevant route, service, task, and UI before assuming a universal pipeline.

## Repository map

The following is a **logical navigation map based on the project’s documented architecture**, not a guarantee that every directory name below exists exactly as written. Use the actual checked-out tree to confirm current paths before editing.

```text
octaos/
├── app/                       # FastAPI application (documented)
│   ├── api/                   # API routes / versioned endpoints
│   ├── core/                  # Configuration, middleware, security
│   ├── db/                    # Database/session infrastructure
│   ├── models/                # Persistence models
│   ├── schemas/               # Request/response validation
│   ├── services/              # Business logic and provider integrations
│   └── worker/                # Celery tasks and background orchestration
├── frontend/                  # Web client (documented)
├── alembic/                   # Database migrations (documented)
├── docs/                      # Manuals and integration notes, if present
├── requirements.txt           # Python dependencies (documented)
├── .env.example               # Environment template (if present)
└── README.md
```

### How to trace a feature in the code

For a reliable end-to-end audit, trace each feature in this order:

1. **Frontend route/page** — entry screen, forms, loading/error states, and API calls.
2. **API route** — HTTP method, path, auth/tenant context, validation, and response shape.
3. **Schema and model** — persisted fields, constraints, relationships, and migrations.
4. **Service or workflow** — business rules, provider calls, retries, and error handling.
5. **Agent/prompt definitions** — task roles, inputs, outputs, and routing conditions.
6. **Background task** — queue name, task arguments, retry policy, idempotency, and schedule.
7. **Connector adapter** — OAuth/token requirements, scopes, rate limits, and API error handling.
8. **Tests and observability** — tests, logs, metrics, audit trail, and failure recovery.

Do not infer that an agent is active merely because its name appears in a prompt, UI, registry, or documentation. Confirm that the runtime invokes it and that its output is consumed.

## How a request moves through OctaOS

A typical task should be understood as the following flow:

```text
User / UI
   |
   v
API endpoint + authentication + tenant context
   |
   v
Validation and business-service layer
   |
   +----> Knowledge/context retrieval
   |
   +----> Agent / model selection
   |
   +----> External connector calls (when configured)
   |
   v
Result validation and policy / approval checks
   |
   +----> Human review or handoff (where required)
   |
   v
Database + task status + audit/logging
   |
   +----> UI result
   +----> Celery follow-up / scheduled work (when configured)
```

Production implementations should enforce tenant isolation at every data access and background-task boundary, not just in frontend filtering.

## Feature areas and workflows

### 1. Orchestrator AI

**Purpose:** provide a common entry point for business requests that span one or more departments.

**Typical flow**
1. Receive the user's goal and any supplied constraints.
2. Identify the intended department(s), required context, and expected outcome.
3. Select a supported workflow or agent capability.
4. Request missing information when the task cannot be performed safely or accurately.
5. Execute or enqueue the work through the relevant service.
6. Return results and execution status, including errors or unavailable integrations.
7. Route consequential actions for human approval where appropriate.

**Important distinction:** conversationally describing a plan is not the same as executing it. The UI should distinguish planned, running, completed, failed, awaiting approval, and simulation-only work whenever those states exist.

### 2. Sales workspace

Sales workflows can include prospect discovery, enrichment, qualification, prioritization, outreach preparation, and follow-up management.

**Typical lead workflow**
1. Define the ideal customer profile, geography, industry, role, and other filters.
2. Source candidate companies or contacts from configured data sources.
3. Normalize records and deduplicate leads.
4. Enrich available company/contact information.
5. Evaluate fit, intent, pain, timing, and evidence according to the configured scoring rules.
6. Save the lead and explain the factors behind its score.
7. Prepare personalized outreach for supported channels.
8. Apply cadence and follow-up rules.
9. Process replies or inbound events and update the lead/ticket state.
10. Escalate uncertain, sensitive, or consequential actions for human review.

**Expected safeguards:** respect source terms and API limits, maintain provenance for enriched facts, suppress opted-out contacts, prevent duplicate sends, and apply applicable privacy and anti-spam requirements. A score must not be represented as a verified fact unless it is grounded in recorded evidence.

### 3. Marketing and Campaign Planner

Marketing workflows coordinate campaign strategy and content production. The documented project direction includes campaign planning, AI-assisted content and creative generation, social channel connections, and publishing workflows.

**Typical campaign flow**
1. Capture the business, product, audience, objective, offer, constraints, and brand guidance.
2. Gather available evidence and existing brand/product context.
3. Draft the strategy, message, content plan, and publishing cadence.
4. Generate channel-specific copy and creative briefs/assets through configured providers.
5. Validate factual claims, links, brand consistency, and channel requirements.
6. Present drafts for review when required.
7. Publish or schedule only through authorized, connected channels.
8. Record publication identifiers/status and surface failures.
9. Use available performance data to inform subsequent iterations.

**AI influencer / creator marketing:** where this feature is present in the checked-out version, its safe workflow is to understand the product and audience, recommend relevant creator profiles using available evidence, explain fit and uncertainty, prepare a proposed campaign, and require review before outreach, contracting, or spending. Verify the current code to confirm which of these steps are implemented.

**Publishing note:** generated content, scheduled content, and successfully published content are distinct states. A success message should be based on the provider's actual response, not on a model's assertion.

### 4. Social publishing

The existing project setup documentation names Meta and LinkedIn OAuth configuration. Other channels should be considered available only when their adapters, authorization flow, permissions, UI, and publishing implementation are present.

**Typical flow**
1. An administrator configures the provider app credentials.
2. A tenant authorizes the channel using OAuth or a supported token flow.
3. The application stores credentials securely and associates the connection with the correct tenant/account.
4. The user selects the destination, content, media, and schedule.
5. The application validates permissions and payload requirements.
6. A worker publishes or schedules the content.
7. Provider response IDs and errors are recorded.
8. The UI displays the real state and allows recovery from failures.

### 5. Customer Support

Support workflows can connect incoming customer conversations to a knowledge base and help agents prepare or send responses.

**Typical message workflow**
1. Receive an event from a supported inbox, webhook, or connected messaging channel.
2. Verify the webhook/signature and resolve the tenant and conversation.
3. Load relevant conversation history and authorized knowledge documents.
4. Draft a grounded response using a configured AI provider.
5. Apply configured delay, approval, or automation policy.
6. If a human agent responds or takes ownership, cancel or suppress the pending automated reply where the implementation supports it.
7. Send through the connected provider only when authorized.
8. Record the result and expose delivery failures for follow-up.

The existing README describes WhatsApp replies with a 4–5 minute delay, email support replies with a 20-minute delay, human interception, knowledge-base use, and Gmail inbox polling on a three-minute schedule. These timings are configuration/code-dependent and should be checked against the deployed task scheduler before being relied upon.

### 6. Knowledge base

The documented workflow allows business documents such as FAQs, pricing sheets, and job specifications to inform AI responses.

A robust knowledge workflow should cover:
- Upload and file validation.
- Tenant-scoped storage and access controls.
- Text extraction and indexing where implemented.
- Document updates and deletion propagation.
- Retrieval of relevant passages at task time.
- Source-aware answers and clear handling of missing information.
- File-size/type limits and protection against unsafe document content.

Do not assume a file is searchable simply because it appears in an upload list; confirm ingestion/indexing status.

### 7. People & HR

People & HR workflows may support recruitment, candidate review, document workflows, and onboarding-related tasks depending on the current code.

**Typical recruiting flow**
1. Create a role and define must-have criteria.
2. Import or receive candidate applications.
3. Extract candidate information from permitted documents.
4. Compare evidence with role requirements and identify missing information.
5. Support human review and interview coordination.
6. Track stage transitions and decisions.
7. Generate HR documents from approved templates where implemented.
8. Record approvals, delivery status, and audit history.

HR decisions are consequential. AI-generated rankings or summaries should assist, not silently replace, qualified human decisions. Avoid unsupported inferences about protected characteristics and keep candidate data access tightly scoped.

### 8. Finance and operations

Finance is named in the existing project overview, but the exact implemented modules, data sources, and accounting actions must be verified in code. Do not treat a Finance label or placeholder screen as proof of a complete ledger, reconciliation, or payment workflow.

For any operational workflow, document its trigger, inputs, owner, state transitions, external side effects, retry behavior, approval requirements, and recovery path.

### 9. Background jobs and schedules

Celery is documented for long-running and scheduled routines. Examples in the existing README include Gmail sales inbox polling and scheduled social/email routines.

For each task, record:
- The registered task name and source file.
- Trigger: API, webhook, queue, or schedule.
- Arguments and tenant context.
- Retry/backoff and timeout behavior.
- Idempotency and duplicate-event handling.
- Result/status persistence.
- Dead-letter or manual recovery path, if implemented.

Start workers and Beat only when their broker, schedule, and deployment configuration are correct.

## Agent orchestration

Agent terminology can describe prompts, classes, graph nodes, registered capabilities, or actually invoked runtime workers. These are not interchangeable. For every agent shown in the product, the implementation documentation should record:

| Field | What to document |
| --- | --- |
| Name and department | Stable identifier and user-facing purpose |
| Trigger | Route, workflow edge, event, or scheduled task that invokes it |
| Inputs | Validated schema and required context |
| Tools | Exact callable tools/connectors and permission boundaries |
| Model | Provider/model selection and fallback behavior |
| Output | Structured schema, not just free-form text |
| Handoffs | Next node, conditional edge, or human review |
| Failure behavior | Timeout, retry, fallback, unavailable state |
| Side effects | Writes, sends, publishes, or external mutations |
| Evidence | Sources supporting factual claims and generated decisions |
| Tests | Unit/integration tests for success and failure paths |

**Recommended execution pattern**

```text
Request
  -> classify intent
  -> build tenant-scoped context
  -> choose workflow
  -> run specialist steps
  -> validate each output
  -> evaluate policy / approval requirements
  -> execute authorized tools
  -> persist result and audit events
  -> return status
```

Use bounded retries, structured outputs, explicit timeouts, budget controls, and clear stopping conditions. A final answer should disclose incomplete steps and connector failures instead of presenting a partial run as successful.

## Connectors and providers

The following integrations are named in the existing README or project direction. Availability is conditional on implementation, credentials, tenant authorization, and provider permissions.

| Connector / provider | Intended role | Configuration / verification |
| --- | --- | --- |
| OpenAI | Language-model inference | `OPENAI_API_KEY` or supported workspace provider settings |
| Anthropic Claude | Language-model inference | `ANTHROPIC_API_KEY` or supported workspace provider settings |
| Meta / Facebook / Instagram | OAuth and supported social publishing | `META_APP_ID`, `META_APP_SECRET`; verify scopes and channel-specific APIs |
| LinkedIn | OAuth and supported publishing | `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`; verify organization/page permissions |
| WhatsApp Cloud API | Customer messaging | Meta app, Phone Number ID, access token, webhook configuration |
| Telegram Bot API | Bot messaging and alerts | Bot token; configure allowed chats and webhook/polling mode |
| Gmail API | Inbox/reply workflows | Google OAuth credentials and granted Gmail scopes |
| Google Calendar API | Scheduling workflows | Google OAuth credentials and Calendar scopes |
| SMTP | Email sending fallback | Host, port, username, password/app password, TLS settings |
| SendGrid / Mailgun | Inbound email webhooks or email delivery, where implemented | Provider account, signing secret, configured webhook URL |
| Apify | Web data extraction / actor execution | Apify token, actor configuration, usage and rate limits |
| Apollo.io | Lead discovery/enrichment | API key, account access and plan limits |
| Hunter.io | Email discovery/verification | API key and usage limits |
| Google Places | Local business discovery | Google Cloud project, Places API enablement and billing |
| PostgreSQL | Application persistence | Database URL/credentials and migrations |
| Redis | Celery broker/cache | Redis URL, connectivity, persistence policy |

### Connector lifecycle

1. Configure provider credentials in a secret store or environment.
2. Complete OAuth or token setup for the correct tenant.
3. Validate scopes and test the connection.
4. Store credentials securely; never return secret values to the frontend.
5. Check tenant ownership and permissions before each call.
6. Apply rate limits, timeouts, and bounded retries.
7. Persist provider IDs, timestamps, and actionable error details.
8. Support disconnect/revoke and credential rotation.
9. Display disconnected, not configured, rate limited, failed, and healthy states distinctly.

Never commit real API keys, OAuth secrets, access tokens, database passwords, or customer data.

## Configuration

Start from the repository's environment template if present:

```bash
cp .env.example .env
```

The existing README names these configuration categories:
- PostgreSQL connection and database credentials.
- Redis connection for Celery and caching.
- One or more AI provider keys.
- Meta and LinkedIn OAuth client credentials.
- SMTP credentials where email sending uses SMTP.
- Google OAuth configuration for Gmail and Calendar.
- External data-provider keys such as Apify, Apollo, Hunter, and Google Places.
- Frontend API base URL, documented previously as `NEXT_PUBLIC_API_URL`.

Variable names and defaults can change. Inspect `.env.example`, application settings, and deployment manifests in the current branch before configuring production. Keep local secrets in an ignored `.env` file or secret manager.

## Local development

### Prerequisites

- Python 3.10 or newer (as documented).
- Node.js 18 or newer and npm.
- PostgreSQL.
- Redis for background jobs and cache.

### Backend

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Configure the database and required environment variables, then apply migrations:

```bash
alembic upgrade head
```

Run the API:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API root: `http://localhost:8000`  
OpenAPI UI: `http://localhost:8000/docs`

### Background worker

In a separate terminal with the same environment:

```bash
celery -A app.worker.tasks worker --loglevel=info
```

Run the scheduler only if the deployment uses Celery Beat and the schedule is configured:

```bash
celery -A app.worker.tasks beat --loglevel=info
```

The import paths above are those documented in the existing README; confirm they still match the current branch.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The existing README documents the development UI at `http://localhost:3000`. Check the frontend's `package.json` for the actual framework, scripts, and required environment variables before running it.

## Operations and troubleshooting

### AI provider unavailable
- Check that a provider key is configured in the intended environment or workspace.
- Verify account access, quota, model availability, and network connectivity.
- Inspect server logs for sanitized provider errors.
- Return a clear unavailable/error state; do not fabricate a successful AI result.

### Celery tasks not running
- Confirm Redis is reachable and the configured broker URL matches.
- Confirm the worker imports the task module and registered task name.
- Check worker logs and queue names.
- Start Beat only for scheduled tasks and avoid multiple schedulers producing duplicate work.

### Database connection or migration errors
- Verify connection settings and database availability.
- Run `alembic current` and `alembic upgrade head` in the intended environment.
- Do not use destructive schema resets on production data.
- Back up the database before risky migrations.

### OAuth or publishing failures
- Check callback URLs, app mode, granted scopes, token expiry, account/page permissions, and provider API changes.
- Distinguish authentication failure from insufficient permission, rate limiting, invalid payload, and provider outage.
- Do not display “published” unless the provider confirms publication.

### Webhook failures
- Verify signature validation, endpoint reachability, event IDs, and provider retry behavior.
- Make handlers idempotent and avoid logging secrets or full message contents unnecessarily.

### Database check
The previous README mentions `python check_db.py`. Run it only if that script exists in the current checkout.

## Security and production checklist

Before production use, verify:

- [ ] Authentication and authorization protect all private API routes.
- [ ] Every tenant-owned read, write, background job, file, and connector is tenant-scoped.
- [ ] Secrets are encrypted or held in a secret manager and excluded from logs/responses.
- [ ] OAuth state, callback URLs, token expiry, revocation, and scopes are handled securely.
- [ ] Webhooks verify signatures and prevent replay/duplicate processing.
- [ ] Outbound email/social actions have opt-out, permission, and approval safeguards.
- [ ] AI output is validated before it drives external side effects.
- [ ] Retries are bounded and side-effecting actions are idempotent.
- [ ] Human approval is available for sensitive or irreversible actions.
- [ ] Uploads are validated and stored with appropriate access controls.
- [ ] Logs and audit events are useful but do not expose secrets or unnecessary personal data.
- [ ] Migrations, backups, restore procedures, health checks, and alerting are tested.
- [ ] Tests cover connector failures, provider timeouts, cross-tenant access, and partial workflow completion.
- [ ] UI states distinguish queued, running, needs-review, succeeded, failed, and unavailable where applicable.

## Documentation and contribution guide

When adding or changing a feature, update the documentation alongside the code:

1. Describe the user-facing capability and its limits.
2. Add the exact frontend route and API endpoint.
3. Document request/response schemas and permission checks.
4. Map the service, agent steps, connectors, and background tasks.
5. List required environment variables and OAuth scopes.
6. Document failure states, retries, idempotency, and approval gates.
7. Add tests for success and failure cases.
8. Update this README only when the behavior is confirmed in code.

### Suggested feature documentation template

```text
Feature:
Frontend entry point:
API routes:
Data models / migrations:
Service and workflow:
Agent nodes and conditional edges:
Connectors and permissions:
Environment variables:
Background tasks / schedules:
Human approval:
Failure and recovery behavior:
Tests:
Known limitations:
```

## License

Check the repository's license file for the applicable terms.
