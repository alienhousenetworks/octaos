# Architecture Audit — OctaOS + Orodruin

## 1. Orodruin Foundation (`Dev-next-gen/orodruin`)
- **Backend:** FastAPI (`app/main.py`), SQLAlchemy 2.0 (`app/db.py`, `app/models.py`), PostgreSQL 16.
- **OSINT Routers (41 modules):** GDELT (`events`, `conflicts`), NASA FIRMS (`fires`), USGS (`quakes`), NASA EONET (`eonet`), GDACS (`disasters`), AISStream (`vessels`), OpenSky (`flights`), SGP4 (`satellites`), Public Cameras (`cameras`), Graph (`graph`), Hotspots, Alerts, Sanctions (`sanctions`), Cyber (`cyber`, `cyberthreat`, `breaches`, `geoip`), Infra (`infra`, `powerplants`), Finance/Markets/Prediction (`finance`, `markets`, `prediction`), Research (`research`), Weather/AirQuality (`weather`, `wxtiles`, `airquality`, `spaceweather`), Roads/Route/Traffic (`roads`, `route`, `traffic`), LiveTV (`tv`), AI Analyst (`chat.py`), Settings (`settings_api.py`).
- **Ingesters:** `app/ingest/` (`gdelt`, `firms`, `gdacs`, `aisstream`, `ofac`, `opensanctions`, `acled`).
- **Frontend:** React 18 + Vite + MapLibre GL + Cesium + `hls.js`.

## 2. OctaOS Source (`OctaOsautomation`)
- **Core Platform:** Multi-tenancy (`Tenant`, `User`, `APICredential`, `ProviderUsage`), JWT Auth, RBAC (`Action`, `Resource`, `ROLE_PERMISSIONS`), Audit logging.
- **Business Domains:** CRM & Leads, Sales OS & Deal Rooms, HR & Candidate Portal, Marketing & Campaign OS (Meta/LinkedIn/Buffer/Google OAuth), Support Chat & Outbound, Unified Email, Finance/Billing (Razorpay).
- **AI & Learning:** `OrchestratorAgent`, `ToolRegistry` (with SSRF protection), `EnterpriseWebResearchService`, `LearningLoop` (`DecisionRecord`, `StrategyPerformance`, `NegativePatternMemory`), durable workflows.
- **Gap Replaced by Local-First AI:** OctaOS's external paid LLM/Model Manager UI is replaced by a fixed, local-first `InferenceService` (`qwen3.5-4b`, `gemma-4-e4b`, `sd15`, `wan2.1-t2v-1.3b`).

## 3. Licensing Note
`orodruin` is licensed under **GNU AGPL v3.0** (`LICENSE`). Any network-hosted derivative must comply with AGPL-3.0 or obtain a commercial license.
