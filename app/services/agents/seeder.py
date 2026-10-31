from sqlalchemy.orm import Session
from app.models.flow_engine import (
    AgentDefinition,
    AgentVersion,
    PackageDefinition,
    PackageVersion,
    FlowDefinition,
    FlowVersion,
    Installation,
)
from app.models.teams import InstalledApp
import uuid

DEFAULT_INBUILT_AUTO_INSTALL_SLUGS = [
    "saas_outreach_system",
    "ecommerce_growth_autopilot",
    "medical_clinic_receptionist",
    "hr_recruiter_system",
    "creative_content_lab",
]


def seed_system_agents(db: Session):
    """Seeds the 6 system platform agents with version 1 definitions if not present."""
    system_agents = [
        {
            "name": "Sales AI",
            "slug": "sales_ai",
            "department": "sales",
            "role": "Outbound & Inbound Sales Specialist",
            "description": "Prospect qualification, automated research, lead scoring, and personalized outreach sequencing.",
            "avatar_icon": "TrendingUp",
            "provider": "openrouter",
            "model": "meta-llama/llama-3.3-70b-instruct",
            "system_prompt": (
                "You are Sales AI, the senior outbound & inbound sales intelligence specialist in OctaOS. Your goal is to discover, qualify, and deliver high-converting leads and pipeline growth.\n\n"
                "ROLE BOUNDARIES & COLLABORATION:\n"
                "- Focus strictly on prospecting, lead qualification, B2B account discovery, and sales outreach.\n"
                "- Do NOT generate marketing content (social posts, ad campaigns, blogs). If brand copy is needed, consult Marketing AI using agent.consult.\n\n"
                "HOW YOU WORK:\n"
                "1. STRICT 1-TURN CLARIFICATION BUDGET: Ask at most ONE clarifying question if the initial request is completely blank. If the user provides a geography, an industry, or says 'any', 'yes', 'proceed', or 'find them', DO NOT ask more questions! Assume sensible defaults (e.g. for Indian SMEs: manufacturing, healthcare clinics, retail, logistics, professional services) and execute autonomous discovery immediately.\n"
                "2. SUPPLIER INVERSION RULE (CRITICAL):\n"
                "   When searching for leads who NEED a service (e.g. website development, SEO, digital marketing, software, branding), NEVER search for or return companies that SELL that service (e.g., never return web design agencies or software shops as leads). "
                "Instead, target prospective CLIENT businesses (such as manufacturing companies, clinics/healthcare, local services, retail, logistics, legal/finance firms) that have weak or outdated web presence, OR public RFPs/tenders requesting website creation/revamp.\n"
                "3. DIRECTORY & TOOL EXCLUSION: Tender portals (e.g. IndiaTenders), scraping tools (e.g. Outscraper), and B2B databases (e.g. RevenueBase) are directories and tools, NOT prospective clients. Never present them as leads.\n"
                "4. When ready, autonomously execute lead generation and web research tools with queries targeting those client verticals. Never output raw code or JSON syntax to the user. Always deliver the full count requested (e.g. 10 leads) in clean, professional markdown format with company names, locations, specific website/opportunity gaps, and outreach pitch angles."
            ),
            "tools": [
                "web_search",
                "lead.create",
                "lead.update",
                "lead.score",
                "knowledge.search_sources",
                "knowledge.live_fetch",
                "app.connector_action",
                "agent.consult",
            ],
        },
        {
            "name": "Marketing AI",
            "slug": "marketing_ai",
            "department": "marketing",
            "role": "Content Strategist & Viral Copywriter",
            "description": "Brand storytelling, social media strategy, multi-channel copywriting, and campaign scheduling.",
            "avatar_icon": "Calendar",
            "provider": "openrouter",
            "model": "meta-llama/llama-3.3-70b-instruct",
            "system_prompt": (
                "You are Marketing AI, an elite brand strategist, viral copywriter, and creative director in OctaOS. You write compelling hooks, educational social posts, creative campaign concepts, and coordinate multi-platform growth campaigns.\n\n"
                "FIRST-LAYER INTENT UNDERSTANDING & WORKFLOW:\n"
                "- GREETINGS & CASUAL CHAT: When the user says hi, hello, thanks, or general pleasantries, respond conversationally, warmly, and concisely as their senior brand strategist. Ask what marketing goals or campaigns they want to tackle today. NEVER invoke `post.create` or run pipelines on greetings.\n"
                "- STRATEGIC CONSULTING & BRAINSTORMING: When the user asks for marketing ideas, content calendars, theme advice, or hashtag recommendations, share your strategic expertise directly in chat without invoking `post.create`.\n"
                "- CREATIVE EXECUTION & IDEA GRILLING (E.G. 'CREATE POST FOR DAILY ALIENHOUSE AND POST TO INSTA DIRECTLY'):\n"
                "  1. CAPABILITY & CONNECTION CHECK: Check if the platform (e.g. Instagram) is connected. Clearly state capability: yes, OctaOS can design the creative assets, copy, hashtags, and draft immediately, but live direct publishing requires an authorized connection. If not connected yet, share the one-click Buffer connection link (`/api/v1/buffer/connect`) or workspace integration link so the user can authorize it in one click.\n"
                "  2. GRILL THE IDEA & UNDERSTAND CREATION: If the prompt is brief or has missing details (e.g. 'daily alienhouse'), interrogate and grill the concept with 1-2 sharp, provocative creative questions (e.g., today's drop vibe, specific apparel piece, video Reel vs. static visual spot, target frequency) while presenting an immediate ready-to-run creative draft!\n"
                "  3. DELIVER COMPLETE ASSETS: Provide the complete captivating caption, bold hook, targeted hashtags, and a photorealistic visual/video creative prompt. Present everything in beautifully structured markdown.\n"
                "  4. SAFETY & PERMISSION GATE: Always request explicit user approval/confirmation before publishing live. When invoke `post.create` is needed, invoke it cleanly with `publish_now: true` if direct publishing was requested, or `publish_now: false` for a draft.\n"
                "- EXTERNAL APP READ/WRITE & CONNECTOR CHECKS:\n"
                "  When the user asks to post to Instagram, Facebook, LinkedIn, Buffer, etc., `post.create` will check connector status. If `connector_required: true`, share the one-click Buffer link (`/api/v1/buffer/connect`) and invite the user to authorize or reply with credentials to publish immediately.\n\n"
                "ROLE BOUNDARIES & COLLABORATION:\n"
                "- Focus strictly on brand messaging, social media copy, campaign strategy, creative hooks, hashtags, and content scheduling.\n"
                "- Do NOT generate B2B sales leads, prospect accounts, or opportunity gap pitch angles. If sales lead generation or CRM pipeline building is needed, consult Sales AI using agent.consult.\n"
                "- When researching brands, trends, or cultural events (e.g. festivals, product launches), synthesize creative content and campaign plans, not sales lead lists."
            ),
            "tools": [
                "web_search",
                "post.create",
                "post.publish",
                "knowledge.search",
                "knowledge.search_sources",
                "knowledge.live_fetch",
                "app.connector_action",
                "agent.consult",
            ],
        },
        {
            "name": "Support AI",
            "slug": "support_ai",
            "department": "support",
            "role": "Customer Experience & Resolution Specialist",
            "description": "Ticket sentiment analysis, technical triage, instant verified troubleshooting, and escalation routing.",
            "avatar_icon": "MessageSquare",
            "provider": "openrouter",
            "model": "meta-llama/llama-3.3-70b-instruct",
            "system_prompt": (
                "You are Support AI, an empathetic, technically astute customer support specialist in OctaOS. You resolve client inquiries accurately based on verified company documentation.\n\n"
                "ROLE BOUNDARIES & COLLABORATION:\n"
                "- Focus strictly on customer inquiries, ticket troubleshooting, FAQs, and incident resolution.\n"
                "- Do NOT handle hiring, sales prospecting, or financial audits. If needed, consult the appropriate specialist using agent.consult."
            ),
            "tools": [
                "ticket.reply",
                "ticket.close",
                "knowledge.search",
                "knowledge.search_sources",
                "knowledge.live_fetch",
                "app.connector_action",
                "agent.consult",
            ],
        },
        {
            "name": "Finance AI",
            "slug": "finance_ai",
            "department": "finance",
            "role": "Financial Analyst & Risk Auditor",
            "description": "Invoice verification, transaction anomaly auditing, budget optimization, and burn-rate tracking.",
            "avatar_icon": "DollarSign",
            "provider": "openrouter",
            "model": "meta-llama/llama-3.3-70b-instruct",
            "system_prompt": (
                "You are Finance AI, an analytical corporate finance controller in OctaOS. You detect billing discrepancies, verify transaction legitimacy, and optimize resource allocation.\n\n"
                "ROLE BOUNDARIES & COLLABORATION:\n"
                "- Focus strictly on financial analysis, audits, invoicing, and budget tracking.\n"
                "- Consult other specialists via agent.consult when cross-departmental context is required."
            ),
            "tools": [
                "knowledge.search",
                "knowledge.search_sources",
                "knowledge.live_fetch",
                "app.connector_action",
                "webhook_post",
                "agent.consult",
            ],
        },
        {
            "name": "HR AI",
            "slug": "hr_ai",
            "department": "hr",
            "role": "Talent Acquisition & People Operations Agent",
            "description": "Candidate CV parsing, job requirement matching, applicant scorecarding, and onboarding coordination.",
            "avatar_icon": "Briefcase",
            "provider": "openrouter",
            "model": "meta-llama/llama-3.3-70b-instruct",
            "system_prompt": (
                "You are HR AI, a perceptive talent scout and human resources coordinator in OctaOS. You screen candidates against role criteria, craft fair scorecards, and streamline hiring.\n\n"
                "ROLE BOUNDARIES & COLLABORATION:\n"
                "- Focus strictly on hiring, candidate evaluation, job descriptions, and employee onboarding.\n"
                "- Consult other specialists via agent.consult when role specifications require departmental input."
            ),
            "tools": [
                "applicant.create",
                "applicant.score",
                "email.send",
                "knowledge.search_sources",
                "knowledge.live_fetch",
                "app.connector_action",
                "agent.consult",
            ],
        },
        {
            "name": "CEO AI",
            "slug": "ceo_ai",
            "department": "executive",
            "role": "Chief Executive Officer & Cross-Team Orchestrator",
            "description": "Autonomous business goal decomposition, inter-agent delegation, boardroom synthesis, and governance.",
            "avatar_icon": "Target",
            "provider": "openrouter",
            "model": "meta-llama/llama-3.3-70b-instruct",
            "system_prompt": (
                "You are CEO AI, the executive orchestrator of OctaOS. You synthesize insights across Sales, Marketing, HR, Finance, and Support to execute strategic initiatives.\n\n"
                "ROLE BOUNDARIES & COLLABORATION:\n"
                "- Orchestrate and delegate to specialist agents (Sales AI, Marketing AI, Support AI, Finance AI, HR AI) using agent.consult.\n"
                "- Provide high-level governance, executive decision-making, and strategic business synthesis."
            ),
            "tools": [
                "web_search",
                "knowledge.search",
                "knowledge.search_sources",
                "knowledge.live_fetch",
                "app.connector_action",
                "lead.score",
                "email.send",
                "agent.consult",
            ],
        },
    ]

    for item in system_agents:
        existing = db.query(AgentDefinition).filter_by(slug=item["slug"], tenant_id=None).first()
        if not existing:
            agent = AgentDefinition(
                name=item["name"],
                slug=item["slug"],
                department=item["department"],
                role=item["role"],
                description=item["description"],
                avatar_icon=item["avatar_icon"],
                is_system=True,
                tenant_id=None,
            )
            db.add(agent)
            db.flush()

            version = AgentVersion(
                agent_id=agent.id,
                version=1,
                system_prompt=item["system_prompt"],
                provider=item["provider"],
                model=item["model"],
                tool_grants=item["tools"],
                temperature=0.7,
                max_tokens=4096,
            )
            db.add(version)
        else:
            # Sync default system agent version to preferred Llama 70B if using older defaults
            latest_v = db.query(AgentVersion).filter_by(agent_id=existing.id).order_by(AgentVersion.version.desc()).first()
            if latest_v and latest_v.model in ["claude-sonnet-4-6", "gemini-2.5-flash", "gpt-4o", "claude-haiku-4-5-20251001"]:
                latest_v.provider = item["provider"]
                latest_v.model = item["model"]
            if latest_v:
                latest_v.system_prompt = item["system_prompt"]
                grants = list(latest_v.tool_grants or [])
                for t in item.get("tools", []):
                    if t not in grants:
                        grants.append(t)
                if item["slug"] == "sales_ai" and "email.send" in grants:
                    grants = [tool for tool in grants if tool != "email.send"]
                latest_v.tool_grants = grants
    db.commit()


SYSTEM_PACKAGES = [
        {
            "name": "SaaS Inbound & Outbound Growth System",
            "slug": "saas_outreach_system",
            "section": "sales",
            "category": "B2B Outbound",
            "complexity": "Advanced",
            "time_saved": "35h/week",
            "icon": "🚀",
            "desc": "End-to-end autonomous SDR flow: researches prospect, calculates lead score, drafts personalized outreach, requires approval, and dispatches email.",
            "features": ["Autonomous Web Research", "Algorithmic ICP Lead Scoring", "Manager Approval Gate", "Automated CRM Sync"],
            "config_schema": {
                "min_score": {"type": "integer", "default": 70, "label": "Minimum Qualification Score"},
                "outreach_tone": {"type": "string", "default": "concise", "label": "Outreach Tone (concise, consultative, bold)"},
            },
            "flow": [
                {
                    "id": "step_research",
                    "name": "Prospect Background Research",
                    "type": "agent",
                    "agent_slug": "sales_ai",
                    "input": {"company": "{{input.company}}", "query": "{{input.company}} market leadership"},
                },
                {
                    "id": "step_qualify",
                    "name": "Lead Qualification & Scoring",
                    "type": "agent",
                    "agent_slug": "sales_ai",
                    "input": {"lead_id": "{{input.lead_id}}", "research": "{{steps.step_research.output}}"},
                },
                {
                    "id": "step_condition",
                    "name": "Score Threshold Check",
                    "type": "condition",
                    "expression": "score >= 70",
                },
                {
                    "id": "step_approval",
                    "name": "Outreach Pitch Approval",
                    "type": "approval",
                    "risk_level": "medium",
                },
                {
                    "id": "step_email",
                    "name": "Deliver Email Outreach",
                    "type": "tool",
                    "tool": "email.send",
                    "input": {"to": "{{input.email}}", "subject": "Accelerating revenue with OctaOS"},
                },
                {
                    "id": "step_update_crm",
                    "name": "Update Sales CRM Record",
                    "type": "entity_action",
                    "action": "lead.update",
                    "input": {"status": "contacted", "score": 88},
                },
            ],
        },
        {
            "name": "E-Commerce Growth & Retention Autopilot",
            "slug": "ecommerce_growth_autopilot",
            "section": "marketing",
            "category": "E-Commerce",
            "complexity": "Intermediate",
            "time_saved": "25h/week",
            "icon": "🛍️",
            "desc": "SEO product desc generator, competitor price monitor, and abandoned cart SMS/email recovery sequences.",
            "features": ["SEO Product Writer", "Competitor Price Monitor", "Cart Recovery Sequencing"],
            "config_schema": {"store_url": {"type": "string", "label": "Online Store URL"}},
            "flow": [
                {
                    "id": "step_copy",
                    "name": "Generate SEO Product Narrative",
                    "type": "agent",
                    "agent_slug": "marketing_ai",
                    "input": {"product": "{{input.product}}"},
                },
                {
                    "id": "step_publish",
                    "name": "Publish Promotional Social Post",
                    "type": "entity_action",
                    "action": "post.create",
                    "input": {"platform": "instagram"},
                },
            ],
        },
        {
            "name": "Medical & Healthcare Patient Receptionist",
            "slug": "medical_clinic_receptionist",
            "section": "support",
            "category": "Healthcare",
            "complexity": "Intermediate",
            "time_saved": "18h/week",
            "icon": "🏥",
            "desc": "Automates patient scheduling, SMS check-in reminders, and insurance triage ticketing.",
            "features": ["Patient Calendar Sync", "SMS Confirmation Reminder", "Insurance Eligibility Triage"],
            "config_schema": {"clinic_name": {"type": "string", "label": "Clinic or Practice Name"}},
            "flow": [
                {
                    "id": "step_triage",
                    "name": "Patient Query Triage",
                    "type": "agent",
                    "agent_slug": "support_ai",
                    "input": {"inquiry": "{{input.inquiry}}"},
                },
                {
                    "id": "step_ticket",
                    "name": "Create Support Intake Ticket",
                    "type": "entity_action",
                    "action": "ticket.create",
                    "input": {"subject": "Patient Intake Request"},
                },
            ],
        },
        {
            "name": "Law Firm Contract & Clause Analyzer",
            "slug": "law_firm_document_automator",
            "section": "finance",
            "category": "LegalTech",
            "complexity": "Advanced",
            "time_saved": "30h/week",
            "icon": "⚖️",
            "desc": "Scans contracts for liability clauses, extracts renewal dates, and drafts legal response letters.",
            "features": ["Contract Clause Scanner", "Renewal Date Extractor", "Legal Correspondence Drafter"],
            "config_schema": {"jurisdiction": {"type": "string", "default": "US Delaware", "label": "Governing Jurisdiction"}},
            "flow": [
                {
                    "id": "step_scan",
                    "name": "Contract Liability Analysis",
                    "type": "agent",
                    "agent_slug": "finance_ai",
                    "input": {"contract_text": "{{input.contract_text}}"},
                },
                {
                    "id": "step_approval",
                    "name": "Partner Review Sign-off",
                    "type": "approval",
                    "risk_level": "high",
                },
            ],
        },
        {
            "name": "FinTech AML & Compliance Anomaly Detector",
            "slug": "fintech_compliance_suite",
            "section": "finance",
            "category": "Fintech",
            "complexity": "Advanced",
            "time_saved": "40h/week",
            "icon": "📊",
            "desc": "Automates quarterly audits, flags suspicious transactions, and prepares anti-money laundering compliance drafts.",
            "features": ["Quarterly Audit Automator", "AML Pattern Detection", "Transaction Anomaly Flagger"],
            "config_schema": {"alert_email": {"type": "string", "label": "Compliance Officer Email"}},
            "flow": [
                {
                    "id": "step_audit",
                    "name": "Transaction AML Audit",
                    "type": "agent",
                    "agent_slug": "finance_ai",
                    "input": {"transactions": "{{input.transactions}}"},
                },
            ],
        },
        {
            "name": "Creative Agency Content & Social Studio",
            "slug": "creative_content_lab",
            "section": "marketing",
            "category": "Creative Agency",
            "complexity": "Beginner",
            "time_saved": "15h/week",
            "icon": "🎨",
            "desc": "Converts raw transcripts into social media clips, generates blog outlines, and autogenerates viral hooks.",
            "features": ["Video-to-Text Snippet Generator", "SEO Blog Outline Writer", "Multi-Platform Scheduler"],
            "config_schema": {"brand_voice": {"type": "string", "default": "energetic", "label": "Brand Voice Style"}},
            "flow": [
                {
                    "id": "step_clips",
                    "name": "Extract Viral Social Clips",
                    "type": "agent",
                    "agent_slug": "marketing_ai",
                    "input": {"transcript": "{{input.transcript}}"},
                },
                {
                    "id": "step_post",
                    "name": "Stage Content Post",
                    "type": "entity_action",
                    "action": "post.create",
                    "input": {"platform": "linkedin"},
                },
            ],
        },
        {
            "name": "HR Recruiter & Talent Screening Pipeline",
            "slug": "hr_recruiter_system",
            "section": "hr",
            "category": "Human Resources",
            "complexity": "Intermediate",
            "time_saved": "28h/week",
            "icon": "👔",
            "desc": "Screens resumes against job specs, runs preliminary interactive screening tests, and coordinates onboarding calendars.",
            "features": ["CV Parser & Score Matcher", "Automated Interview Coordinator", "Onboarding Schedule Coordinator"],
            "config_schema": {"default_role": {"type": "string", "label": "Primary Job Title Target"}},
            "flow": [
                {
                    "id": "step_screen",
                    "name": "Candidate Spec Matching",
                    "type": "agent",
                    "agent_slug": "hr_ai",
                    "input": {"candidate_cv": "{{input.candidate_cv}}"},
                },
                {
                    "id": "step_applicant",
                    "name": "Register Candidate Profile",
                    "type": "entity_action",
                    "action": "applicant.create",
                    "input": {"name": "{{input.name}}", "email": "{{input.email}}"},
                },
            ],
        },
        {
            "name": "Restaurant Review & Dining Autopilot",
            "slug": "restaurant_growth_autopilot",
            "section": "marketing",
            "category": "Restaurant & Dining",
            "complexity": "Beginner",
            "time_saved": "20h/week",
            "icon": "🍽️",
            "desc": "Automates Google and Yelp review responses, generates daily chef specials for social media, and coordinates reservation inquiries.",
            "features": ["Yelp & Google Review Responder", "Daily Chef Specials Generator", "Reservation Request Triage", "Social Promotion Scheduler"],
            "config_schema": {
                "restaurant_name": {"type": "string", "default": "Bella Cucina Bistro", "label": "Restaurant Name"},
                "cuisine_style": {"type": "string", "default": "Modern Italian & Wine Bar", "label": "Cuisine / Dining Style"},
            },
            "sample_input": {
                "restaurant_name": "Bella Cucina Bistro",
                "review_text": "The handmade pappardelle was out of this world, though we waited 15 minutes for our table. Will definitely return!",
                "reviewer_name": "Elena R.",
                "rating": 4,
            },
            "flow": [
                {
                    "id": "step_review_analysis",
                    "name": "Analyze Review Sentiment & Highlights",
                    "type": "agent",
                    "agent_slug": "support_ai",
                    "input": {"review": "{{input.review_text}}", "reviewer": "{{input.reviewer_name}}"},
                },
                {
                    "id": "step_reply_draft",
                    "name": "Draft Warm Personalized Response",
                    "type": "agent",
                    "agent_slug": "marketing_ai",
                    "input": {"restaurant": "{{input.restaurant_name}}", "sentiment": "{{steps.step_review_analysis.output}}"},
                },
                {
                    "id": "step_promo_post",
                    "name": "Create Daily Chef Special Post",
                    "type": "agent",
                    "agent_slug": "marketing_ai",
                    "input": {"special": "Truffle Pappardelle & Chianti Pairing"},
                },
                {
                    "id": "step_publish",
                    "name": "Stage Instagram & Facebook Post",
                    "type": "entity_action",
                    "action": "post.create",
                    "input": {"platform": "instagram"},
                },
            ],
        },
        {
            "name": "Real Estate Buyer & Showing Concierge",
            "slug": "real_estate_showing_concierge",
            "section": "sales",
            "category": "Real Estate",
            "complexity": "Intermediate",
            "time_saved": "32h/week",
            "icon": "🏡",
            "desc": "Screens property buyer inquiries, scores pre-approval and purchasing timeline, schedules private showings, and syncs buyer preferences to CRM.",
            "features": ["Buyer Budget & Timeline Scoring", "Listing & Neighborhood Matcher", "Private Showing Scheduler", "Automated Broker Follow-up"],
            "config_schema": {
                "brokerage_name": {"type": "string", "default": "Apex Luxury Realty", "label": "Brokerage / Agency Name"},
                "service_area": {"type": "string", "default": "Downtown & West Suburbs", "label": "Primary Market Area"},
            },
            "sample_input": {
                "buyer_name": "Marcus Vance",
                "email": "marcus.vance@example.com",
                "budget": "$1,200,000",
                "target_property": "3-Bed Penthouse or Brownstone with Parking",
                "timeline": "Next 60 days",
            },
            "flow": [
                {
                    "id": "step_buyer_intake",
                    "name": "Qualify Buyer Criteria & Purchasing Power",
                    "type": "agent",
                    "agent_slug": "sales_ai",
                    "input": {"buyer": "{{input.buyer_name}}", "budget": "{{input.budget}}", "timeline": "{{input.timeline}}"},
                },
                {
                    "id": "step_score_lead",
                    "name": "Calculate High-Intent Readiness Score",
                    "type": "agent",
                    "agent_slug": "sales_ai",
                    "input": {"details": "{{steps.step_buyer_intake.output}}"},
                },
                {
                    "id": "step_approval",
                    "name": "Agent Review Showing Schedule",
                    "type": "approval",
                    "risk_level": "medium",
                },
                {
                    "id": "step_invite_email",
                    "name": "Send Private Showing Itinerary",
                    "type": "tool",
                    "tool": "email.send",
                    "input": {"to": "{{input.email}}", "subject": "Your Private Property Tour Itinerary"},
                },
                {
                    "id": "step_crm_sync",
                    "name": "Advance Buyer Stage in Sales CRM",
                    "type": "entity_action",
                    "action": "lead.update",
                    "input": {"status": "showing_scheduled", "score": 92},
                },
            ],
        },
        {
            "name": "EdTech & Student Admissions Concierge",
            "slug": "education_admissions_concierge",
            "section": "support",
            "category": "Education & EdTech",
            "complexity": "Intermediate",
            "time_saved": "25h/week",
            "icon": "🎓",
            "desc": "Answers prospective student questions from course knowledge bases, verifies prerequisite criteria, and schedules admissions interviews.",
            "features": ["Course & Syllabus Knowledge RAG", "Prerequisite Criteria Verification", "Admissions Interview Coordinator", "Automated Information Packet Dispatch"],
            "config_schema": {
                "institution_name": {"type": "string", "default": "Novus Academy of Applied AI", "label": "School or Institute Name"},
                "admissions_contact": {"type": "string", "default": "admissions@novusacademy.edu", "label": "Admissions Office Email"},
            },
            "sample_input": {
                "student_name": "Aria Montgomery",
                "email": "aria.m@example.com",
                "program_of_interest": "Accelerated AI Systems Engineering (Fall Cohort)",
                "question": "Can I transfer credits from my electrical engineering bachelor's degree?",
            },
            "flow": [
                {
                    "id": "step_faq_search",
                    "name": "Knowledge Search Program Catalog",
                    "type": "tool",
                    "tool": "knowledge.search",
                    "input": {"query": "{{input.program_of_interest}} credit transfer"},
                },
                {
                    "id": "step_advising_reply",
                    "name": "Draft Academic Advisor Response",
                    "type": "agent",
                    "agent_slug": "support_ai",
                    "input": {"student": "{{input.student_name}}", "question": "{{input.question}}", "docs": "{{steps.step_faq_search.output}}"},
                },
                {
                    "id": "step_applicant_record",
                    "name": "Register Prospective Student Profile",
                    "type": "entity_action",
                    "action": "applicant.create",
                    "input": {"name": "{{input.student_name}}", "email": "{{input.email}}"},
                },
                {
                    "id": "step_send_packet",
                    "name": "Deliver Admissions Welcome Packet",
                    "type": "tool",
                    "tool": "email.send",
                    "input": {"to": "{{input.email}}", "subject": "Admissions Information & Transfer Credit Guide"},
                },
            ],
        },
        {
            "name": "Gym & Fitness Membership Autopilot",
            "slug": "fitness_membership_autopilot",
            "section": "sales",
            "category": "Fitness & Wellness",
            "complexity": "Beginner",
            "time_saved": "18h/week",
            "icon": "💪",
            "desc": "Converts gym trial pass visitors into recurring members with automated check-in SMS, class recommendations, and trainer booking.",
            "features": ["3-Day Trial Pass Nurturing", "Personal Trainer Trial Booking", "Member Goal Assessment", "Membership Conversion Sequences"],
            "config_schema": {
                "gym_name": {"type": "string", "default": "Titan Athletic Club", "label": "Gym or Studio Name"},
                "trial_days": {"type": "integer", "default": 3, "label": "Free Trial Duration (Days)"},
            },
            "sample_input": {
                "lead_name": "Jordan Cole",
                "email": "jordan.cole@example.com",
                "fitness_goal": "Strength building & functional mobility",
                "preferred_time": "Weekday Mornings (7:00 AM)",
            },
            "flow": [
                {
                    "id": "step_goal_assessment",
                    "name": "Assess Fitness Profile & Training Match",
                    "type": "agent",
                    "agent_slug": "sales_ai",
                    "input": {"lead": "{{input.lead_name}}", "goal": "{{input.fitness_goal}}"},
                },
                {
                    "id": "step_schedule_pass",
                    "name": "Send VIP Pass & Trainer Schedule",
                    "type": "tool",
                    "tool": "email.send",
                    "input": {"to": "{{input.email}}", "subject": "Your VIP Trial Pass + Free Personal Training Session"},
                },
                {
                    "id": "step_lead_crm",
                    "name": "Register Trial Member in CRM",
                    "type": "entity_action",
                    "action": "lead.create",
                    "input": {"name": "{{input.lead_name}}", "email": "{{input.email}}"},
                },
            ],
        },
    ]


def get_system_packages_fallback(section: str | None = None):
    """Guaranteed in-memory fallback returning all curated packages with complete schema."""
    out = []
    for p in SYSTEM_PACKAGES:
        if section and section != "all" and p.get("section") != section:
            continue
        slug = p["slug"]
        is_core = slug in DEFAULT_INBUILT_AUTO_INSTALL_SLUGS
        out.append({
            "id": f"pkg_{slug}",
            "name": p["name"],
            "slug": slug,
            "section": p["section"],
            "category": p["category"],
            "desc": p["desc"],
            "icon": p["icon"],
            "complexity": p["complexity"],
            "time_saved": p["time_saved"],
            "is_system": True,
            "is_inbuilt": True,
            "is_core_default": is_core,
            "is_community": False,
            "is_installed": is_core,
            "installation_id": f"inst_{slug}" if is_core else None,
            "features": p.get("features", []),
            "config_schema": p.get("config_schema", {}),
            "eval_scores": {"task_success": 96.5, "tool_accuracy": 98.0, "avg_latency_s": 4.2, "avg_cost_usd": 0.024},
            "flow_steps": p.get("flow", []),
            "sample_input": p.get("sample_input", {}),
        })
    return out


def seed_system_packages(db: Session):
    """Seeds the real executable Marketplace Packages safely into DB."""
    try:
        from app.models.base import Base
        from app.models import flow_engine, teams  # noqa: F401
        Base.metadata.create_all(bind=db.get_bind())
    except Exception as e:
        print(f"Table verification in seed_system_packages: {e}")
        try:
            db.rollback()
        except Exception:
            pass

    try:
        for p in SYSTEM_PACKAGES:
            existing = db.query(PackageDefinition).filter_by(slug=p["slug"], tenant_id=None).first()
            if not existing:
                pack = PackageDefinition(
                    name=p["name"],
                    slug=p["slug"],
                    section=p["section"],
                    category=p["category"],
                    desc=p["desc"],
                    icon=p["icon"],
                    complexity=p["complexity"],
                    time_saved=p["time_saved"],
                    is_system=True,
                    is_community=False,
                    review_status="published",
                    tenant_id=None,
                )
                db.add(pack)
                db.flush()

                ver = PackageVersion(
                    package_id=pack.id,
                    version="1.0.0",
                    manifest={
                        "name": p["name"],
                        "section": p["section"],
                        "features": p["features"],
                        "flow": p["flow"],
                        "is_inbuilt": True,
                        "is_core_default": p["slug"] in DEFAULT_INBUILT_AUTO_INSTALL_SLUGS,
                        "sample_input": p.get("sample_input", {"company": "Acme Corp", "email": "alex@acme.com"}),
                    },
                    config_schema=p["config_schema"],
                    required_tools=["web_search", "email.send", "lead.update"],
                    required_scopes=["sales:write", "email:send"],
                    eval_scores={"task_success": 96.5, "tool_accuracy": 98.0, "avg_latency_s": 4.2, "avg_cost_usd": 0.024},
                )
                db.add(ver)
            else:
                existing.category = p["category"]
                existing.icon = p["icon"]
                existing.desc = p["desc"]
                latest_ver = db.query(PackageVersion).filter_by(package_id=existing.id).first()
                if latest_ver:
                    manifest_data = dict(latest_ver.manifest or {})
                    if "sample_input" not in manifest_data or not manifest_data["sample_input"]:
                        manifest_data["sample_input"] = p.get("sample_input", {})
                        latest_ver.manifest = manifest_data
                        db.add(latest_ver)
                else:
                    ver = PackageVersion(
                        package_id=existing.id,
                        version="1.0.0",
                        manifest={
                            "name": p["name"],
                            "section": p["section"],
                            "features": p["features"],
                            "flow": p["flow"],
                            "is_inbuilt": True,
                            "is_core_default": p["slug"] in DEFAULT_INBUILT_AUTO_INSTALL_SLUGS,
                            "sample_input": p.get("sample_input", {"company": "Acme Corp", "email": "alex@acme.com"}),
                        },
                        config_schema=p["config_schema"],
                        required_tools=["web_search", "email.send", "lead.update"],
                        required_scopes=["sales:write", "email:send"],
                        eval_scores={"task_success": 96.5, "tool_accuracy": 98.0, "avg_latency_s": 4.2, "avg_cost_usd": 0.024},
                    )
                    db.add(ver)
        db.commit()
    except Exception as e:
        print(f"Error seeding system packages: {e}")
        try:
            db.rollback()
        except Exception:
            pass


def ensure_default_installations(db: Session, tenant_id: str):
    """Auto-installs the curated core Inbuilt Packages for the given tenant workspace if not yet present."""
    if not tenant_id:
        return
    try:
        seed_system_packages(db)
        for slug in DEFAULT_INBUILT_AUTO_INSTALL_SLUGS:
            pack = db.query(PackageDefinition).filter_by(slug=slug, is_system=True).first()
            if not pack:
                continue
            existing_inst = db.query(Installation).filter_by(tenant_id=tenant_id, package_id=pack.id).first()
            if existing_inst:
                continue

            latest_ver = db.query(PackageVersion).filter_by(package_id=pack.id).order_by(PackageVersion.created_at.desc()).first()
            if not latest_ver:
                continue

            # 1. Backward-compatible InstalledApp record
            legacy = db.query(InstalledApp).filter_by(tenant_id=tenant_id, app_name=pack.name).first()
            if not legacy:
                legacy = InstalledApp(tenant_id=tenant_id, app_name=pack.name, config={})
                db.add(legacy)

            # 2. Dedicated FlowDefinition & FlowVersion
            flow_steps = latest_ver.manifest.get("flow", []) if latest_ver.manifest else []
            flow = FlowDefinition(
                tenant_id=tenant_id,
                name=f"{pack.name} Flow",
                slug=f"{pack.slug}_flow_{uuid.uuid4().hex[:6]}",
                section=pack.section,
                description=f"Auto-installed core workflow from {pack.name}.",
                package_id=pack.id,
            )
            db.add(flow)
            db.flush()

            flow_ver = FlowVersion(
                flow_id=flow.id,
                version=1,
                definition=flow_steps,
                trigger_type="event" if pack.section == "sales" else "manual",
                trigger_config={"event": "lead.created"} if pack.section == "sales" else {},
            )
            db.add(flow_ver)

            # 3. Installation record
            inst = Installation(
                tenant_id=tenant_id,
                package_id=pack.id,
                package_version_id=latest_ver.id,
                status="active",
                config={},
                created_resource_ids={"flow_id": flow.id},
            )
            db.add(inst)
        db.commit()
    except Exception as e:
        print(f"Error ensuring default installations: {e}")
        db.rollback()

