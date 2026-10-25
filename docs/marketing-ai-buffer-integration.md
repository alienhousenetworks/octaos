# OctaOS Marketing AI: Buffer connection and end-to-end publishing

## What this implementation adds

- Tenant-scoped Buffer OAuth 2.0 Authorization Code + PKCE.
- Short-lived encrypted OAuth state that carries the authenticated tenant/user identity through the callback; callback does not accept a tenant ID from user-controlled query parameters.
- Encrypted server-side access/refresh token storage using the existing OctaOS credential encryption helper.
- Single-use refresh-token rotation: the newly issued refresh token is persisted immediately.
- Optional BYOK API-key setup as a fallback, validated against Buffer before the connection is reported as active.
- Connected organization/channel discovery and platform-to-channel mapping.
- Campaign Studio platform selection covers all currently documented Buffer GraphQL API publishing services: Instagram, Threads, LinkedIn, X, Facebook, TikTok, Google Business Profile, Mastodon, YouTube, Pinterest, and Bluesky.
- Backend mapping and publishing boundaries validate requested platform names against the same API-supported set; unsupported services fail closed rather than being presented as publishable.
- Backend approval checks before a ContentPost can be sent to Buffer.
- Buffer queue integration in the existing scheduled-post worker for workspaces with a Buffer connection and channel mapping.
- Image/video assets are attached by public HTTPS URL. Buffer fetches assets from the URL when the post publishes; the URL must remain reachable until then.
- An integration settings page at `/settings/integrations`.

## Required Buffer app setup

Register a confidential OAuth client in Buffer API settings. Set the callback URL to the exact deployed URL:

```text
https://YOUR_API_HOST/api/v1/marketing/connectors/buffer/callback
```

Configure these server-only environment variables:

```dotenv
BUFFER_CLIENT_ID=
BUFFER_CLIENT_SECRET=
BUFFER_REDIRECT_URI=https://YOUR_API_HOST/api/v1/marketing/connectors/buffer/callback
FRONTEND_BASE_URL=https://YOUR_FRONTEND_HOST
```

The OAuth redirect URI must exactly match the URI registered with Buffer. Do not put the Buffer client secret in Next.js/public environment variables. Production must use HTTPS and a strong server SECRET_KEY / ENCRYPTION_KEY.

## User flow

1. User signs into OctaOS and opens `/settings/integrations`.
2. Select **Connect Buffer**. OctaOS creates PKCE verifier/challenge and encrypted state, then returns the user to Buffer consent.
3. Buffer redirects to the configured callback. OctaOS validates the state, verifies the user is still active in the same tenant, exchanges the code and encrypts the tokens.
4. OctaOS loads the Buffer organizations and connected channels.
5. Workspace admin maps OctaOS platforms to the intended Buffer channels.
6. Campaign agents create posts and media as drafts. The post must be approved in OctaOS before it can be submitted.
7. The future-post scheduler sends approved posts to Buffer with OctaOS's intended timestamp. Due-time posts without a future Buffer queue entry use the Buffer queue path. Buffer's post ID is saved to prevent the same OctaOS post being queued repeatedly.

## API routes

All routes below are mounted under `/api/v1/marketing/connectors/buffer`:

- `GET /connect` — authenticated, RBAC-protected OAuth start; returns an authorization URL.
- `GET /callback` — Buffer OAuth callback.
- `GET /status` — connection state without returning secrets.
- `GET /channels` — list connected organizations/channels and saved mappings.
- `POST /channels/map` — map one OctaOS platform to a verified Buffer channel.
- `POST /api-key` — optional API-key fallback; server validates it and encrypts it.
- `POST /publish/{post_id}` — manually queue a tenant-owned approved post.
- `DELETE /disconnect` — remove the workspace's Buffer credential.

## Buffer API platform coverage

The current Buffer GraphQL API publishing allowlist is: **Instagram, Threads, LinkedIn, X, Facebook, TikTok, Google Business Profile, Mastodon, YouTube, Pinterest, and Bluesky**. The Campaign Studio campaign channel picker and influencer creative platform selectors use these channel identifiers. The selected channel must still exist in the connected Buffer account and match the requested service.

Buffer's broader product UI supports additional destinations and workflows that are not necessarily available through its API. In particular, **Substack and Start Page must not be represented as API-publishable until Buffer adds programmatic post creation for them**. YouTube publishing format, Instagram Reels/Stories, TikTok, and other platform-specific capabilities remain subject to Buffer's current GraphQL input schema, connected account permissions, and network constraints. A platform being selectable is not a guarantee that every format is supported.

## Publishing and media boundaries

- The backend rejects unapproved posts, cross-tenant post IDs, unmapped Buffer channels, and channels whose service does not match the post platform.
- Buffer accepts media via public HTTPS URLs, not a raw upload in this integration. The URL must stay available until Buffer publishes it. Keep generated assets in durable public/object storage and do not use expiring preview URLs.
- Current adapter supports one image or one video asset per post. Multi-image carousels, platform-specific post metadata, reels/stories-specific options, and document posts require additional channel-aware adapters.
- A Buffer API acceptance means "queued by Buffer", not "published by the social network". The ten-minute status task reconciles delivery state by Buffer post ID; this is polling and may lag. Buffer analytics metrics are not pulled by this connector. Buffer documents metric access as limited to personal workflows/automations using a personal API key, so do not assume OAuth can provide those metrics.
- Buffer's GraphQL API, account scopes and platform-specific features can change. Run a real test against a tenant-owned Buffer account before enabling auto-scheduling in production.
- A request timeout can leave an ambiguous external result. Never blindly retry a timed-out create mutation; reconcile Buffer's post list first. The current minimal adapter does not claim exactly-once external delivery.

## Marketing workforce: target closed loop

1. **Business and product understanding** — website/product catalog, approved claims, pricing, differentiators, ICPs, existing customer questions and restrictions.
2. **Evidence-backed research** — web search and extraction, current events, competitor pages, keyword/search demand and source timestamps/URLs.
3. **Campaign strategy** — objective, audience, offer, message, funnel, channels, KPI definitions, budget and experiment plan.
4. **Specialist execution** — existing Campaign OS agents for strategy/copy/critique, plus image/video generation, localization, influencer concepting and platform-specific creative.
5. **Quality and policy gates** — fact-checking, brand voice, claim provenance, synthetic-person disclosure, asset technical checks, permissions and approvals.
6. **Distribution** — Buffer OAuth/channel map; approved content only; platform constraints validated before scheduling.
7. **Measurement** — Buffer/native insights, GA4, Search Console and CRM/commerce conversions with freshness and attribution metadata.
8. **Learning** — compare actual outcomes against objectives, preserve evidence and experiment results, recommend bounded changes.

The repository already has Campaign OS, brand knowledge, context radar, trend synthesis, media generation and analytics components. This connector closes part of the distribution gap; it does not by itself make all research, creative providers, native insights, revenue attribution or optimization production-ready.

## Validation checklist

- Run `pytest -q tests/marketing/test_buffer_oauth.py`.
- Run Python compile checks for the new service/router and the modified publisher helper/worker.
- Run frontend lint/build.
- Run the existing Campaign OS orchestration regression suite.
- Apply no database migration for this connector: it reuses the existing tenant-scoped `APICredential` table.
- Validate with a real Buffer test account and verify scheduled post, image/video reachability, refresh-token rotation, disconnect, tenant isolation, rate limits and ambiguous timeouts.

## Platform source of truth

Check Buffer's live API capability documentation before expanding the allowlist: https://support.buffer.com/en-us/articles/what-is-buffers-api-GtIYIQilz5. The UI allowlist and backend validation should be updated together with tests whenever Buffer adds or changes publishing services. Analytics, comments, and engagement are separate capabilities and are not implied by publishing support.
