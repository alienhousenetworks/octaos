from fastapi import APIRouter
from app.api.v1.endpoints import (
    tenants, leads, marketing, llm, commands, dashboard, auth, support, hr,
    coordination, google, meta_oauth, linkedin_oauth, ceo, ceo_v5, system_admin, audit, usage, videos,
    enterprise, manager, federated_learning,
    deal_rooms, sales_manager, sales_os, automations, schedules,
    knowledge_connectors, mcp, rooms,
    hr_workflow, candidate_portal,
    data_collection,
    automation_nodes, automation_documents,
    hr_people, hr_workforce, hr_copilot, hr_enterprise, hr_compensation_read,
    sales_crm, sales_inbox, sales_platform, sales_inbound_webhooks,
    integrations, rbac, heygen, autonomous_work, buffer_oauth, workforce_events,
    research,
)

from app.api.v1.orchestrator import router as orchestrator_router
from app.api.v1.data_intelligence import router as data_intelligence_router

api_router = APIRouter()
api_router.include_router(rooms.router, prefix="/rooms", tags=["section-rooms"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(leads.router, prefix="/leads", tags=["leads"])
api_router.include_router(marketing.router, prefix="/marketing", tags=["marketing"])
api_router.include_router(llm.router, prefix="/llm", tags=["llm"])
api_router.include_router(commands.router, prefix="/commands", tags=["commands"])
api_router.include_router(autonomous_work.router, prefix="/autonomous-work", tags=["autonomous-work"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(support.router, prefix="/support", tags=["support"])
api_router.include_router(hr.router, prefix="/hr", tags=["hr"])
api_router.include_router(hr_people.router, prefix="/hr/people", tags=["hr-people"])
api_router.include_router(hr_workforce.router, prefix="/hr/workforce", tags=["hr-workforce"])
api_router.include_router(hr_enterprise.router, prefix="/hr/enterprise", tags=["hr-enterprise"])
api_router.include_router(hr_compensation_read.router, prefix="/hr/enterprise/compensation", tags=["hr-compensation-read"])
api_router.include_router(hr_copilot.router, prefix="/hr/copilot", tags=["hr-copilot"])
api_router.include_router(hr_workflow.router, prefix="/hr-workflows", tags=["hr-workflows"])
api_router.include_router(hr_workflow.router, prefix="/hr/workflow", tags=["hr-workflow"])
api_router.include_router(hr_workflow.router, prefix="/hr/workflows", tags=["hr-workflows-alias"])
api_router.include_router(candidate_portal.router, prefix="/public/candidate-portal", tags=["candidate-portal"])
api_router.include_router(coordination.router, prefix="/coordination", tags=["coordination"])
api_router.include_router(ceo.router, prefix="/ceo", tags=["ceo"])
api_router.include_router(ceo_v5.router, prefix="/ceo", tags=["ceo-v5"])
api_router.include_router(google.router, prefix="/google", tags=["google"])
api_router.include_router(meta_oauth.router, prefix="/meta", tags=["meta-oauth"])
api_router.include_router(linkedin_oauth.router, prefix="/linkedin", tags=["linkedin-oauth"])
api_router.include_router(system_admin.router, prefix="/system-admin", tags=["system-admin"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(usage.router, prefix="/usage", tags=["usage"])
api_router.include_router(videos.router, prefix="/videos", tags=["videos"])
api_router.include_router(enterprise.router, prefix="/enterprise", tags=["enterprise"])
api_router.include_router(manager.router, prefix="/manager", tags=["manager"])
api_router.include_router(federated_learning.router, prefix="/learning", tags=["federated-learning"])
api_router.include_router(orchestrator_router, prefix="/octa", tags=["octa-orchestrator"])
# The assistant calls /orchestrator/execute. The router already carries the
# /orchestrator prefix, so this mount is /api/v1/orchestrator/execute.
api_router.include_router(orchestrator_router, tags=["orchestrator"])
api_router.include_router(data_intelligence_router, tags=["orchestra-data-intelligence"])
api_router.include_router(research.router, prefix="/research", tags=["search-intelligence"])
api_router.include_router(deal_rooms.router, prefix="/deal-rooms", tags=["deal-rooms"])
api_router.include_router(sales_manager.router, prefix="/sales-manager", tags=["sales-manager"])
api_router.include_router(sales_os.router, prefix="/sales-os", tags=["sales-os"])
api_router.include_router(sales_crm.router, prefix="/sales-crm", tags=["sales-crm"])
api_router.include_router(sales_inbox.router, prefix="/sales-inbox", tags=["sales-inbox"])
api_router.include_router(sales_platform.router, prefix="/sales-os", tags=["sales-platform"])
# Dedicated real-estate and property-oriented field-sales routers are intentionally
# not registered in the industry-neutral product surface. Historical models and
# migrations remain for data compatibility until a separately tested migration.
api_router.include_router(sales_inbound_webhooks.router, prefix="/sales-os", tags=["sales-inbound-webhooks"])
api_router.include_router(automations.router, prefix="/automations", tags=["automations"])
api_router.include_router(schedules.router, prefix="/schedules", tags=["schedules"])
api_router.include_router(knowledge_connectors.router, prefix="/knowledge/connectors", tags=["knowledge-connectors"])
api_router.include_router(mcp.router, prefix="/mcp", tags=["mcp"])
api_router.include_router(data_collection.router, prefix="/data-collection", tags=["data-collection"])
api_router.include_router(automation_nodes.router, prefix="/automation-nodes", tags=["automation-nodes"])
api_router.include_router(automation_documents.router, prefix="/automation-documents", tags=["automation-documents"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
api_router.include_router(rbac.router, prefix="/rbac", tags=["rbac"])
api_router.include_router(heygen.router, prefix="/integrations/heygen", tags=["heygen-integration"])
api_router.include_router(buffer_oauth.router, prefix="/marketing/connectors/buffer", tags=["marketing-buffer"])

api_router.include_router(workforce_events.router, prefix="/workforce/events", tags=["workforce-events"])
