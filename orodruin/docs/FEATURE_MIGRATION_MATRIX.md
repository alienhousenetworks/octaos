# Feature Migration Matrix

| OctaOS / Orodruin Module | Source | Target Location in `orodruin` | Status |
| :--- | :--- | :--- | :--- |
| OSINT 41 Routers & Ingesters | `orodruin/backend/app/api/*` | `app/intelligence/osint/` + preserved `/api/*` | **Preserve** |
| MapLibre GL + Cesium + Actor Graph | `orodruin/frontend/src/*` | `frontend/src/maps/` & `frontend/src/intelligence/` | **Preserve & Wrap** |
| Multi-Tenancy, Auth, RBAC, Audit | `OctaOsautomation/app/core/` & `models/base.py` | `app/core/{tenancy,security,permissions}/` | **Migrate & Refactor** |
| Enterprise Web Research | `OctaOsautomation/app/services/research/` | `app/intelligence/company_research/` | **Migrate** |
| Lead Discovery & Qualification | `OctaOsautomation/app/api/v1/endpoints/leads.py` | `app/intelligence/lead_discovery/` + `app/business/crm/` | **Rebuild with Evidence** |
| Market & Competitor Strategy | New + Orodruin feeds | `app/intelligence/{market_trends,competitor_analysis,strategy}/` | **Build** |
| Local Inference & Workers | Replaces `llm_gateway.py` + `orodruin/llm.py` | `app/core/inference/` + `workers/` | **Rebuild (Local-First)** |
| Model Manager UI | `OctaOsautomation` settings/llm | — | **Retire (Removed)** |
| CRM, Sales, HR, Marketing, Support, Email, Finance | `OctaOsautomation/app/api/v1/endpoints/*` | `app/business/{crm,sales,hr,marketing,support,email,finance}/` | **Migrate** |
| Image/Video Content Studio | `OctaOsautomation/app/services/marketing/visual_creative/` | `app/generation/{text,image,video}/` | **Rebuild (Local Workers)** |
| LearningLoop & Telemetry | `OctaOsautomation/app/services/learning_loop.py` | `app/learning/` | **Migrate & Centralize** |
| Durable Workflows & Agents | `OctaOsautomation/app/services/agents/` | `app/agents/` + `app/workflows/` | **Migrate** |
