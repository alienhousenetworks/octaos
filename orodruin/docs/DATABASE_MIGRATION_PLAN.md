# Database Migration Plan

- **Engine:** PostgreSQL 16+ with PostGIS (geospatial) and `pgvector` (semantic retrieval). Local unit tests run against SQLite in-memory/file DB via SQLAlchemy 2.0.
- **Tenant Isolation:** Every business, intelligence, agent, generation, and learning table includes `tenant_id` (`ForeignKey("tenants.id")`, indexed).
- **Core Tables:** `tenants`, `users`, `audit_logs`, `api_credentials`.
- **OSINT Tables (Preserved):** `actors`, `events`, `fires`, `conflicts`, `vessels`, `disasters`, `sanctions`.
- **Business Intelligence Tables:** `company_profiles`, `intelligence_leads`, `market_signals`, `competitor_profiles`, `strategy_briefs` (all with structured `evidence_json` + `classification`: `RAW|MEASURED|DERIVED|EXTERNAL`).
- **Business OS Tables:** `crm_deals`, `sales_sequences`, `hr_candidates`, `marketing_campaigns`, `content_assets`, `support_tickets`, `email_messages`, `billing_subscriptions`, `workflow_definitions`, `workflow_runs`.
- **Learning Tables:** `decision_records`, `strategy_performance`, `negative_pattern_memory`.
