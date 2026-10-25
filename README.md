# OctaOS — Detailed Product, Architecture, Directory, Feature & Agent Workflow Guide

OctaOS is an AI-enabled business operations workspace intended to coordinate work across Marketing, Sales, Customer Support, People & HR, Operations, and other business functions. This README is the main product and engineering guide: it describes the logical architecture, feature taxonomy, sub-features, end-to-end workflows, agent responsibilities, connector categories, and a detailed directory map.

> **Accuracy note — read before using this as an implementation map:** The repository could not be exhaustively enumerated source-file by source-file during this documentation pass. The directory tree and workflow diagrams below are a detailed **logical documentation map** based on the project context and documented stack, not a guarantee that every path, agent, sub-feature, or connector exists in the current checkout. Treat a capability as live only after confirming its route, service, UI, configuration, tests, and external integration in code. Diagrams describe the intended workflow pattern and must not be read as proof of production execution. Update this README when implementation differs.

## Contents

- [1. What OctaOS is](#1-what-octaos-is)
- [2. Platform architecture](#2-platform-architecture)
- [3. Detailed directory structure](#3-detailed-directory-structure)
- [4. Shared workflow lifecycle](#4-shared-workflow-lifecycle)
- [5. Orchestrator and AI Workforce](#5-orchestrator-and-ai-workforce)
- [6. Marketing and Campaign Planner](#6-marketing-and-campaign-planner)
- [7. Sales and revenue operations](#7-sales-and-revenue-operations)
- [8. Customer Support](#8-customer-support)
- [9. People and HR](#9-people-and-hr)
- [10. Operations and workflow automation](#10-operations-and-workflow-automation)
- [11. Real-estate sales workflows](#11-real-estate-sales-workflows)
- [12. Knowledge and business context](#12-knowledge-and-business-context)
- [13. Social publishing and communications](#13-social-publishing-and-communications)
- [14. Analytics, reporting, and auditability](#14-analytics-reporting-and-auditability)
- [15. Agent architecture and diagrams](#15-agent-architecture-and-diagrams)
- [16. Connector and AI-provider catalogue](#16-connector-and-ai-provider-catalogue)
- [17. Security, tenancy, and approval boundaries](#17-security-tenancy-and-approval-boundaries)
- [18. Configuration and local development](#18-configuration-and-local-development)
- [19. Testing and production-readiness checklist](#19-testing-and-production-readiness-checklist)
- [20. How to keep this README accurate](#20-how-to-keep-this-readme-accurate)

---

## 1. What OctaOS is

OctaOS is designed as a multi-department AI employee and workflow platform. Rather than treating every request as a standalone chat, the product model is to translate a business goal into work, run the appropriate steps, connect approved tools, retain execution state, and present the outcome to a human operator.

### Main product concepts

| Concept | Meaning |
|---|---|
| Workspace / tenant | An organisation's isolated users, records, configuration, connections, and execution history. |
| Feature module | A business domain such as Marketing, Sales, Support, People & HR, or Operations. |
| Workflow | A sequence or graph of steps with inputs, dependencies, status, retry rules, and completion conditions. |
| Agent | A bounded worker assigned a defined task with scoped context, tools, and an output contract. |
| Orchestrator | The coordinator that interprets a goal, creates or selects a workflow, tracks progress, and assembles results. |
| Provider / model | A configured AI service and model used for a particular task. |
| Connector | An adapter for an external service, API, webhook, or communication channel. |
| Approval gate | A pause requiring a permitted person to approve a consequential action. |
| Execution record | A durable record of request, plan, step states, outputs, errors, external IDs, and timestamps. |
| Evidence | The source data, tool response, document, event, or external confirmation supporting a result. |

### Design principles

1. **Outcome-led:** workflows begin with a business objective and constraints.
2. **Modular:** department workflows share platform services without mixing domain data or business rules.
3. **Tenant-aware:** every tenant-owned read and write is scoped to the authorised tenant.
4. **Tool-bounded:** agents receive only the tools and data required for their task.
5. **Human-controlled:** publishing, external messaging, hiring decisions, money movement, record deletion, and other high-impact actions can require approval.
6. **Observable:** each step has a traceable state and failure reason.
7. **Truthful:** “drafted,” “approved,” “submitted,” “delivered,” and “verified complete” are distinct states.
8. **Provider-flexible:** model routing is configurable where implemented; credentials are never exposed to the browser.
9. **Recoverable:** async work uses idempotency, bounded retries, timeouts, and explicit terminal failure states.

## 2. Platform architecture

The following diagrams represent the logical architecture. Confirm the actual implementation, deployment topology, and service names in the source before treating them as exact.

### 2.1 High-level system map

~~~mermaid
flowchart TB
    PERSON[Workspace member] --> WEB[Web frontend]
    WEB --> API[FastAPI / API layer]
    API --> IAM[Authentication, tenant context, permissions]
    IAM --> DOMAIN[Feature services]
    DOMAIN --> ORCH[Workflow and agent orchestrator]
    DOMAIN <--> DB[(Relational database)]
    ORCH <--> DB
    ORCH --> MODEL[AI provider and model adapter]
    ORCH --> QUEUE[Background job queue]
    QUEUE --> WORKER[Async workers / scheduled tasks]
    WORKER --> ADAPTER[Connector adapters]
    ADAPTER --> EXT[External platforms and APIs]
    WORKER --> DB
    API --> OBS[Logs, metrics, execution traces]
    ORCH --> OBS
    WORKER --> OBS
    DB --> WEB
~~~

### 2.2 Layer responsibilities

| Layer | Responsibility | Typical contents |
|---|---|---|
| Frontend | User experience, forms, workflow builder, execution timelines, approvals, reports | Pages, feature components, API clients, typed contracts |
| API | HTTP boundary, validation, authentication, response codes | Routers, request dependencies, schemas |
| Core platform | Configuration, tenant context, identity, permissions, logging | Settings, auth helpers, policy checks |
| Feature services | Department-specific business rules | Campaign service, lead service, HR service, support service |
| Orchestration | Plans, step dependencies, dispatch, cancellation, aggregation | Workflow engine, execution state machine |
| Agent runtime | Context assembly, model invocation, tool call, output validation | Agent definitions, prompts, tools, validators |
| Providers | Model API adapters, model selection, retry and timeout policy | OpenAI / Anthropic / other configured adapters |
| Connectors | External API requests and event handling | OAuth clients, API clients, webhook handlers |
| Workers | Async execution, scheduled jobs, retries | Queue app, tasks, schedules |
| Persistence | Durable business and execution state | Models, repositories, migrations |
| Observability | Debugging and operational visibility | Structured logs, metrics, traces, audit events |

### 2.3 Typical request lifecycle

~~~mermaid
sequenceDiagram
    actor User
    participant UI as Frontend
    participant API as API
    participant S as Feature service
    participant O as Orchestrator
    participant A as Agent / worker
    participant DB as Database
    participant C as Connector

    User->>UI: Submit goal or action
    UI->>API: Authenticated request
    API->>API: Validate payload, tenant and permission
    API->>S: Invoke business use case
    S->>DB: Create request / execution record
    S->>O: Start workflow if required
    O->>DB: Save plan and step states
    O->>A: Dispatch eligible step
    A->>A: Load scoped context and execute
    opt External action is permitted
        A->>C: Call connector
        C-->>A: Response / external reference
    end
    A->>DB: Persist result and execution evidence
    A-->>O: Step result
    O->>DB: Update aggregate workflow state
    API-->>UI: Return execution ID / initial state
    UI-->>User: Display progress, result, or approval request
~~~

## 3. Detailed directory structure

### 3.1 How to read this tree

This is a **recommended logical map**, not a source-verified inventory. Names may differ in the repository, and optional folders may not exist yet. Use it to understand intended responsibility and to organise future documentation; do not assume a path exists until it is confirmed in the checkout.

~~~text
octaos/
├── README.md                         # This product and engineering guide
├── .env.example                      # Safe template of required environment variable names
├── .gitignore                        # Excludes secrets, caches, build output and local data
├── Dockerfile                        # Container build, if supplied by the repository
├── docker-compose.yml                # Local service orchestration, if supplied
├── requirements.txt                  # Python dependencies, if this checkout uses it
├── pyproject.toml                    # Python packaging and tool configuration, if used
├── package.json                      # Root scripts only if this is a monorepo
├── alembic.ini                       # Migration configuration, if Alembic is used
├── alembic/                           # Versioned database migrations
│   └── versions/                     # Individual migration revisions
├── app/                               # Backend application package (logical)
│   ├── main.py                        # App creation, middleware, router registration
│   ├── api/                           # HTTP route handlers
│   │   ├── dependencies.py            # Shared auth, tenant and DB dependencies
│   │   └── v1/                        # Versioned route collection, if used
│   │       ├── health.py              # Liveness/readiness endpoints
│   │       ├── orchestrator.py        # Goal and execution endpoints
│   │       ├── marketing.py           # Campaign and content endpoints
│   │       ├── sales.py               # Lead, outreach and pipeline endpoints
│   │       ├── support.py             # Inbox, ticket and response endpoints
│   │       ├── people.py              # Candidate, HR and document endpoints
│   │       ├── operations.py          # Workflow and operational task endpoints
│   │       ├── knowledge.py           # Knowledge source and retrieval endpoints
│   │       ├── connectors.py          # Connection status and OAuth endpoints
│   │       └── analytics.py           # Reports and execution metrics
│   ├── core/                          # Cross-cutting platform functionality
│   │   ├── config.py                  # Environment-driven settings
│   │   ├── security.py                # Password/token/security utilities
│   │   ├── auth.py                    # Identity and authentication dependencies
│   │   ├── tenancy.py                 # Tenant resolution and scoping helpers
│   │   ├── permissions.py             # Role/action policy checks
│   │   ├── logging.py                 # Structured logging configuration
│   │   └── exceptions.py              # Shared API and domain error mapping
│   ├── db/                            # Database connection and transaction boundaries
│   │   ├── session.py                 # Engine/session creation
│   │   ├── base.py                    # ORM metadata/base declarations
│   │   └── repositories/              # Query and persistence helpers, if separated
│   ├── models/                        # Persistent entities
│   │   ├── user.py                    # Workspace identity
│   │   ├── tenant.py                  # Organisation / tenant
│   │   ├── execution.py               # Workflow and execution state
│   │   ├── agent.py                   # Agent metadata and configuration
│   │   ├── connector.py               # Connection metadata (not plaintext secrets)
│   │   ├── marketing.py               # Campaign/content records
│   │   ├── sales.py                   # Lead/opportunity records
│   │   ├── support.py                 # Conversation/ticket records
│   │   └── people.py                  # Candidate/document/onboarding records
│   ├── schemas/                       # Validated API input/output contracts
│   │   ├── common.py                  # Pagination, status, common response shapes
│   │   ├── execution.py               # Goal, run, step, and approval contracts
│   │   ├── marketing.py               # Campaign and content payloads
│   │   ├── sales.py                   # Lead and outreach payloads
│   │   ├── support.py                 # Support ticket and response payloads
│   │   └── people.py                  # Candidate and HR document payloads
│   ├── services/                      # Business use cases / domain operations
│   │   ├── orchestrator_service.py    # Goal-to-workflow entry point
│   │   ├── marketing_service.py      # Campaign lifecycle and validation
│   │   ├── sales_service.py          # Lead lifecycle and sales actions
│   │   ├── support_service.py        # Ticket lifecycle and response handling
│   │   ├── people_service.py         # Recruiting and HR workflows
│   │   └── connector_service.py      # Connection lifecycle and capability checks
│   ├── agents/                        # Bounded AI worker definitions (logical)
│   │   ├── registry.py               # Agent lookup and capability registry
│   │   ├── base.py                   # Shared agent contract and execution wrapper
│   │   ├── orchestrator/             # Intent, planning, routing, synthesis
│   │   ├── marketing/                # Research, strategy, copy, creative, QA
│   │   ├── sales/                    # Research, qualification, outreach, follow-up
│   │   ├── support/                  # Classification, retrieval, response, escalation
│   │   └── people/                   # Resume extraction, screening support, documents
│   ├── workflows/                     # Step graphs, conditions, state transitions
│   │   ├── engine.py                 # Workflow execution contract
│   │   ├── state_machine.py          # Valid state transitions
│   │   ├── definitions/               # Feature workflow definitions
│   │   └── validators.py              # Input/output and transition validation
│   ├── providers/                     # AI model/provider adapters
│   │   ├── registry.py               # Available provider registry
│   │   ├── router.py                 # Per-task provider/model selection
│   │   └── adapters/                  # Vendor-specific request/response adapters
│   ├── connectors/                    # External platform integrations
│   │   ├── base.py                   # Common connector contract
│   │   ├── registry.py               # Connector discovery/capability metadata
│   │   ├── social/                   # Social publishing APIs
│   │   ├── email/                    # Email and mailbox integrations
│   │   ├── messaging/                # WhatsApp/Telegram or other channels
│   │   ├── crm/                      # CRM and sales data integrations
│   │   ├── calendar/                 # Calendar and scheduling integrations
│   │   └── data_sources/              # Research/enrichment sources
│   ├── integrations/                  # Webhooks, callbacks and inbound events
│   │   ├── webhooks.py               # Shared verification and routing
│   │   └── handlers/                  # Event-specific handlers
│   ├── worker/                        # Async tasks and schedules
│   │   ├── celery_app.py             # Queue application, if Celery is used
│   │   ├── tasks.py                  # Registered task functions
│   │   └── schedules.py              # Periodic jobs, if configured
│   ├── knowledge/                     # Document ingestion and grounded retrieval
│   │   ├── ingestion.py              # File/source ingestion
│   │   ├── chunking.py               # Text segmentation
│   │   ├── retrieval.py               # Tenant-scoped retrieval
│   │   └── citations.py               # Source references for grounded answers
│   ├── analytics/                     # Metrics and report aggregation
│   └── utils/                         # Small generic helpers
├── frontend/                          # Web UI (actual name/framework must be verified)
│   ├── package.json                  # UI dependencies and scripts
│   ├── public/                        # Static files
│   └── src/
│       ├── app/                      # Routes, layouts and app shell
│       ├── components/               # Shared buttons, tables, dialogs and status UI
│       ├── features/                 # Feature-oriented pages and components
│       │   ├── orchestrator/         # Goal input, agent fleet and execution timeline
│       │   ├── marketing/            # Planner, campaigns, content, channels, reports
│       │   ├── sales/                # Leads, research, outreach, inbox, pipeline
│       │   ├── support/              # Inbox, tickets, AI drafts and handoff
│       │   ├── people/               # Candidates, HR documents, onboarding
│       │   ├── operations/           # Tasks, workflow builder, operational reports
│       │   ├── knowledge/             # Sources, documents, retrieval configuration
│       │   └── settings/              # Users, roles, providers and connectors
│       ├── services/                 # API client and request utilities
│       ├── hooks/                    # Reusable UI hooks
│       ├── types/                    # TypeScript/API contracts
│       └── utils/                    # Formatting and UI helpers
├── tests/                             # Automated test suite
│   ├── unit/                         # Isolated business logic and agent tests
│   ├── integration/                  # Database, provider and connector tests
│   ├── api/                          # Route and permission tests
│   └── workflows/                    # End-to-end workflow state tests
├── docs/                              # Supporting architecture and feature documentation
└── scripts/                           # Local setup, migration and maintenance scripts
~~~

### 3.2 Directory responsibility boundaries

| Directory | Owns | Avoid putting here |
|---|---|---|
| api | HTTP contracts, route dependencies, status codes | Large domain workflows and raw provider logic |
| core | Auth, configuration, tenancy, permissions, logging | Department-specific business decisions |
| models | Persistent data structures and relationships | AI prompts, network requests, orchestration |
| schemas | Input/output validation contracts | Database queries and side effects |
| services | Domain use cases and transaction coordination | One giant service for all departments |
| agents | Task-specific instructions, tool access, output validation | Unrestricted access to every tool or tenant |
| workflows | Step definitions, dependencies, transitions and retries | Hidden actions without state/evidence |
| providers | Model routing and vendor-specific model calls | Feature logic tied to one provider |
| connectors | External API request/response mapping and auth | Cross-department business rules |
| integrations | Verified inbound webhooks and callbacks | Trusting unverified events |
| worker | Async jobs, schedules, timeouts and retries | Untracked background threads |
| knowledge | Ingestion, indexing, retrieval and source references | Cross-tenant document search |
| frontend/features | Feature-specific UI and client contracts | Duplicated backend business logic |
| tests | Regression, permissions, integration and workflow behavior | Only happy-path coverage |

### 3.3 Suggested feature subdirectory map

This map shows the breadth of the product taxonomy. It is not a verified file listing.

~~~text
frontend/src/features/
├── orchestrator/
│   ├── command-center/       # Goal input, suggested tasks and status overview
│   ├── agent-directory/      # Agent catalogue, capabilities and availability
│   ├── executions/            # Runs, step timeline, logs and output inspection
│   ├── approvals/             # Human review queue and action confirmation
│   └── settings/              # Provider/model and orchestration preferences
├── marketing/
│   ├── business-context/      # Brand, product, audience, offer and constraints
│   ├── strategy/              # Objectives, funnel, positioning and channel plan
│   ├── campaigns/             # Brief, audience, budget, dates and goals
│   ├── content-studio/        # Copy, blog, landing page, email and social content
│   ├── seo-content/           # Search-led content planning and optimisation
│   ├── social-media/          # Channel-specific content and publishing calendar
│   ├── paid-media/            # Paid campaign briefs and creative variants
│   ├── email-marketing/       # Newsletter, nurture and lifecycle sequences
│   ├── influencer-marketing/  # Creator discovery, fit, briefs and performance
│   ├── creative-production/   # Image/video brief and asset workflow
│   ├── cro/                   # Landing page and conversion experiment ideas
│   ├── approvals/             # Brand, compliance and human approval
│   └── analytics/             # Campaign results and learnings
├── sales/
│   ├── lead-capture/          # Inbound and imported leads
│   ├── enrichment/            # Company/contact research and source records
│   ├── qualification/         # Fit, intent, need, budget and readiness
│   ├── outreach/              # Personalised email/message drafts and sequences
│   ├── inbox/                 # Replies, intent classification and routing
│   ├── meetings/              # Calendar availability, booking and prep
│   ├── pipeline/              # Stages, ownership, tasks and opportunity history
│   └── analytics/             # Funnel, conversion and activity reports
├── support/
│   ├── inbox/                 # Email/chat/message conversations
│   ├── triage/                # Classification, priority and routing
│   ├── knowledge/             # Searchable support answers
│   ├── responses/             # Suggested answers and response quality checks
│   ├── escalation/            # Human handoff and SLA tracking
│   └── analytics/             # Volume, resolution and recurring issue analysis
├── people/
│   ├── recruiting/            # Requisitions, candidates and stages
│   ├── resume-parsing/        # Structured candidate profile extraction
│   ├── screening/             # Criteria-based review assistance
│   ├── interviews/            # Scheduling, scorecards and feedback
│   ├── documents/             # Template mapping, generation and review
│   ├── onboarding/            # Task plans, forms and joining workflows
│   └── approvals/             # HR review and authorised decisions
├── operations/
│   ├── workflow-builder/      # Configurable triggers, nodes and conditions
│   ├── tasks/                 # Assignments, due dates and status
│   ├── process-automation/    # Repetitive cross-team processes
│   ├── integrations/          # Connection setup and event status
│   └── reporting/             # Operational exceptions and throughput
├── knowledge/
│   ├── sources/               # Connected sources and uploaded documents
│   ├── ingestion/             # Import status and errors
│   ├── search/                # Search and retrieval controls
│   └── access/                # Source permissions and tenant boundaries
└── settings/
    ├── workspace/             # Company profile and defaults
    ├── members/               # Users and membership
    ├── roles/                 # Role and permission configuration
    ├── providers/             # AI provider/model settings
    └── connectors/            # External account connections
~~~

## 4. Shared workflow lifecycle

Most agent-assisted features should use a common execution pattern so users can understand the status and developers can test the same guarantees across modules.

### 4.1 Lifecycle diagram

~~~mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Validating
    Validating --> Rejected: Invalid input / not authorised
    Validating --> Queued: Valid request
    Queued --> Running
    Running --> WaitingApproval: Approval required
    WaitingApproval --> Running: Approved
    WaitingApproval --> Cancelled: Rejected or cancelled
    Running --> RetryScheduled: Retryable failure
    RetryScheduled --> Running: Retry allowed
    Running --> Succeeded: Output and completion checks pass
    Running --> Failed: Non-retryable / retry limit reached
    Running --> Cancelled: Cancellation accepted
    Succeeded --> [*]
    Failed --> [*]
    Rejected --> [*]
    Cancelled --> [*]
~~~

### 4.2 Standard step contract

A workflow step should define:

- Stable step ID and workflow version.
- Responsible agent/service and required capability.
- Input schema and allowed context sources.
- Required tools and permission scopes.
- Dependencies and execution condition.
- Timeout, retry policy, rate-limit handling and idempotency key.
- Output schema and validation rules.
- Approval requirement and the role allowed to approve.
- Evidence/source references and external action IDs.
- Start/end timestamps, status, attempt count and failure details.

### 4.3 General workflow rules

1. Validate tenant and user permissions before creating side effects.
2. Persist the execution before dispatching asynchronous work.
3. Pass only the minimum required context to each agent.
4. Validate agent output before it becomes an input to another step.
5. Treat model output as untrusted input; never execute arbitrary code or instructions from retrieved content.
6. Use approval gates for actions with material external consequences.
7. Make retries safe with idempotency or a deduplication strategy.
8. Record connector response IDs and distinguish attempted actions from confirmed actions.
9. Mark unavailable integrations as unavailable; do not silently pretend that the step succeeded.
10. Preserve enough execution history to explain why a result was produced.

## 5. Orchestrator and AI Workforce

### Purpose

The Orchestrator is the cross-department entry point for turning a natural-language goal into a sequence of actionable tasks. It should coordinate domain modules rather than reimplement every module's business logic.

### Sub-features

- **Goal intake:** accept the user's objective, context, constraints, desired output, time horizon, and budget where relevant.
- **Intent and domain routing:** identify whether the request belongs to Marketing, Sales, Support, People & HR, Operations, or multiple departments.
- **Plan generation:** produce an explicit sequence of tasks with dependencies and expected outputs.
- **Agent directory:** show available agents, their responsibilities, permitted tools, status, and limitations.
- **Execution timeline:** display queued/running/completed/failed steps, attempts, duration, and outputs.
- **Cross-department coordination:** pass validated outputs between modules through explicit contracts.
- **Provider/model selection:** choose a configured provider/model for a task where supported.
- **Approval queue:** pause before high-impact external actions.
- **Recovery:** retry safe failures, resume eligible steps, or stop a workflow with a clear reason.
- **Result synthesis:** combine verified step outputs into a final brief with unresolved items and evidence.
- **Execution history:** inspect previous runs and compare results.
- **Operational controls:** cancellation, timeout, concurrency limits, and cost controls where implemented.

### Orchestrator workflow diagram

~~~mermaid
flowchart TD
    A[User states business goal] --> B[Validate request and tenant permissions]
    B --> C[Extract objective, constraints, deliverable and success criteria]
    C --> D[Classify intent and required capabilities]
    D --> E[Build explicit task plan and dependencies]
    E --> F{Plan valid and permitted?}
    F -- No --> G[Ask for clarification or return validation error]
    F -- Yes --> H[Persist execution and planned steps]
    H --> I[Dispatch ready steps]
    I --> J[Run specialist agent or domain service]
    J --> K[Validate output and evidence]
    K --> L{Needs approval or external action?}
    L -- Yes --> M[Pause for authorised human review]
    M --> N{Approved?}
    N -- No --> O[Cancel or revise step]
    N -- Yes --> P[Execute approved action]
    L -- No --> Q[Record step result]
    P --> Q
    Q --> R{All dependencies satisfied?}
    R -- No --> S[Retry, wait, or mark blocked/failed]
    S --> I
    R -- Yes --> T[Aggregate results and unresolved items]
    T --> U[Persist final status and show report]
~~~

### Orchestrator agent roles

| Role | Responsibility | Expected output |
|---|---|---|
| Intent classifier | Identify goal type and required capability groups | Structured intent and confidence |
| Planner | Break the goal into dependent tasks | Versioned plan with success criteria |
| Capability router | Match tasks to available agents/services | Agent assignment and rationale |
| Context builder | Retrieve relevant tenant-scoped information | Bounded context with source references |
| Specialist agents | Perform bounded domain tasks | Typed task output |
| Validator / critic | Check structure, consistency, policy, and requirements | Pass/fail plus actionable findings |
| Approval controller | Determine whether a step requires human review | Approval request or permission decision |
| Execution coordinator | Manage dependencies, state, retries and cancellation | Updated step/workflow state |
| Result synthesiser | Produce a coherent final response from completed steps | Summary, outputs, limitations and next steps |

Do not assume these are separate deployed agents. They are logical responsibilities and may be implemented as functions, services, prompts, or separate workers.

## 6. Marketing and Campaign Planner

### Purpose

Marketing workflows should understand the business, product, audience, positioning, offer, brand constraints, campaign objective, budget, and target channels before producing content. A campaign planner should coordinate the work from brief to approved assets and measured outcomes.

### Marketing sub-feature catalogue

| Marketing type | Sub-features | Typical output |
|---|---|---|
| Marketing strategy | Business/context intake, positioning, value proposition, ICP/personas, funnel mapping, channel selection, objectives and KPIs | Strategy brief and campaign priorities |
| Campaign planning | Campaign brief, audience, offer, messaging pillars, budget allocation, calendar, channel plan and milestones | Campaign plan with deliverables |
| Brand marketing | Brand voice, key messages, differentiators, proof points, consistency checks and approved claims | Brand-aligned messaging framework |
| Content marketing | Topic clusters, content calendar, blogs, articles, guides, case studies, lead magnets and repurposing | Content plan and drafts |
| SEO-led content | Search intent, keyword/topic mapping, on-page recommendations, internal linking ideas and content refresh briefs | Search-oriented content brief; live ranking claims require actual data |
| Social media marketing | Platform-specific post variants, content pillars, captions, hashtags, calendar, community response drafts and repurposing | Channel-ready social drafts |
| Paid advertising | Campaign concepts, audience hypotheses, ad copy variants, creative briefs, landing-page alignment and budget suggestions | Paid-media brief and variants; live ad changes require authorised ad-platform access |
| Email marketing | Newsletter, welcome series, nurture sequence, re-engagement, product updates and lifecycle copy | Email drafts and sequence plan |
| Influencer / creator marketing | Creator discovery criteria, niche and audience fit, brand-safety review, outreach draft, campaign brief, deliverables and performance review | Shortlist, outreach drafts and creator brief; discovery requires data sources |
| Video marketing | Short-form scripts, hooks, storyboard, shot list, subtitles/captions, repurposing plan and video-generation handoff | Script/storyboard/asset brief |
| Visual / creative production | Image briefs, visual direction, format variants, creative QA and asset handoff | Creative brief or generated asset when a configured tool is available |
| Product marketing | Product narrative, feature-to-benefit mapping, launch messaging, competitive positioning and release content | Launch brief and product messaging |
| Event / webinar marketing | Event concept, registration page copy, promotion calendar, reminder sequence and follow-up content | Event promotion workflow |
| Partner / affiliate marketing | Partner fit criteria, co-marketing concepts, referral messaging and campaign tracking requirements | Partner brief and co-marketing plan |
| Conversion-rate optimisation (CRO) | Funnel review, landing-page hypotheses, CTA and form ideas, experiment design and measurement plan | Prioritised experiment backlog; results need analytics evidence |
| Reputation / community marketing | Review-response drafts, FAQ content, community themes and escalation cues | Response drafts and community content plan |
| Marketing analytics | KPI definitions, campaign comparisons, content performance, channel attribution inputs and lessons learned | Performance report based on connected data |
| Marketing automation | Triggered journeys, lead nurture logic, audience segments, lifecycle conditions and workflow schedules | Automation specification / workflow |
| Local / regional marketing | Location-specific messaging, regional offers, local landing-page briefs and localisation | Local campaign variants |
| International marketing | Language and market variants, localisation review, regional constraints and channel adaptation | Localised campaign package; human linguistic review may be required |

**Scope boundary:** The table describes a broad marketing taxonomy for documenting the product. It does not assert that every marketing type has a complete, production-ready UI, backend service, agent, and connector today. Verify each sub-feature against implementation.

### Campaign Planner sub-features

1. **Business understanding:** capture company profile, product/service, differentiators, pricing/offer constraints, audience, target markets, brand voice, approved claims, and excluded claims.
2. **Campaign brief:** objective, funnel stage, audience, key message, offer, channels, budget, dates, deliverables, and measurement plan.
3. **Research and evidence:** collect permitted source material, competitor/context notes, audience insights, and source links. Keep sourced facts separate from hypotheses.
4. **Strategy and narrative:** define campaign angle, message pillars, hooks, CTA, objections, and creative direction.
5. **Content production:** create channel-specific copy, variants, scripts, email sequences, and creative briefs.
6. **AI influencer / creator workflow:** translate product and audience context into creator criteria; shortlist only when a configured discovery source is available; assess audience fit and brand safety; draft outreach and deliverables; track response and results when data is connected.
7. **Brand and factual QA:** check tone, banned claims, unsupported statistics, prohibited language, link/CTA presence, channel limits, and consistency.
8. **Review and approval:** send drafts to an authorised reviewer before publishing or sending where required.
9. **Scheduling and publishing:** create channel-specific scheduled items through supported connectors; record the external platform ID and returned status.
10. **Measurement and learning:** ingest connected metrics, compare against defined KPIs, record limitations, and use results to inform the next plan.

### Marketing end-to-end flow

~~~mermaid
flowchart TD
    A[Marketing request] --> B[Load tenant brand and product context]
    B --> C[Clarify goal, audience, market, budget and deadline]
    C --> D[Research permitted sources and record evidence]
    D --> E[Marketing strategist: plan funnel, channel mix and KPIs]
    E --> F[Campaign planner: create brief, calendar and deliverables]
    F --> G{Which deliverables are needed?}
    G --> H[Content agent: blogs, landing pages and lead magnets]
    G --> I[Social agent: platform-specific posts and calendar]
    G --> J[Email agent: newsletter and nurture sequence]
    G --> K[Paid-media agent: ad concepts and variants]
    G --> L[Creator agent: influencer fit, outreach and brief]
    G --> M[Creative agent: image/video scripts and asset briefs]
    H --> N[Brand, factual and channel QA]
    I --> N
    J --> N
    K --> N
    L --> N
    M --> N
    N --> O{QA passes?}
    O -- No --> P[Return targeted revisions to creator]
    P --> N
    O -- Yes --> Q[Human approval where required]
    Q --> R{Approved?}
    R -- No --> S[Revise, hold or cancel]
    R -- Yes --> T[Schedule or publish through configured connector]
    T --> U[Record platform response and content ID]
    U --> V[Collect connected performance metrics]
    V --> W[Report outcomes, data gaps and next experiments]
~~~

### Influencer marketing agent workflow

~~~mermaid
flowchart TD
    A[Product, audience and campaign goal] --> B[Extract niche, geography, audience and brand constraints]
    B --> C[Define creator scoring rubric]
    C --> D{Discovery connector configured?}
    D -- No --> E[Return criteria and request data/source; do not invent creators]
    D -- Yes --> F[Retrieve candidate profiles and source metadata]
    F --> G[Validate candidate fields and source freshness]
    G --> H[Score relevance, audience fit, engagement evidence, brand safety and cost fit]
    H --> I[Flag missing, suspicious or unverifiable metrics]
    I --> J[Rank candidates with transparent rationale]
    J --> K[Human review of shortlist]
    K --> L[Prepare personalised outreach and campaign brief]
    L --> M{Outreach approved?}
    M -- No --> N[Revise or stop]
    M -- Yes --> O[Send via authorised channel connector]
    O --> P[Track reply and agreed deliverables when connected]
    P --> Q[Collect campaign metrics and compare to goals]
    Q --> R[Report outcomes with data-source limitations]
~~~

### Marketing specialist agent responsibilities

| Agent role | Input | Output / checks |
|---|---|---|
| Brand/context analyst | Business profile, product docs, prior approved content | Structured brand/product context and missing information |
| Audience researcher | Target market and research sources | Audience needs and source-linked findings |
| Campaign strategist | Goal, audience, offer, budget, channel constraints | Strategy, funnel stage, KPI definitions |
| Content planner | Strategy and publishing cadence | Content themes and calendar |
| Copywriter | Brief, tone, channel and CTA | Drafts with required fields and variants |
| SEO content planner | Search intent and available SEO evidence | Topic/content brief; no invented search volume |
| Social channel adapter | Approved core message and channel rules | Platform-specific versions |
| Email journey planner | Lifecycle stage and trigger conditions | Sequence, timing and stop conditions |
| Creator researcher | Creator criteria and discovery results | Evidence-linked shortlist and uncertainty flags |
| Creative director | Message and visual requirements | Creative direction, script or production brief |
| Brand/fact checker | Draft, brand rules, source claims | Violations and corrections |
| Channel validator | Destination platform constraints | Format and length validation |
| Campaign judge | All outputs and original brief | Completeness, alignment and revision list |
| Publisher | Approved content and authorised connection | Submission result and external reference |
| Performance analyst | Connected performance data and KPI definitions | Report, caveats and next tests |

### Marketing approval boundary

A generated draft is not a published post. A campaign plan is not a live ad campaign. An influencer shortlist is not proof of availability or audience authenticity. Paid media, outbound messages, public publishing, and budget changes should require the correct permissions and explicit approval where applicable.

## 7. Sales and revenue operations

### Purpose

Sales workflows support the journey from lead intake and research through qualification, personalised outreach, reply handling, meeting scheduling, pipeline management, and reporting.

### Sales sub-feature catalogue

- **Lead capture/import:** forms, manual entry, approved imports, inbound requests, and source attribution.
- **Lead enrichment:** company profile, industry, geography, website, relevant events, job postings, and contact research from configured sources.
- **ICP matching:** compare the prospect with target industry, company size, location, use case, and exclusion rules.
- **Contact discovery:** locate business contact information only through permitted sources; retain provenance and confidence.
- **Qualification:** assess fit, need, intent, timing, budget evidence, authority, and disqualifiers.
- **Lead scoring:** configurable weighted scoring with reasons; missing evidence must not be treated as positive evidence.
- **Research brief:** summarise company context, likely business needs, relevant trigger events, and unknowns.
- **Personalised outreach:** draft emails or messages tied to verified prospect context.
- **Cadence management:** sequence steps, timing, stop conditions, opt-out handling, and duplicate prevention.
- **Inbox/reply handling:** classify replies, identify positive interest, objections, unsubscribe, out-of-office, and requests for human follow-up.
- **Meeting scheduling:** check permitted calendar availability, propose times, create events, and send confirmations when connected.
- **Pipeline and ownership:** stages, owners, next actions, tasks, history, and stale-deal reminders.
- **Sales enablement:** call prep, discovery questions, objection handling, follow-up summaries, and proposal drafts.
- **Analytics:** lead-source quality, stage conversion, response rates, meeting rates, and data completeness.

### Sales workflow diagram

~~~mermaid
flowchart TD
    A[Lead arrives or is imported] --> B[Validate tenant, source, consent and duplicates]
    B --> C[Enrich company and contact from configured sources]
    C --> D[Record sources, freshness and missing fields]
    D --> E[Compare with ICP and exclusion rules]
    E --> F[Qualification agent scores fit, need, intent and timing]
    F --> G{Meets criteria and evidence threshold?}
    G -- No --> H[Disqualify, nurture, or request human review]
    G -- Yes --> I[Research brief and personalised message draft]
    I --> J[Compliance, suppression and duplicate checks]
    J --> K{Outbound approval / policy satisfied?}
    K -- No --> L[Hold for review or block]
    K -- Yes --> M[Send through authorised connector]
    M --> N[Record external message ID and status]
    N --> O[Monitor inbox and classify reply]
    O --> P{Reply type}
    P -- Interested --> Q[Prepare response and meeting options]
    P -- Objection --> R[Draft contextual follow-up for review]
    P -- Unsubscribe --> S[Suppress future outreach]
    P -- Out of office --> T[Schedule permitted follow-up or pause]
    P -- Human needed --> U[Assign owner and transfer context]
    Q --> V[Book meeting when approved and calendar is connected]
    R --> W[Human review / next action]
    V --> X[Update pipeline, task and activity history]
    W --> X
    U --> X
    H --> X
~~~

### Lead qualification agent workflow

~~~mermaid
flowchart LR
    A[Lead record] --> B[Check required fields and provenance]
    B --> C[Retrieve company and contact evidence]
    C --> D[Fit analysis]
    C --> E[Need / trigger analysis]
    C --> F[Intent and timing analysis]
    C --> G[Budget / authority evidence]
    D --> H[Apply configured scorecard]
    E --> H
    F --> H
    G --> H
    H --> I[Check exclusions and confidence]
    I --> J{Sufficient evidence?}
    J -- No --> K[Mark unknowns and request research or human review]
    J -- Yes --> L[Return score, rationale and recommended next step]
    K --> M[Persist result with source links]
    L --> M
~~~

### Example configurable scoring model

A sales team may configure a weighted score such as company fit, problem relevance, intent, growth signals, and contactability. Weights are business configuration, not universal truth. Every score should show the factors, evidence, missing fields, and rule version that produced it. Do not fabricate budget, buying intent, or contact details.

## 8. Customer Support

### Purpose

Support workflows help triage inbound conversations, retrieve grounded answers, draft replies, route cases, and escalate to a human when confidence, risk, or customer need requires it.

### Support sub-features

- **Multi-channel intake:** connected email, web chat, messaging, and other supported inbox sources.
- **Conversation normalisation:** map external message formats into a common internal conversation model.
- **Classification:** topic, intent, urgency, product area, sentiment cues, and language where supported.
- **Priority and SLA:** priority rules, due times, queue routing, and overdue alerts.
- **Knowledge retrieval:** search tenant-approved documentation and cite source references.
- **Reply drafting:** create context-aware drafts grounded in conversation history and approved knowledge.
- **Response QA:** check policy, tone, factual support, missing details, and unsafe promises.
- **Human handoff:** assign the conversation with summary, attempted steps, sources, and open questions.
- **Follow-up reminders:** track unresolved cases and next actions.
- **Feedback loop:** record corrections and recurring knowledge gaps.
- **Analytics:** volume, first-response time, resolution time, escalation rate, and recurring issue categories when source data is available.

### Support workflow diagram

~~~mermaid
flowchart TD
    A[Inbound customer message] --> B[Verify source / webhook and map conversation]
    B --> C[Load tenant, customer and conversation context]
    C --> D[Classify intent, topic and urgency]
    D --> E[Check policy and escalation triggers]
    E --> F{Sensitive, high-risk or unclear?}
    F -- Yes --> G[Route to human with context summary]
    F -- No --> H[Retrieve approved knowledge and source passages]
    H --> I[Draft grounded response]
    I --> J[Check answer against sources and support policy]
    J --> K{Confidence and policy checks pass?}
    K -- No --> G
    K -- Yes --> L{Auto-send explicitly allowed?}
    L -- No --> M[Place draft in agent review queue]
    L -- Yes --> N[Send through connected channel]
    M --> O[Human edits and approves]
    O --> N
    N --> P[Record external message ID and delivery result]
    P --> Q[Update ticket status, SLA and audit trail]
    G --> R[Human resolves or requests more information]
    R --> Q
~~~

### Support agent roles

| Role | Responsibility |
|---|---|
| Intake normaliser | Validate incoming event and map channel fields |
| Triage classifier | Determine topic, urgency and routing recommendation |
| Context retriever | Find relevant tenant-scoped conversation and knowledge context |
| Response drafter | Produce a draft grounded in retrieved sources |
| Policy / quality checker | Detect unsupported claims, policy conflicts and missing information |
| Escalation router | Route to the right queue/person and attach a concise handoff |
| Resolution analyst | Summarise patterns and identify missing documentation |

## 9. People and HR

### Purpose

People & HR workflows support recruitment and employee lifecycle administration. HR workflows should assist with structured review and document preparation while preserving human control over consequential employment decisions.

### HR sub-feature catalogue

- **Workforce/requisition intake:** role description, skills, location, seniority, compensation band, and hiring constraints.
- **Candidate intake:** resume upload, application forms, source and consent metadata.
- **Resume parsing:** extract skills, experience, education, roles, dates, and contact fields into a reviewable profile.
- **Candidate deduplication:** identify potential duplicates without silently merging uncertain identities.
- **Screening support:** compare stated qualifications with explicit job criteria and show evidence from the resume.
- **Pipeline/stages:** configurable statuses such as sourced, screened, interviewing, offer, hired, and rejected where used.
- **Interview coordination:** availability, scheduling, calendar invites, interviewer assignments, and reminders when connected.
- **Interview kits:** structured questions, role-specific scorecards, and feedback forms.
- **Document templates:** map approved templates to candidate/employee fields; preserve missing fields for human completion.
- **Document generation and review:** create draft offer/contract/onboarding documents for authorised review.
- **Onboarding workflows:** tasks, required forms, joining checklist, owners, due dates, and completion status.
- **Approvals and audit:** authorised sign-off, version history, and traceable document changes.
- **HR reporting:** funnel, time-in-stage, workload, and document completion when data supports it.

### HR workflow diagram

~~~mermaid
flowchart TD
    A[Create role / requisition] --> B[Define job criteria and approval]
    B --> C[Receive candidate application]
    C --> D[Validate file, consent and candidate fields]
    D --> E[Extract resume data into structured profile]
    E --> F[Check extraction quality and possible duplicates]
    F --> G[Compare profile to explicit job criteria]
    G --> H[Produce evidence-linked screening summary]
    H --> I[Recruiter reviews and decides next stage]
    I --> J{Move forward?}
    J -- No --> K[Record authorised disposition and status]
    J -- Yes --> L[Coordinate interview and calendar]
    L --> M[Collect interviewer feedback]
    M --> N[Human hiring decision]
    N --> O{Offer approved?}
    O -- No --> P[Continue process or close requisition]
    O -- Yes --> Q[Populate approved document template]
    Q --> R[Validate missing fields and generate draft]
    R --> S[HR/legal review and approval]
    S --> T[Send/sign only through configured authorised workflow]
    T --> U[Create onboarding tasks and deadlines]
    U --> V[Track completion and preserve audit history]
~~~

### HR agent roles and guardrails

- **Resume extractor:** extracts structured facts and marks uncertain values; it must not infer missing qualifications.
- **Criteria matcher:** compares only with documented job criteria and points to supporting resume evidence.
- **Interview planner:** proposes interview structure and scheduling options.
- **Document field mapper:** maps approved source fields into a versioned template and flags missing fields.
- **Onboarding coordinator:** creates checklist tasks and reminders.
- **Compliance checker:** flags missing approvals, required fields, and process inconsistencies.

AI should not autonomously make final hiring, rejection, compensation, disciplinary, or termination decisions. Human review and applicable legal requirements remain essential.

## 10. Operations and workflow automation

### Purpose

Operations workflows coordinate repeatable tasks and cross-department processes using explicit triggers, conditions, actions, ownership, and recovery rules.

### Sub-features

- **Workflow builder:** create/edit workflow definitions, steps, conditions, and dependencies.
- **Trigger catalogue:** manual request, schedule, webhook, status change, or other implemented event.
- **Conditional routing:** branch on validated business fields and rules.
- **Task management:** assign owner, due date, priority, status, and linked business object.
- **Cross-department workflows:** pass explicit outputs between Sales, Marketing, Support, and HR.
- **Approvals:** route a decision to a permitted reviewer.
- **Scheduled jobs:** run recurring permitted work and report missed/failed runs.
- **Exception handling:** retry safe transient failures; route permanent failures to an operator.
- **Connector health:** show configured/connected/expired/failed state where measurable.
- **Audit history:** record who triggered, approved, changed, or cancelled a workflow.

### Workflow builder diagram

~~~mermaid
flowchart TD
    A[User configures workflow] --> B[Validate nodes, fields and connections]
    B --> C[Validate permissions and required connectors]
    C --> D{Definition valid?}
    D -- No --> E[Show configuration errors]
    D -- Yes --> F[Save versioned workflow]
    F --> G[Receive trigger]
    G --> H[Create execution and snapshot workflow version]
    H --> I[Evaluate eligible node]
    I --> J[Run action or agent step]
    J --> K[Validate output and record status]
    K --> L{Conditional branch / more steps?}
    L -- Yes --> I
    L -- No --> M{Approval required?}
    M -- Yes --> N[Wait for authorised approval]
    N --> O{Approved?}
    O -- No --> P[Stop or route for revision]
    O -- Yes --> Q[Continue permitted action]
    M -- No --> R[Evaluate completion conditions]
    Q --> R
    R --> S[Persist final state and execution report]
~~~

### Workflow execution states

Use explicit states such as draft, active, paused, queued, running, waiting for approval, retry scheduled, succeeded, failed, and cancelled. The exact enum names should match the actual code. Keep workflow definition version separate from execution state so an edit does not silently rewrite a running job's logic.

## 11. Real-estate sales workflows

This section documents a domain workflow pattern relevant when real-estate functionality is enabled in the deployment. It is not proof that a real-estate module is present in every branch or tenant.

### Sub-features

- **Project and inventory catalogue:** projects, units, unit attributes, availability, and pricing rules.
- **Lead-to-project matching:** compare buyer requirements, budget range, preferred location, configuration, and timeline with available inventory.
- **Salesperson assignment:** assign an owner based on workload, territory, location, skill, availability, and priority rules.
- **Visit planning:** propose site visits and group nearby appointments where location data and mapping integrations are available.
- **Appointment scheduling:** reserve time slots and record confirmations/cancellations.
- **Inventory holds:** time-bound hold with concurrency control and clear expiry/release behaviour where implemented.
- **Follow-up:** visit outcome, buyer interest, objections, next action, and reminders.
- **Broker/channel tracking:** record referral source and configured commission rules.
- **Field-sales coordination:** location telemetry and route recommendations only with appropriate consent, permissions, and mobile support.
- **Reporting:** lead response, visits, conversion, inventory status, and source quality.

### Real-estate lead-to-visit workflow

~~~mermaid
flowchart TD
    A[New buyer lead] --> B[Capture requirements and consent]
    B --> C[Match project and available units]
    C --> D[Check inventory freshness and constraints]
    D --> E[Recommend eligible units with rationale]
    E --> F[Assign salesperson using configured rules]
    F --> G[Check salesperson and buyer availability]
    G --> H[Suggest visit slots and route plan when supported]
    H --> I[Human or buyer confirms visit]
    I --> J[Create appointment and notify participants]
    J --> K[Record visit outcome and buyer feedback]
    K --> L{Next step}
    L --> M[Follow-up / second visit]
    L --> N[Authorised inventory hold or reservation]
    L --> O[Mark not interested / nurture]
    M --> P[Update CRM history and reminders]
    N --> P
    O --> P
~~~

Inventory reservation, deposits, commission calculation, and location tracking require explicit business rules, concurrency safety, permission checks, and auditability.

## 12. Knowledge and business context

### Purpose

Knowledge services provide a controlled source of company, product, policy, support, sales, and brand context to workflows and agents. Knowledge retrieval should be tenant-scoped and source-aware.

### Sub-features

- **Source management:** upload files or connect supported repositories/systems.
- **Ingestion:** validate file type, extract text, track processing status, and report parse failures.
- **Chunking/indexing:** prepare content for retrieval using the configured search/index system.
- **Metadata and access control:** associate tenant, source, owner, timestamps, permissions, and document version.
- **Semantic/keyword retrieval:** find relevant passages using configured retrieval capabilities.
- **Grounded generation:** give agents only relevant passages and request source-linked answers.
- **Citations/provenance:** retain document and passage references used by a response.
- **Freshness/reindexing:** detect changed or removed source content and handle stale indexes.
- **Deletion lifecycle:** remove or invalidate indexed content when the source is deleted or access is revoked.
- **Knowledge-gap reporting:** identify repeated questions with no reliable answer.

### Knowledge ingestion and retrieval diagram

~~~mermaid
flowchart TD
    A[Approved upload or connected source] --> B[Authenticate source and check tenant access]
    B --> C[Validate type, size and processing policy]
    C --> D[Extract text and metadata]
    D --> E[Chunk and index content]
    E --> F[Persist source version and ingestion status]
    G[Agent task] --> H[Construct scoped retrieval query]
    H --> I[Retrieve permitted relevant passages]
    I --> J[Apply relevance and access filters]
    J --> K[Generate answer from retrieved context]
    K --> L[Attach source references and uncertainty]
    L --> M[Validate answer before use]
~~~

Retrieved documents are untrusted content. They must not be allowed to override system policy, expand permissions, or instruct an agent to reveal secrets or call unrelated tools.

## 13. Social publishing and communications

### Social publishing sub-features

- **Channel connection:** connect a supported account with least-privilege OAuth scopes.
- **Channel capability discovery:** distinguish supported post types, media formats, account types, and actions per platform.
- **Content adaptation:** adapt one approved core message to the destination platform's format.
- **Media handling:** validate dimensions, size, duration, file type, and platform-specific requirements.
- **Calendar and scheduling:** draft, review, schedule, and track scheduled items.
- **Publishing status:** distinguish queued, submitted, published, rejected, and unknown status.
- **Retry and duplicate protection:** prevent accidental duplicate posts after timeout or uncertain response.
- **Inbox/community response:** draft or route replies where supported.
- **Analytics:** import available engagement metrics with time range and source metadata.
- **Connection health:** show token expiry, missing scopes, provider errors, and reconnect actions.

### Publishing workflow diagram

~~~mermaid
flowchart TD
    A[Approved campaign asset] --> B[Choose destination accounts]
    B --> C[Check account permissions and platform capabilities]
    C --> D[Adapt copy and validate media]
    D --> E[Preview final destination-specific payload]
    E --> F[Approval gate if required]
    F --> G[Schedule or publish via connector]
    G --> H{Connector response}
    H -- Confirmed --> I[Store platform post ID and status]
    H -- Rejected --> J[Show platform error and remediation]
    H -- Timeout / unknown --> K[Reconcile before retry to avoid duplicate]
    I --> L[Sync available analytics]
    L --> M[Report results and source coverage]
~~~

### Communication channel notes

Email, WhatsApp, Telegram, social networks, and calendars have different authentication, policy, and delivery semantics. Do not present them as interchangeable. A connector being listed in settings does not mean all actions, media types, account types, or webhook events are supported.

## 14. Analytics, reporting, and auditability

### Reporting sub-features

- **Feature dashboards:** status and performance for a specific business module.
- **Execution reports:** workflow outcomes, duration, retries, failed steps, and approval waits.
- **Marketing reporting:** campaign and channel KPIs from connected data.
- **Sales reporting:** lead sources, qualification, outreach activity, meetings, and stage conversion.
- **Support reporting:** case volume, response/resolution time, escalation and recurring topics.
- **HR reporting:** recruitment stages, time-in-stage, interview scheduling, and onboarding completion.
- **Operations reporting:** throughput, overdue tasks, connector health, and exception counts.
- **Audit trail:** actor, action, timestamp, target record, approval, and external response ID.
- **Data freshness:** last successful sync and the period covered by a metric.
- **Export:** only formats and data ranges actually supported by the implementation.

### Analytics trust rules

- Define every metric, its time window, source, and aggregation.
- Distinguish zero from missing, stale, unavailable, or unconfigured data.
- Do not invent values when a connector is disconnected.
- Separate model-generated recommendations from measured outcomes.
- Keep currency, timezone, attribution, and denominator definitions explicit.
- Treat external platform metrics as source-provided values and retain sync timestamps.

## 15. Agent architecture and diagrams

### 15.1 Standard agent contract

Every specialist agent should have a clearly defined:

1. Name and purpose.
2. Input schema and required context.
3. Allowed tools and permission scopes.
4. Prompt/instruction version.
5. Provider/model policy and timeout.
6. Output schema.
7. Validation and quality criteria.
8. Failure, retry, and escalation policy.
9. Evidence/source requirements.
10. Logging and evaluation tests.

### 15.2 Generic multi-agent workflow

~~~mermaid
flowchart TB
    GOAL[Business goal] --> INTAKE[Intent and constraint extraction]
    INTAKE --> PLAN[Planner creates dependency graph]
    PLAN --> POLICY[Permission and policy gate]
    POLICY --> CTX[Context builder: tenant-scoped sources]
    CTX --> ROUTER[Capability router]
    ROUTER --> A1[Specialist agent A]
    ROUTER --> A2[Specialist agent B]
    ROUTER --> A3[Specialist agent C]
    A1 --> VALIDATE[Schema, evidence and policy validation]
    A2 --> VALIDATE
    A3 --> VALIDATE
    VALIDATE --> CRITIC[Quality critic / evaluator]
    CRITIC --> DECISION{Pass criteria?}
    DECISION -- No --> REVISE[Targeted revision or human review]
    REVISE --> VALIDATE
    DECISION -- Yes --> APPROVAL{External action?}
    APPROVAL -- Yes --> HUMAN[Authorised human approval]
    HUMAN --> ACTION[Permitted tool / connector action]
    APPROVAL -- No --> RESULT[Aggregate result]
    ACTION --> RESULT
    RESULT --> STORE[Persist outputs, sources and final state]
    STORE --> USER[Present result and limitations]
~~~

### 15.3 Agent output contract

A useful structured output should include:

- Result payload matching the expected schema.
- Summary of the decision or generated work.
- Evidence references for factual claims.
- Assumptions and unknowns.
- Validation result and any failed checks.
- Proposed next action, separated from action already performed.
- Approval requirement if the next step has external impact.
- Provider/model metadata where policy permits storing it.
- Error details that are safe to expose to operators but do not leak secrets.

### 15.4 Parallelism and dependencies

~~~mermaid
flowchart LR
    A[Create campaign brief] --> B[Audience research]
    A --> C[Brand messaging]
    A --> D[Channel plan]
    B --> E[Campaign synthesis]
    C --> E
    D --> E
    E --> F[Copy and creative generation]
    F --> G[QA and approval]
    G --> H[Publish / schedule]
    H --> I[Measure]
~~~

Independent research tasks can run in parallel. Synthesis must wait for required inputs. Publishing must wait for QA and required approvals. Measurement must wait for available source data and the appropriate reporting window.

### 15.5 Retry and failure handling

~~~mermaid
flowchart TD
    A[Step begins] --> B[Execute with timeout and idempotency key]
    B --> C{Result}
    C -- Success --> D[Validate output and persist]
    C -- Rate limited / transient --> E[Backoff within retry budget]
    E --> F{Attempts remain?}
    F -- Yes --> B
    F -- No --> G[Mark failed and surface operator action]
    C -- Invalid output --> H[One bounded repair attempt or human review]
    H --> I{Valid now?}
    I -- Yes --> D
    I -- No --> G
    C -- Permission / policy denied --> J[Stop; do not retry as a workaround]
    C -- Unknown external outcome --> K[Reconcile external state before retry]
~~~

Never retry a non-idempotent external action blindly after a timeout. First determine whether the external platform accepted the action.

## 16. Connector and AI-provider catalogue

This is a catalogue of connector categories referenced by the project context and existing documentation. Actual availability depends on implementation, credentials, account permissions, provider policy, and deployment configuration.

### 16.1 AI model providers

| Provider category | Typical use | Requirements / caveats |
|---|---|---|
| OpenAI | Text reasoning, structured output, summarisation, content generation | API key, permitted model, quotas, and configured model name |
| Anthropic / Claude | Text reasoning, writing and analysis | API key, model availability, quotas and configured adapter |
| Google / Gemini | Alternative model routing where implemented | Credentials and a working provider adapter |
| xAI / Grok | Alternative model routing where implemented | Credentials and a working provider adapter |
| OpenRouter | Multi-model gateway where configured | Gateway key, allowed model identifier, provider limits and fallback policy |
| Image provider | Image generation where configured | Separate image capability and model settings; do not assume text model can generate images |
| Video provider | Video generation where configured | Provider-specific API, asynchronous job status and media handling |

Only display providers and models that the running backend actually supports. Environment defaults should remain defaults; if manual model entry is supported, validate it server-side and do not expose secrets.

### 16.2 External business connectors

| Connector / category | Intended workflows | Configuration and verification |
|---|---|---|
| Meta / Facebook / Instagram APIs | Social publishing, account management and available insights | App credentials, OAuth redirect, scopes, account/page permissions and API review where required |
| LinkedIn API | Professional social publishing and available organisation/member actions | Client credentials, approved scopes, account permissions and product access |
| WhatsApp Cloud API | Support or approved business messaging | Business/account setup, access token, phone-number ID, webhook verification and message-policy compliance |
| Telegram Bot API | Bot-based notifications or conversations | Bot token, webhook/polling configuration and chat permissions |
| Gmail API | Inbox reading and email workflow where implemented | OAuth client, consent/scopes, refresh-token handling and mailbox permissions |
| Google Calendar API | Meeting availability, scheduling and event management | OAuth scopes, timezone handling and attendee permissions |
| SMTP | Outbound email where configured | Host, port, TLS mode, username, password/secret and sender policy |
| SendGrid / Mailgun | Email delivery and inbound event/webhook workflows | API credentials, verified domain, webhook signature validation and event mapping |
| Apify | Data collection or research tasks using approved actors | API token, actor allowlist, usage limits, cost controls and source-policy review |
| Apollo.io | B2B prospect research/enrichment | API credentials, permitted fields, plan limits and usage terms |
| Hunter.io | Business email discovery/verification where permitted | API key, quotas and lawful outreach process |
| Google Places | Business/location discovery | API key, enabled APIs, billing and usage restrictions |
| CRM connector category | Lead/opportunity synchronisation if implemented | OAuth/API token, field mapping, conflict rules and sync ownership |
| SEO / analytics connector category | Search and website performance reporting if implemented | Correct property/account access, date windows, scopes and sync status |
| Mapping / routing category | Real-estate field visits and location-aware scheduling if implemented | API key, usage limits, location permission and routing capability |

### 16.3 Connector lifecycle

~~~mermaid
flowchart TD
    A[Admin opens connector settings] --> B[Select provider and requested capabilities]
    B --> C[Start OAuth or enter secret securely]
    C --> D[Validate callback, scopes and credential]
    D --> E{Connection valid?}
    E -- No --> F[Show actionable error without exposing secret]
    E -- Yes --> G[Store encrypted credential reference and account metadata]
    G --> H[Run capability / health check]
    H --> I[Expose only supported actions]
    I --> J[Workflow requests an action]
    J --> K[Check tenant, user permission and approval]
    K --> L[Call provider with timeout and idempotency where supported]
    L --> M[Persist status, external ID and safe response metadata]
    M --> N[Monitor expiry, rate limits and failures]
~~~

### 16.4 Connector state semantics

Use distinct statuses such as **not configured**, **connected**, **permission missing**, **expired**, **rate limited**, **temporarily unavailable**, **failed**, and **unknown external outcome**. Do not report “connected” merely because credentials exist; perform an appropriate health or capability check. Never store API secrets in frontend code, repository files, or plain-text logs.

## 17. Security, tenancy, and approval boundaries

### Tenant isolation

- Derive tenant context from a verified authenticated identity, not from an untrusted client-supplied tenant ID alone.
- Scope every tenant-owned query, update, deletion, search, vector retrieval, export, and background job.
- Include tenant identity in queued task payloads and revalidate permissions when the worker executes.
- Prevent one tenant's prompts, files, tokens, execution logs, or provider usage from leaking into another tenant's context.
- Test cross-tenant access denial explicitly.

### Credentials and connector security

- Keep secrets server-side and encrypt them at rest using a managed secret store or an appropriate encryption scheme.
- Redact tokens, passwords, email content and sensitive personal data from logs.
- Validate OAuth state and callback parameters.
- Verify webhook signatures and timestamps where the provider supports them.
- Apply least-privilege scopes and support revocation/disconnection.
- Rotate credentials and handle expiry without silently failing workflows.

### Agent safety and approvals

- Treat model output and retrieved documents as untrusted.
- Use tool allowlists and typed arguments.
- Keep model planning separate from permission enforcement.
- Re-check authorisation at the moment of a consequential action.
- Require review where configured for public publishing, outbound messaging, spending, employment decisions, deletion, or sensitive record changes.
- Maintain an audit event for approval, rejection, execution, and external confirmation.
- Make cancellation and retries safe and observable.

## 18. Configuration and local development

### 18.1 Configuration principles

Use the actual .env.example and settings loader as the source of truth for required variable names. The names below are common examples from the documented architecture and may not all be consumed by the current checkout.

| Variable / setting | Purpose |
|---|---|
| DATABASE_URL | Database connection string, if used |
| REDIS_URL | Queue/cache endpoint, if Redis is used |
| SECRET_KEY | Application signing secret; use a strong unique value |
| OPENAI_API_KEY | OpenAI credential, if enabled |
| ANTHROPIC_API_KEY | Anthropic credential, if enabled |
| OPENROUTER_API_KEY | OpenRouter credential, if enabled |
| OPENROUTER_MODEL | Default OpenRouter model when configured |
| META_APP_ID / META_APP_SECRET | Meta OAuth credentials, if used |
| LINKEDIN_CLIENT_ID / LINKEDIN_CLIENT_SECRET | LinkedIn OAuth credentials, if used |
| NEXT_PUBLIC_API_URL | Frontend API base URL if the frontend uses this convention |
| SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD | SMTP configuration, if used |
| GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET | Google OAuth credentials, if used |
| APOLLO_API_KEY / HUNTER_API_KEY / APIFY_API_TOKEN | Optional research-source credentials, if enabled |

Never paste real secret values into README, issues, screenshots, commits, or frontend build variables.

### 18.2 Local setup outline

Exact commands depend on the checked-out repository files. Verify the package manager, Python version, migration tool, and required services before running the commands.

~~~bash
# 1. Clone the repository
git clone https://github.com/alienhousenetworks/octaos.git
cd octaos

# 2. Inspect the actual project structure and setup instructions
find . -maxdepth 3 -type f | sort | head -300

# 3. Create and activate a Python virtual environment if this checkout uses Python
python3 -m venv .venv
source .venv/bin/activate

# 4. Install backend dependencies only if requirements.txt exists
pip install -r requirements.txt

# 5. Configure local environment using the repository's example file
cp .env.example .env

# 6. Start the API only after confirming the actual entry point and required services
# Example for a FastAPI app whose entry point is app.main:app:
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
~~~

If the frontend uses Node.js, inspect its package.json and lockfile, then use the package manager indicated by that lockfile. Do not assume Next.js, Vite, or a specific package manager without checking the source. Likewise, run migrations and workers using the commands defined in the repository rather than guessed commands.

### 18.3 Local verification

- Check the API health endpoint and API documentation route configured by the application.
- Verify database connectivity and migration state.
- Verify worker/queue connectivity before starting asynchronous workflows.
- Run unit and integration tests using the repository's defined test commands.
- Test one low-risk workflow using mocked connectors before enabling external side effects.
- Confirm the UI shows missing configuration instead of pretending an integration is connected.
- Use test accounts and test recipients for outbound email, social publishing, or messaging.

## 19. Testing and production-readiness checklist

### Feature completeness

- [ ] Every visible UI action maps to a real API operation or is clearly disabled/not configured.
- [ ] Every advertised sub-feature has an implementation owner, route/service, and tests.
- [ ] Every agent has a documented input/output contract and bounded tools.
- [ ] Workflow diagrams match the real execution code.
- [ ] Each connector lists supported actions, scopes, limitations, and tested account types.
- [ ] Marketing types such as influencer, paid, email, SEO-led content, and social publishing are not presented as live unless their end-to-end paths are verified.
- [ ] No feature is merely a placeholder while the UI reports success.

### Reliability

- [ ] Async work is durable and survives API process restarts.
- [ ] Retries are bounded and safe for side-effecting operations.
- [ ] Timeouts, rate limits, cancellation and unknown external outcomes are handled.
- [ ] Execution status is consistent across API, worker, database and UI.
- [ ] Duplicate triggers and webhook replays are deduplicated.
- [ ] Failed steps expose actionable operator information without secrets.

### Security

- [ ] Tenant isolation is tested on APIs, jobs, files, retrieval and exports.
- [ ] Roles and permissions are enforced server-side.
- [ ] Secrets are encrypted and redacted.
- [ ] OAuth state and webhook signatures are verified.
- [ ] Consequential actions have approval policies.
- [ ] Prompt injection and untrusted retrieved content are covered by tests.
- [ ] Personal data retention and deletion policies are documented.

### Data and reporting

- [ ] Metrics include source, time range, timezone and freshness.
- [ ] Missing/unavailable data is not represented as zero.
- [ ] AI-generated claims are distinguishable from source-verified facts.
- [ ] External actions store external IDs and response status.
- [ ] Audit logs cover changes, approvals and external actions.

## 20. How to keep this README accurate

When adding or changing a feature, update the documentation in the same pull request:

1. Add the real directory/file paths from the repository tree.
2. Name the frontend page/components and backend route/service that implement the feature.
3. Document each sub-feature as implemented, partial, planned, or unavailable.
4. List each agent's real name, input, output, tools, and dependencies.
5. Update the workflow diagram to match the actual code path.
6. List connector capabilities, required scopes, setup, known limitations, and tests.
7. Record the relevant API endpoints and configuration keys from source.
8. Add failure paths, retry behaviour, approval gates, and audit events.
9. Link tests and document how to run them.
10. Remove or relabel claims that are not implemented.

### Suggested status labels

- **Implemented and tested:** verified in code and covered by relevant tests.
- **Implemented, not integration-tested:** code exists, but live provider behaviour has not been verified.
- **Partially implemented:** some UI or backend path exists, but the end-to-end workflow is incomplete.
- **Configured per deployment:** capability depends on credentials, account scopes, or tenant setup.
- **Planned / logical design:** documented target behaviour; not a claim of current implementation.
- **Unavailable:** the current deployment lacks the required implementation or connection.

### Documentation truth rule

A menu item is not proof of a working feature. An agent name is not proof that it is invoked. A configured API key is not proof that a connector works. A generated draft is not proof that an external action succeeded. Keep the README, UI, API, execution records, and tests aligned.

---

**Repository:** [alienhousenetworks/octaos](https://github.com/alienhousenetworks/octaos)  
**Primary purpose of this document:** product orientation, logical directory map, feature/sub-feature catalogue, workflow and agent diagrams, connector overview, and engineering guardrails.
