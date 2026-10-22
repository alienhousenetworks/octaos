"""Eighteen industry packs. Configuration only: labels, pipelines, qualification, and guardrails.

Domain modules that need their own transactions (unit holds, RFQ lines, regulated
decisions) are marked not_built. A pack must not be treated as a separate CRM.
"""
from __future__ import annotations

from typing import Any


def _plural(word: str) -> str:
    if word.endswith("y") and len(word) > 1 and word[-2] not in "aeiou":
        return word[:-1] + "ies"
    if word.endswith("s"):
        return word
    return word + "s"


import re


def _sanitize_stage_id(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return cleaned or "stage"


def _pack(
    pack_id: str,
    name: str,
    summary: str,
    *,
    lead: str,
    account: str,
    opportunity: str,
    objects: list[str],
    stages: list[str],
    qualification: list[str],
    prohibited: list[str],
    representative: bool = False,
    domain_note: str,
    pipeline_stages: list[dict[str, Any]] | None = None,
    fields: list[dict[str, Any]] | None = None,
    capabilities: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    resolved_pipeline_stages = pipeline_stages or [
        {
            "id": _sanitize_stage_id(stage),
            "label": stage,
            "color": "#75AFCB",
            "is_terminal": idx == len(stages) - 1,
            "terminal_outcome": "won" if any(w in stage.lower() for w in ("won", "onboard", "book")) else ("lost" if any(w in stage.lower() for w in ("lost", "cancel")) else None),
            "valid_transitions": [_sanitize_stage_id(stages[idx + 1])] if idx + 1 < len(stages) else [],
        }
        for idx, stage in enumerate(stages)
    ]
    return {
        "id": pack_id,
        "version": "1.0.0",
        "name": name,
        "summary": summary,
        "readiness": "representative" if representative else "configuration",
        "domain_status": "not_built",
        "domain_note": domain_note,
        "terminology": {
            "lead": lead,
            "leads": _plural(lead),
            "account": account,
            "accounts": _plural(account),
            "contact": "Contact",
            "contacts": "Contacts",
            "opportunity": opportunity,
            "opportunities": _plural(opportunity),
            "pipeline": "Pipeline",
        },
        "objects": objects,
        "stages": stages,
        "pipeline_stages": resolved_pipeline_stages,
        "fields": fields or [],
        "capabilities": capabilities or {},
        "qualification": qualification,
        "record_tabs": ["Overview", "Qualification", "Activity", "History"],
        "ai_guidance": {
            "allowed": [
                "Use only fields stored on the record or cited by a source.",
                "Say when a qualification answer is missing.",
                "Prepare a draft or a next step for a person to review.",
            ],
            "prohibited": prohibited,
        },
        "representative": representative,
    }


PACKS: dict[str, dict[str, Any]] = {
    item["id"]: item
    for item in [
        _pack(
            "banking",
            "Banking",
            "Prospects, product interests, and relationship coverage.",
            lead="Prospect",
            account="Relationship",
            opportunity="Product interest",
            objects=["Prospects", "Relationships", "Product interests", "KYC readiness"],
            stages=["Identified", "Eligibility review", "Documents", "Human review", "Handed to banker"],
            qualification=["Product of interest", "Relationship manager", "Eligibility evidence", "Consent to contact"],
            prohibited=["Do not mark KYC or eligibility as approved.", "Do not open an account."],
            domain_note="Eligibility and KYC stay with a designated reviewer. No banking decision engine is installed.",
        ),
        _pack(
            "credit_unions",
            "Credit unions",
            "Members, eligibility, and membership onboarding.",
            lead="Member prospect",
            account="Membership",
            opportunity="Membership application",
            objects=["Member prospects", "Memberships", "Share accounts", "Onboarding"],
            stages=["Inquiry", "Eligibility", "Application", "Review", "Onboarded"],
            qualification=["Membership eligibility", "Field of membership", "Requested share account"],
            prohibited=["Do not approve membership.", "Do not invent a share balance."],
            domain_note="Membership approval is not automated.",
        ),
        _pack(
            "insurance",
            "Insurance",
            "Coverage conversations and licensed-agent handoff.",
            lead="Prospect",
            account="Household or business",
            opportunity="Quote request",
            objects=["Prospects", "Products", "Coverage options", "Renewals"],
            stages=["Inquiry", "Needs", "Quote request", "Licensed handoff", "Renewal"],
            qualification=["Coverage sought", "Licensed agent", "Renewal date if already stored"],
            prohibited=["Do not bind coverage.", "Do not state that a policy is issued."],
            domain_note="Quotes are requests until a licensed workflow exists.",
        ),
        _pack(
            "mortgage",
            "Mortgage",
            "Loan inquiries and document readiness. Not a credit decision.",
            lead="Loan inquiry",
            account="Applicant",
            opportunity="Loan scenario",
            objects=["Loan inquiries", "Property", "Document checklist", "Preliminary scenario"],
            stages=["Inquiry", "Documents", "Preliminary scenario", "Human credit review"],
            qualification=["Loan purpose", "Property reference if stored", "Document checklist", "Consent"],
            prohibited=[
                "Do not call a scenario an approved loan.",
                "Do not make a credit decision.",
            ],
            domain_note="A sales user may collect an inquiry. Regulated credit decisions are not performed here.",
        ),
        _pack(
            "manufacturing",
            "Manufacturing",
            "RFQ, quantity, and delivery questions on the shared commercial record.",
            lead="RFQ",
            account="Buyer",
            opportunity="Quote",
            objects=["RFQs", "SKUs", "Quantities", "Delivery questions"],
            stages=["RFQ received", "Clarifying", "Quoted", "Negotiation", "Won or lost"],
            qualification=["Requested SKU or part", "Quantity", "Needed-by date", "Ship-to if stored"],
            prohibited=["Do not invent capacity, MOQ, or a unit price that is not on a price book."],
            representative=True,
            domain_note="BOM lines, MOQ tiers, and capacity checks are not a separate module yet. Use the shared quote path.",
        ),
        _pack(
            "saas",
            "High tech / SaaS",
            "The standard B2B motion: accounts, trials, seats, and renewals.",
            lead="Lead",
            account="Account",
            opportunity="Opportunity",
            objects=["Leads", "Accounts", "Trials", "Subscriptions", "Renewals"],
            stages=["New", "Qualified", "Discovery", "Security review", "Proposal", "Won or lost"],
            qualification=["Problem", "Seat or usage count if stored", "Security review owner", "Renewal or trial end if stored"],
            prohibited=["Do not invent ARR, seat counts, or a security approval."],
            representative=True,
            domain_note="Subscription billing is not installed. Seat and renewal fields are recorded only when a person stores them.",
        ),
        _pack(
            "transportation",
            "Transportation / logistics",
            "Lanes, freight requests, and rate conversations.",
            lead="Freight request",
            account="Shipper",
            opportunity="Rate quote",
            objects=["Lanes", "Shipments", "Equipment", "Rate quotes"],
            stages=["Request", "Lane review", "Rate quoted", "Tender", "Won or lost"],
            qualification=["Origin", "Destination", "Mode", "Ready date"],
            prohibited=["Do not invent a lane rate or available capacity."],
            domain_note="Routing and rating engines are not installed.",
        ),
        _pack(
            "business_services",
            "Business services",
            "Engagements, scope, and renewals.",
            lead="Inquiry",
            account="Client",
            opportunity="Engagement",
            objects=["Engagements", "Scope", "Retainers", "Renewals"],
            stages=["Inquiry", "Scoped", "Proposal", "Active", "Renewal"],
            qualification=["Service sought", "Start timing", "Commercial model if stored"],
            prohibited=["Do not invent utilization or a signed SOW."],
            domain_note="Time and materials billing is not installed.",
        ),
        _pack(
            "retail",
            "Retail / franchise",
            "Location and franchise inquiries.",
            lead="Franchise inquiry",
            account="Prospect operator",
            opportunity="Territory application",
            objects=["Locations", "Territories", "Fees", "Qualification"],
            stages=["Inquiry", "Territory check", "Qualification", "Disclosure", "Decision"],
            qualification=["Desired territory", "Operating experience", "Fee discussion status"],
            prohibited=["Do not award a territory or invent a fee."],
            domain_note="Territory exclusivity is not enforced by a booking lock.",
        ),
        _pack(
            "cpg",
            "CPG",
            "Retail accounts, distribution, and promotions.",
            lead="Retail lead",
            account="Retail account",
            opportunity="Distribution or promo",
            objects=["SKUs", "Distributors", "Trade terms", "Promotions"],
            stages=["Target", "Buyer meeting", "Terms", "Launch", "Replenishment"],
            qualification=["Banner or store", "Category", "Distributor if stored"],
            prohibited=["Do not invent velocity, distribution, or a trade rate."],
            domain_note="Trade-promotion accounting is not installed.",
        ),
        _pack(
            "pharma",
            "Pharma / life sciences",
            "Organizations, territories, and approved-material limits.",
            lead="Organization lead",
            account="Organization",
            opportunity="Engagement",
            objects=["Organizations", "Territories", "Approved materials", "Interactions"],
            stages=["Identified", "Access confirmed", "Visit", "Follow-up", "Closed"],
            qualification=["Organization", "Territory", "Approved material used", "Interaction logged"],
            prohibited=[
                "Do not make a medical or efficacy claim.",
                "Do not invent an interaction or an HCP profile.",
            ],
            domain_note="Approved-content control and interaction logging are policy text only. They are not a certified pharma module.",
        ),
        _pack(
            "telecom",
            "Telecom",
            "Locations, circuits, and feasibility questions.",
            lead="Service inquiry",
            account="Service location",
            opportunity="Package",
            objects=["Locations", "Circuits", "Bandwidth", "SLAs"],
            stages=["Inquiry", "Feasibility", "Design", "Quote", "Install"],
            qualification=["Service address", "Bandwidth requested", "Feasibility status if stored"],
            prohibited=["Do not mark a site feasible without a stored feasibility result."],
            domain_note="Network feasibility calculation is not installed.",
        ),
        _pack(
            "public_sector",
            "Public sector",
            "Agencies, solicitations, and bid schedules.",
            lead="Solicitation",
            account="Agency",
            opportunity="Bid",
            objects=["Agencies", "Solicitations", "Certifications", "Approvals"],
            stages=["Identified", "Eligible", "Drafting", "Submitted", "Awarded or lost"],
            qualification=["Solicitation id", "Due date", "Required certification", "Bid owner"],
            prohibited=["Do not guarantee an award.", "Do not suggest improper influence."],
            domain_note="Tender compliance checks are questions, not an automated eligibility engine.",
        ),
        _pack(
            "energy",
            "Energy / utilities",
            "Sites, usage assumptions, and proposals with stated assumptions.",
            lead="Site inquiry",
            account="Site",
            opportunity="Service proposal",
            objects=["Sites", "Consumption", "Tariffs", "Installation"],
            stages=["Inquiry", "Usage", "Feasibility", "Proposal", "Install"],
            qualification=["Site", "Stored usage or an explicit assumption", "Tariff input if stored"],
            prohibited=["Do not present a savings estimate as measured fact.", "Do not invent consumption."],
            domain_note="Tariff math and installation capacity are not installed.",
        ),
        _pack(
            "media",
            "Media / advertising",
            "Advertisers, flights, and inventory questions.",
            lead="Advertiser lead",
            account="Advertiser",
            opportunity="Campaign flight",
            objects=["Advertisers", "Inventory", "Rate cards", "Flight dates"],
            stages=["Brief", "Plan", "Reserved", "Live", "Reported"],
            qualification=["Flight dates", "Objective", "Rate card reference if stored"],
            prohibited=["Do not invent impressions, inventory, or a CPM."],
            domain_note="Ad-server delivery is not connected.",
        ),
        _pack(
            "real_estate",
            "Real estate",
            "Projects, units, visits, and channel partners on the shared record.",
            lead="Inquiry",
            account="Project",
            opportunity="Booking",
            objects=["Projects", "Units", "Site visits", "Channel partners"],
            stages=["Inquiry", "Site visit", "Hold requested", "Booking", "Cancelled"],
            pipeline_stages=[
                {"id": "inquiry", "label": "New Inquiry", "color": "#75AFCB", "valid_transitions": ["qualified", "site_visit", "cancelled"]},
                {"id": "qualified", "label": "Buyer Qualified", "color": "#A1AEF0", "valid_transitions": ["site_visit", "cancelled"]},
                {"id": "site_visit", "label": "Site Visit Scheduled", "color": "#D9AD68", "valid_transitions": ["hold_requested", "booking", "cancelled"]},
                {"id": "hold_requested", "label": "Hold Requested", "color": "#D9828B", "valid_transitions": ["booking", "site_visit", "cancelled"]},
                {"id": "booking", "label": "Confirmed Booking", "color": "#64B99A", "is_terminal": True, "terminal_outcome": "won"},
                {"id": "cancelled", "label": "Cancelled / Lost", "color": "#4B5563", "is_terminal": True, "terminal_outcome": "lost"},
            ],
            fields=[
                {"key": "project_id", "label": "Project / Property", "type": "string", "required": True},
                {"key": "property_type", "label": "Property Type", "type": "enum", "options": ["Apartment", "Penthouse", "Villa", "Commercial", "Plot"]},
                {"key": "unit_preference", "label": "Unit Config", "type": "string"},
                {"key": "budget_min", "label": "Budget Min", "type": "currency"},
                {"key": "budget_max", "label": "Budget Max", "type": "currency"},
                {"key": "purchase_purpose", "label": "Purpose", "type": "enum", "options": ["Self-Use", "Investment", "Rental Yield"]},
                {"key": "financing_status", "label": "Financing Status", "type": "enum", "options": ["Cash", "Pre-Approved Mortgage", "Loan Assistance Needed"]},
                {"key": "purchase_timeline", "label": "Timeline", "type": "enum", "options": ["Immediate", "30 Days", "60 Days", "90+ Days"]},
            ],
            capabilities={
                "inventory_catalog": {"id": "inventory_catalog", "name": "Property & Unit Catalog", "status": "AVAILABLE", "description": "Tenant-scoped projects, towers, units, and price lists."},
                "atomic_unit_reservation": {"id": "atomic_unit_reservation", "name": "Unit Hold & Concurrency Control", "status": "AVAILABLE", "description": "Transactional reservation with expiration timer and conflict prevention."},
                "site_visit_scheduler": {"id": "site_visit_scheduler", "name": "Site Visit & Tour Management", "status": "AVAILABLE", "description": "Showing calendar, agent escort assignment, and feedback logging."},
                "channel_partner_attribution": {"id": "channel_partner_attribution", "name": "Broker Attribution & Commissions", "status": "AVAILABLE", "description": "RERA partner attribution and commission agreement tracking."},
                "portal_webhooks": {"id": "portal_webhooks", "name": "Listing Portal Ingestion", "status": "AVAILABLE", "description": "Normalized webhook adapters for real estate portals and ad platforms."},
            },
            qualification=["Project", "Unit or configuration", "Visit status", "Channel partner if stored"],
            prohibited=[
                "Do not mark a unit held or booked unless that state is stored.",
                "Do not invent inventory.",
                "Do not confirm receipt of token deposit without payment evidence."
            ],
            representative=True,
            domain_note="Operates with tenant-scoped property catalog, atomic unit holds, and visit schedules.",
        ),
        _pack(
            "restaurant",
            "Restaurant / catering",
            "Events, party size, and booking questions.",
            lead="Event inquiry",
            account="Host",
            opportunity="Booking",
            objects=["Events", "Party size", "Menus", "Deposits"],
            stages=["Inquiry", "Menu", "Hold", "Deposit", "Booked"],
            qualification=["Date", "Party size", "Dietary notes if stored", "Deposit status if stored"],
            prohibited=["Do not confirm a booking or a deposit that is not stored.", "Do not invent venue capacity."],
            domain_note="Venue capacity and deposit capture are not installed.",
        ),
        _pack(
            "ecommerce",
            "B2B e-commerce",
            "Wholesale catalogs, carts, and purchase orders.",
            lead="Wholesale lead",
            account="Buyer account",
            opportunity="Purchase order",
            objects=["Catalogs", "Bulk tiers", "Purchase orders", "Credit terms"],
            stages=["Lead", "Catalog sent", "Cart", "PO", "Fulfilled"],
            qualification=["Catalog of interest", "Order quantity", "Payment terms if stored"],
            prohibited=["Do not invent stock, a tier price, or tax-exempt status."],
            domain_note="Cart and tax calculation are not installed.",
        ),
    ]
}

PACK_ORDER: list[str] = list(PACKS)

# Startup validation: guarantee every registered pack conforms to the manifest schema
from app.services.sales_os.industry_runtime.manifest import validate_manifest  # noqa: E402

for _pack_id, _pack_dict in PACKS.items():
    validate_manifest(_pack_dict)

