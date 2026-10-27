"""Eighteen Marketing Industry Packs.

Configuration and domain specialization: marketing funnels, content pillars,
statutory compliance guardrails, visual tokens, and industry event radars.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _pack(
    pack_id: str,
    name: str,
    summary: str,
    *,
    campaign: str,
    post: str,
    asset: str,
    offer: str,
    cta: str,
    audience: str,
    funnel_stages: List[Dict[str, Any]],
    content_pillars: List[Dict[str, Any]],
    prohibited_guarantees: List[str],
    taboo_words: List[str],
    required_disclosures: List[str],
    visual_tokens: Dict[str, Any],
    industry_calendar_events: List[Dict[str, Any]],
    representative: bool = False,
    domain_status: str = "configuration",
    domain_note: str = "",
    capabilities: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "id": pack_id,
        "version": "1.0.0",
        "name": name,
        "summary": summary,
        "readiness": "representative" if representative else "configuration",
        "representative": representative,
        "domain_status": domain_status,
        "domain_note": domain_note or f"Marketing configuration with tailored pillars, compliance rules, and visual tokens for {name}.",
        "terminology": {
            "campaign": campaign,
            "post": post,
            "asset": asset,
            "offer": offer,
            "cta": cta,
            "audience": audience,
        },
        "funnel_stages": funnel_stages,
        "content_pillars": content_pillars,
        "compliance_guardrails": {
            "prohibited_guarantees": prohibited_guarantees,
            "taboo_words": taboo_words,
            "required_disclosures": required_disclosures,
        },
        "visual_creative_tokens": visual_tokens,
        "industry_calendar_events": industry_calendar_events,
        "capabilities": capabilities or {
            "content_pillars": {"status": "AVAILABLE", "description": "Structured pillar hook generator"},
            "compliance_linter": {"status": "AVAILABLE", "description": "Deterministic regulatory guardrail scanner"},
            "visual_direction": {"status": "AVAILABLE", "description": "Industry-calibrated aesthetics and lighting tokens"},
            "moment_radar": {"status": "AVAILABLE", "description": "Industry calendar event recommendations"},
        },
    }


PACKS: Dict[str, Dict[str, Any]] = {
    # ── 1. Banking ────────────────────────────────────────────────────────────
    "banking": _pack(
        "banking",
        "Banking & Wealth",
        "Wealth management, commercial banking, security, and financial planning.",
        campaign="Financial Advisory Campaign",
        post="Wealth Insight",
        asset="Guide / Calculator",
        offer="Consultation / Rate Option",
        cta="Schedule Private Consultation",
        audience="HNIs, Business Owners & Retail Investors",
        funnel_stages=[
            {"id": "market_awareness", "label": "Macro & Market Awareness", "channels": ["linkedin", "facebook"]},
            {"id": "financial_literacy", "label": "Financial Literacy & Guidance", "channels": ["linkedin", "x", "instagram"]},
            {"id": "product_spotlight", "label": "Product & Rate Showcase", "channels": ["linkedin", "facebook"]},
            {"id": "trust_security", "label": "Security & Fraud Defense", "channels": ["linkedin", "facebook"]},
            {"id": "advisor_booking", "label": "Private Advisor Booking", "channels": ["linkedin"]},
        ],
        content_pillars=[
            {
                "id": "wealth_preservation",
                "label": "Wealth Management & Tax Efficiency",
                "description": "Strategies for capital preservation and multi-generational wealth.",
                "hooks": ["Why high-net-worth portfolios are shifting toward private credit this quarter.", "The 3 tax-efficiency blindspots family offices overlook."],
            },
            {
                "id": "treasury_cash_management",
                "label": "Commercial Treasury & Cash Flow",
                "description": "Optimizing working capital and liquidity for mid-market CFOs.",
                "hooks": ["How mid-market CFOs are earning 4.8% on idle cash without sacrificing liquidity.", "Managing cross-border FX exposure in volatile quarters."],
            },
            {
                "id": "cybersecurity_trust",
                "label": "Institutional Security & Fraud Defense",
                "description": "Defending business accounts against executive impersonation and wire fraud.",
                "hooks": ["The wire fraud vector targeting finance teams right now.", "How multi-factor token governance prevents unauthorized sweeps."],
            },
            {
                "id": "first_time_homebuyer",
                "label": "Mortgage & Home Lending Literacy",
                "description": "Educating buyers on amortizations, fixed vs. floating spreads, and equity build.",
                "hooks": ["Fixed vs adjustable: which mortgage strategy saves $42k over 7 years?", "The 5 document hurdles that delay home loan pre-approval."],
            },
            {
                "id": "business_expansion",
                "label": "Capex & Credit Facilities",
                "description": "Financing equipment, fleet acquisition, and commercial real estate lines.",
                "hooks": ["Structuring asset-backed equipment loans to preserve debt covenants.", "When to tap a revolving credit line vs term facility."],
            },
        ],
        prohibited_guarantees=[
            r"(?i)\bguarantee(d)?\b.*?\b(returns?|profits?|yield|interest|apy)",
            r"(?i)\brisk-free\b",
            r"(?i)\bno\s+loss\b",
            r"(?i)\bdouble\s+your\s+deposit\b",
        ],
        taboo_words=["get rich", "sure thing", "risk free", "zero downside", "foolproof investment"],
        required_disclosures=[
            "Member FDIC / Equivalent Banking Regulatory Authority.",
            "Investment products are not insured, may lose value, and carry no bank guarantee.",
            "All loans subject to credit underwriting and approval.",
        ],
        visual_tokens={
            "aesthetic": "Sophisticated financial editorial, polished corporate offices, clean architectural glass",
            "lighting": "Natural daylight, crisp executive interior lighting, subtle premium contrast",
            "color_palette": ["#0F2537", "#1E4B6E", "#C5A059", "#F4F6F9"],
            "camera_framing": "Medium executive shots, modern conference rooms, sleek tablet interface screens",
            "motion_pace": "Measured, confident, smooth cinematic pans",
        },
        industry_calendar_events=[
            {"month": "January", "name": "Tax Planning & Q1 Portfolio Rebalance Season", "hook": "Are your capital gains allocations optimized for the new fiscal year?"},
            {"month": "April", "name": "Financial Literacy Month", "hook": "Demystifying compound interest and credit health."},
            {"month": "October", "name": "National Cybersecurity Awareness Month", "hook": "Protecting enterprise accounts from executive impersonation."},
        ],
    ),

    # ── 2. Credit Unions ──────────────────────────────────────────────────────
    "credit_unions": _pack(
        "credit_unions",
        "Credit Unions & Cooperatives",
        "Member-owned financial cooperative campaigns, community impact, and low-fee auto/home loans.",
        campaign="Member Empowerment Campaign",
        post="Member Story / Financial Tip",
        asset="Member Benefit Guide",
        offer="Rate Advantage / Bonus",
        cta="Join Member Field of Membership",
        audience="Local Community, Teachers, Healthcare Workers, Members",
        funnel_stages=[
            {"id": "community_awareness", "label": "Community & Cooperative Mission", "channels": ["facebook", "instagram"]},
            {"id": "better_rates", "label": "Lower Rates & Member Returns", "channels": ["facebook", "instagram", "linkedin"]},
            {"id": "financial_wellness", "label": "Free Financial Coaching", "channels": ["instagram", "facebook"]},
            {"id": "membership_invite", "label": "Join Credit Union", "channels": ["facebook", "instagram"]},
        ],
        content_pillars=[
            {
                "id": "member_first_rates",
                "label": "Member Rate Difference",
                "description": "Comparing profit-driven megabanks with cooperative member dividends.",
                "hooks": ["Why our auto loan rates are 1.4% below commercial banks.", "Where do bank profits go? In our case, directly back to member dividends."],
            },
            {
                "id": "community_impact",
                "label": "Local Community & Non-Profit Support",
                "description": "Highlighting local branch grants, scholarships, and food drives.",
                "hooks": ["Over $120,000 returned to local schools this semester.", "Banking where your deposits stay in our hometown."],
            },
            {
                "id": "financial_coaching",
                "label": "Zero-Fee Financial Literacy",
                "description": "Debt consolidation, emergency savings ladders, and credit score building.",
                "hooks": ["3 steps our members use to boost their credit score by 45 points in 90 days.", "Consolidating high-rate credit cards into one low-interest member loan."],
            },
        ],
        prohibited_guarantees=[
            r"(?i)\bguaranteed\s+(dividend|approval|loan)",
            r"(?i)\beveryone\s+is\s+approved\b",
        ],
        taboo_words=["bank", "profit-maximizing", "guaranteed credit", "no check approval"],
        required_disclosures=[
            "Federally insured by NCUA or provincial cooperative regulator.",
            "Equal Housing Opportunity Lender.",
            "Membership eligibility required.",
        ],
        visual_tokens={
            "aesthetic": "Warm community lifestyle, authentic branch staff, friendly family moments",
            "lighting": "Warm golden sunlight, bright and welcoming interiors",
            "color_palette": ["#1A535C", "#4ECDC4", "#F7FFF7", "#FFE66D"],
            "camera_framing": "Eye-level human portraits, community gathering scenes, handshake moments",
            "motion_pace": "Warm, relatable, cheerful pacing",
        },
        industry_calendar_events=[
            {"month": "October", "name": "International Credit Union Day", "hook": "Celebrating people-over-profit banking and community ownership."},
            {"month": "November", "name": "Holiday Savings Club Campaign", "hook": "Start your holiday savings stash early without debt stress."},
        ],
    ),

    # ── 3. Insurance ──────────────────────────────────────────────────────────
    "insurance": _pack(
        "insurance",
        "Insurance & Risk Coverage",
        "Commercial liability, property & casualty, health, and life insurance advisory.",
        campaign="Coverage Advisory Campaign",
        post="Risk Mitigation Brief",
        asset="Policy Comparison Checklist",
        offer="Complimentary Risk Audit",
        cta="Request Policy Review with Licensed Agent",
        audience="Commercial Business Owners & Family Heads",
        funnel_stages=[
            {"id": "risk_education", "label": "Unseen Risk Education", "channels": ["linkedin", "facebook"]},
            {"id": "scenario_walkthrough", "label": "Claim Scenario Analysis", "channels": ["linkedin", "facebook"]},
            {"id": "policy_comparison", "label": "Coverage Gap Comparison", "channels": ["linkedin"]},
            {"id": "agent_consultation", "label": "Licensed Agent Consultation", "channels": ["linkedin", "facebook"]},
        ],
        content_pillars=[
            {
                "id": "business_liability",
                "label": "Commercial Cyber & General Liability",
                "description": "Protecting mid-market enterprises from ransom demands, D&O suits, and slip-and-falls.",
                "hooks": ["The single clause that denies 73% of cyber insurance claims.", "Why standard commercial liability won't cover your subcontractor's error."],
            },
            {
                "id": "family_wealth_protection",
                "label": "Term Life & Living Benefits",
                "description": "Ensuring income replacement and mortgage payoff for young families.",
                "hooks": ["How a 30-year term policy locks in 20-something rates for your 40s.", "The living benefits rider most policyholders never know they have."],
            },
            {
                "id": "catastrophe_readiness",
                "label": "Property & Climate Resilience",
                "description": "Wildfire, flood, and storm hardening for commercial roofs and estates.",
                "hooks": ["How hail-rated roofing cuts commercial property premiums by 18%.", "Understanding replacement cost vs actual cash value after a storm."],
            },
        ],
        prohibited_guarantees=[
            r"(?i)\ball\s+claims\s+paid\b",
            r"(?i)\bguaranteed\s+(payout|coverage|claim\s+settlement)",
            r"(?i)\byou\s+are\s+fully\s+covered\b",
        ],
        taboo_words=["binds coverage automatically", "instant claim guarantee", "no deductible"],
        required_disclosures=[
            "Coverage cannot be bound or modified via social media or email without written binder.",
            "Policies underwritten by licensed carriers; terms, exclusions, and limits apply.",
            "License # displayed in states where required.",
        ],
        visual_tokens={
            "aesthetic": "Protective, dependable, cinematic documentary realism, peaceful family safety",
            "lighting": "Clean cinematic daylight, dramatic weather skies clearing to sunlight",
            "color_palette": ["#102A43", "#243B53", "#334E68", "#62B0E8"],
            "camera_framing": "Wide exterior architectural shots, protective family framing, modern enterprise servers",
            "motion_pace": "Steadied, reassuring, calm dissolves",
        },
        industry_calendar_events=[
            {"month": "May", "name": "Hurricane & Storm Preparedness Week", "hook": "Review your commercial windstorm and flood deductibles before peak season."},
            {"month": "September", "name": "Life Insurance Awareness Month", "hook": "Calculating your real income-replacement multiplier."},
        ],
    ),

    # ── 4. Mortgage ───────────────────────────────────────────────────────────
    "mortgage": _pack(
        "mortgage",
        "Mortgage & Home Lending",
        "Home purchase financing, refinancing calculations, and borrower readiness.",
        campaign="Home Financing Campaign",
        post="Mortgage Strategy Note",
        asset="Borrowing Capacity Calculator",
        offer="Rate Lock Consultation",
        cta="Get Pre-Approval Readiness Assessment",
        audience="First-Time Buyers, Move-Up Buyers & Real Estate Investors",
        funnel_stages=[
            {"id": "affordability_readiness", "label": "Affordability & Credit Readiness", "channels": ["instagram", "facebook", "linkedin"]},
            {"id": "rate_scenario", "label": "Rate & Points Scenarios", "channels": ["facebook", "linkedin"]},
            {"id": "first_time_buyer", "label": "Down Payment & Grant Options", "channels": ["instagram", "facebook"]},
            {"id": "preapproval_drive", "label": "Pre-Approval Application", "channels": ["facebook", "linkedin"]},
        ],
        content_pillars=[
            {
                "id": "rate_buydown_strategy",
                "label": "Seller Concessions & 2-1 Buydowns",
                "description": "How to negotiate lower monthly payments using seller-paid rate buydowns.",
                "hooks": ["Why a 2-1 buydown saves $680/mo in year one compared to a price drop.", "Permanent rate discount points: math that proves when it breaks even."],
            },
            {
                "id": "credit_boost",
                "label": "Credit Optimization for Tier 1 Rates",
                "description": "Lowering debt-to-income and revolving balances 60 days before loan application.",
                "hooks": ["The $2,000 credit card mistake that bumps your mortgage rate by 0.375%.", "How paying down installment debt unfreezes $85,000 in purchase power."],
            },
            {
                "id": "investor_dscr",
                "label": "DSCR & Rental Portfolio Financing",
                "description": "Financing investment properties based on property lease revenue rather than personal W-2.",
                "hooks": ["How real estate investors scale to 6 units using DSCR loans with zero W-2 verification.", "What debt-service-coverage ratio of 1.25 actually requires."],
            },
        ],
        prohibited_guarantees=[
            r"(?i)\bguaranteed\s+(rate|loan|approval|closing)",
            r"(?i)\bzero\s+closing\s+costs\s+guaranteed\b",
            r"(?i)\bno\s+credit\s+check\s+mortgage\b",
        ],
        taboo_words=["100% approval", "instant mortgage", "guaranteed lock without app"],
        required_disclosures=[
            "Equal Housing Opportunity Lender. NMLS ID # required.",
            "All loans subject to underwriting approval and property appraisal.",
            "Sample APRs assume 740+ FICO and 20% down payment unless stated otherwise.",
        ],
        visual_tokens={
            "aesthetic": "Modern architectural residential homes, keys handover, bright sunlit kitchens",
            "lighting": "Golden hour exterior warmth, bright airy interior lighting",
            "color_palette": ["#1F3A52", "#3E6B89", "#D4AF37", "#FFFFFF"],
            "camera_framing": "Architectural exterior elevation, happy homeowner handover, clean financial charts",
            "motion_pace": "Warm, inspiring, aspirational cuts",
        },
        industry_calendar_events=[
            {"month": "March", "name": "Spring Homebuyer Season Kickoff", "hook": "Getting your pre-approval letter battle-ready before open houses begin."},
            {"month": "June", "name": "National Homeownership Month", "hook": "Building intergenerational equity through home ownership."},
        ],
    ),

    # ── 5. Manufacturing ──────────────────────────────────────────────────────
    "manufacturing": _pack(
        "manufacturing",
        "Industrial Manufacturing & OEM",
        "Precision engineering, contract manufacturing, supply chain resilience, and RFQ generation.",
        campaign="Industrial Capability Campaign",
        post="Engineering Case Study",
        asset="BOM / Tolerance Spec Sheet",
        offer="Complimentary DFM / RFQ Review",
        cta="Submit CAD for Engineering Review",
        audience="VP Engineering, Procurement Directors, Supply Chain Chiefs",
        funnel_stages=[
            {"id": "technical_authority", "label": "Engineering & Precision Tolerances", "channels": ["linkedin"]},
            {"id": "supply_chain_resilience", "label": "Onshore / Nearshore Reliability", "channels": ["linkedin"]},
            {"id": "dfm_cost_savings", "label": "Design for Manufacturing Cost Reduction", "channels": ["linkedin"]},
            {"id": "rfq_submission", "label": "Request for Quote (RFQ)", "channels": ["linkedin"]},
        ],
        content_pillars=[
            {
                "id": "dfm_optimization",
                "label": "Design for Manufacturability (DFM)",
                "description": "Reducing machining time and scrap rate through smart part geometries.",
                "hooks": ["How radius adjustments on 5-axis CNC reduced cycle time by 28%.", "3 injection molding wall thickness flaws that cause sink marks."],
            },
            {
                "id": "reshoring_lead_times",
                "label": "Nearshore Supply Chain Security",
                "description": "Cutting lead times from 16 weeks to 18 days with domestic cell production.",
                "hooks": ["The hidden landed cost of overseas freight in 2026.", "How cellular manufacturing delivers small-batch runs without tooling premiums."],
            },
            {
                "id": "iso_aerospace_certifications",
                "label": "ISO 9001 / AS9100 Quality Control",
                "description": "CMM inspection reports, material lot traceability, and zero-defect QA.",
                "hooks": ["Full 3D coordinate-measuring machine (CMM) verification down to +/- 0.0002 inches.", "Traceable mill certs: why defense contracts demand 100% lot tracking."],
            },
        ],
        prohibited_guarantees=[
            r"(?i)\bzero\s+lead\s+time\b",
            r"(?i)\bunlimited\s+factory\s+capacity\b",
            r"(?i)\bcheapest\s+in\s+the\s+world\b",
        ],
        taboo_words=["cheap parts", "instant tooling without review", "untested alloy"],
        required_disclosures=[
            "All lead times subject to material availability and CAD validation.",
            "Tolerances subject to engineering drawing specifications.",
        ],
        visual_tokens={
            "aesthetic": "Heavy precision engineering, CNC spark erosion, cleanroom assembly, robotics",
            "lighting": "Industrial studio lighting, cool fluorescent contrast with warm machining sparks",
            "color_palette": ["#202426", "#E63946", "#A8DADC", "#457B9D"],
            "camera_framing": "Macro close-ups of machined titanium, wide shots of automated factory floor",
            "motion_pace": "Crisp, mechanical, high-precision industrial rhythm",
        },
        industry_calendar_events=[
            {"month": "September", "name": "IMTS (International Manufacturing Technology Show)", "hook": "Next-gen 5-axis automation and lights-out machining."},
            {"month": "October", "name": "National Manufacturing Day", "hook": "Empowering modern precision machinists and advanced tooling."},
        ],
    ),

    # ── 6. B2B SaaS ───────────────────────────────────────────────────────────
    "saas": _pack(
        "saas",
        "High Tech & B2B SaaS",
        "Enterprise cloud software, automated workflows, developer velocity, and product-led growth.",
        campaign="Enterprise Velocity Campaign",
        post="Workflow Breakdown / Data Insight",
        asset="ROI Benchmark / Case Study",
        offer="Interactive Product Demo / Free Sandbox",
        cta="Start 14-Day Enterprise Trial",
        audience="VPs, Directors of Operations, Engineers, Enterprise Buyers",
        funnel_stages=[
            {"id": "problem_awareness", "label": "Workflow Friction & Broken Spreadsheets", "channels": ["linkedin", "x"]},
            {"id": "benchmark_data", "label": "Industry Benchmarks & ROI Proof", "channels": ["linkedin", "x"]},
            {"id": "product_breakdown", "label": "Feature Deep-Dives & Interactive Canvas", "channels": ["linkedin", "x", "instagram"]},
            {"id": "social_proof", "label": "Enterprise Customer Case Studies", "channels": ["linkedin"]},
            {"id": "trial_conversion", "label": "Free Sandbox & Trial Drive", "channels": ["linkedin", "x"]},
        ],
        content_pillars=[
            {
                "id": "workflow_friction",
                "label": "The Death of Disconnected Spreadsheets",
                "description": "Highlighting manual data re-entry, human lag, and operational blindspots.",
                "hooks": ["Your operations team is losing 14 hours a week copying data between 3 tabs.", "Why modern revenue teams are replacing 5 legacy point tools with one unified canvas."],
            },
            {
                "id": "roi_speed_benchmark",
                "label": "Time-to-Value & Engineering Velocity",
                "description": "Quantified speed gains, automation cycle times, and operational leverage.",
                "hooks": ["How Company X shipped 4x faster with 1/3 the back-office overhead.", "What happens when your deployment pipeline drops from 45 minutes to 90 seconds."],
            },
            {
                "id": "security_enterprise_readiness",
                "label": "SOC2, RBAC & Enterprise Governance",
                "description": "Reassuring CISOs on enterprise security, tenant isolation, and audit trails.",
                "hooks": ["The security checklist enterprise procurement teams verify before signing any SaaS agreement.", "Zero data leakage: why multi-tenant isolation matters in AI pipelines."],
            },
            {
                "id": "feature_spotlight",
                "label": "Product Teardown & Micro-Interactions",
                "description": "Visualizing sleek UI workflows, keyboard shortcuts, and smart automations.",
                "hooks": ["Under the hood: how our distributed engine processes 50,000 webhooks/sec.", "Watch how one slash command auto-resolves a complex reconciliation."],
            },
        ],
        prohibited_guarantees=[
            r"(?i)\b100%\s+uptime\s+guaranteed\b",
            r"(?i)\bunhackable\b",
            r"(?i)\bguaranteed\s+(10x|100x)\s+growth\b",
            r"(?i)\bzero\s+bugs\s+guaranteed\b",
        ],
        taboo_words=["unhackable", "100% bug free", "instant billionaire", "magic AI without rules"],
        required_disclosures=[
            "Customer results may vary based on deployment scale and integration depth.",
            "Certifications (SOC2 Type II / ISO 27001) verified on annual audit report.",
        ],
        visual_tokens={
            "aesthetic": "Ultra-sleek dark mode UI, glowing glassmorphism, 3D floating interface elements",
            "lighting": "Subtle neon cyan/purple edge illumination, sleek ambient monitor glow",
            "color_palette": ["#0B0F19", "#1E293B", "#38BDF8", "#818CF8"],
            "camera_framing": "Isometric 3D software cards, clean terminal typography, sleek cursor interactions",
            "motion_pace": "Snappy, fluid, tech-forward micro-transitions",
        },
        industry_calendar_events=[
            {"month": "September", "name": "SaaStr Annual & Dreamforce Window", "hook": "Scaling B2B go-to-market motions and net-retention strategies."},
            {"month": "November", "name": "AWS re:Invent & Q4 Budget Flush Season", "hook": "Consolidating software spend before end-of-fiscal-year budget resets."},
        ],
        representative=True,
    ),

    # ── 7. Transportation & Logistics ─────────────────────────────────────────
    "transportation": _pack(
        "transportation",
        "Freight, Fleet & Logistics",
        "Intermodal shipping, dry van, refrigerated freight, and supply chain visibility.",
        campaign="Freight Reliability Campaign",
        post="Lane / Capacity Intelligence",
        asset="Lane Rate Index / Transit Map",
        offer="Lane Capacity Tender",
        cta="Request Spot Quote or Dedicated Capacity",
        audience="Shippers, Logistics Directors, Supply Chain Coordinators",
        funnel_stages=[
            {"id": "market_index", "label": "National Lane Rate & Rejection Indices", "channels": ["linkedin"]},
            {"id": "on_time_performance", "label": "OTIF (On-Time In-Full) Performance", "channels": ["linkedin"]},
            {"id": "fleet_tracking", "label": "Real-Time Telematics & Tracking", "channels": ["linkedin"]},
            {"id": "lane_booking", "label": "Lane Quote & Tender", "channels": ["linkedin"]},
        ],
        content_pillars=[
            {
                "id": "tender_acceptance",
                "label": "99.2% Primary Tender Acceptance",
                "description": "Never stranding loads in spot market auctions during holiday surges.",
                "hooks": ["Why tender rejection rates jump 18% during harvest season — and how our contracted capacity shields you.", "The true cost of a missed appointment on refrigerated perishables."],
            },
            {
                "id": "telematics_visibility",
                "label": "Real-Time GPS & Temperature Telematics",
                "description": "Continuous geofenced tracking and temp-controlled sensor compliance.",
                "hooks": ["Eliminating blind spots: live telemetry every 15 minutes from dock to receiver.", "How automated EDI 214 updates eliminate 'where is my load?' calls."],
            },
        ],
        prohibited_guarantees=[
            r"(?i)\bzero\s+transit\s+delays\s+guaranteed\b",
            r"(?i)\bweather-proof\s+delivery\b",
        ],
        taboo_words=["zero delay guarantee", "instant cross-country in 12 hours"],
        required_disclosures=[
            "Transit times and lane rates subject to carrier availability, DOT hours of service, and weather.",
            "DOT & MC carrier operating authority compliant.",
        ],
        visual_tokens={
            "aesthetic": "Cinematic highway cinematography, modern fleet trucks, bustling intermodal ports",
            "lighting": "Dawn and twilight highway lighting, sleek illuminated digital cab telemetry",
            "color_palette": ["#111827", "#1E3A8A", "#F59E0B", "#F3F4F6"],
            "camera_framing": "Low-angle dynamic tracking shots of semi-trucks, overhead drone port views",
            "motion_pace": "Powerful, continuous, forward-moving momentum",
        },
        industry_calendar_events=[
            {"month": "October", "name": "Peak Shipping Season Surge (Pre-Holidays)", "hook": "Locking in contracted dry-van and reefer capacity before spot spikes."},
            {"month": "May", "name": "DOT Roadcheck Week", "hook": "Maintaining 100% safety audit compliance across fleet operations."},
        ],
    ),

    # ── 8. Service Company & Professional Services ───────────────────────────
    "business_services": _pack(
        "business_services",
        "Service Company & Professional Services",
        "Software engineering agencies, IT services, digital consultancies, retainers, and outsourced staff.",
        campaign="Service Solution & Case Study Campaign",
        post="Engineering / Agency Case Study",
        asset="Service Playbook / Solution Blueprint",
        offer="Scoping Workshop / Architecture Assessment",
        cta="Book 30-Minute Solution Discovery Call",
        audience="CTOs, VPs of Engineering, Product Leaders, CEOs, Operations Directors",
        funnel_stages=[
            {"id": "thought_leadership", "label": "Technical Architecture & Strategy Briefings", "channels": ["linkedin", "x"]},
            {"id": "client_transformation", "label": "Client Outcome & Transformation Case Studies", "channels": ["linkedin", "facebook"]},
            {"id": "scoping_workshop", "label": "Solution Architecture & Fixed-Scope Discovery", "channels": ["linkedin"]},
            {"id": "retainer_kickoff", "label": "Book Architecture & Discovery Call", "channels": ["linkedin"]},
        ],
        content_pillars=[
            {
                "id": "client_transformation",
                "label": "Client Outcomes & Architecture Breakdowns",
                "description": "Deconstructing measurable client transformations, cloud migrations, and product launches.",
                "hooks": [
                    "How we helped a fintech cut compute costs by 38% in 60 days.",
                    "Inside the rewrite: How a dedicated engineering squad scaled this marketplace to 1M daily requests.",
                ],
            },
            {
                "id": "service_capabilities",
                "label": "Technical Standards & Dedicated Squad Delivery",
                "description": "Why high-growth companies hire dedicated technical agencies over erratic contract hiring.",
                "hooks": [
                    "Why mid-market CTOs choose dedicated pods over vendor roulette.",
                    "Our 4-step framework for scoping fixed-price milestones with zero scope creep.",
                ],
            },
            {
                "id": "operational_roi",
                "label": "Operational Efficiency & Retainer ROI",
                "description": "Budget allocation, retainer models, and maximizing velocity per dollar.",
                "hooks": [
                    "Fixed-fee vs. Dedicated Squad: What actually saves engineering budget.",
                    "The hidden costs of offshore staffing and how to fix team velocity.",
                ],
            },
        ],
        prohibited_guarantees=[
            r"(?i)\bguaranteed\s+(delivery|10x\s+roi|zero\s+bug)",
            r"(?i)\bguaranteed\s+(legal\s+win|tax\s+refund)",
        ],
        taboo_words=["guaranteed zero bugs", "100% bug-free", "instant 10x roi", "guaranteed court victory"],
        required_disclosures=[
            "Past client outcomes do not guarantee identical project velocity or metrics.",
            "Scope, milestones, and deliverables are governed by formal Statement of Work (SOW).",
        ],
        visual_tokens={
            "aesthetic": "Modern tech studio, high-contrast engineering workspaces, clean terminal displays, minimal typography",
            "lighting": "Crisp architectural studio lighting with deep slate and cool accents",
            "color_palette": ["#0F172A", "#1E293B", "#38BDF8", "#F8FAFC"],
            "camera_framing": "Candid engineering architecture whiteboarding, focused developer pair-programming, clean workspace setups",
            "motion_pace": "Dynamic, focused, engineering-driven pacing",
        },
        industry_calendar_events=[
            {"month": "November", "name": "Annual Product Roadmap & Headcount Planning", "hook": "Stress-testing your 2027 fiscal engineering roadmap and vendor allocation."},
            {"month": "January", "name": "Q1 Project Kickoff & Tech Stack Audits", "hook": "Structuring vendor milestone agreements for predictable Q1 delivery."},
        ],
    ),

    # ── 9. Retail & Franchise ─────────────────────────────────────────────────
    "retail": _pack(
        "retail",
        "Retail & Franchise Systems",
        "Store expansion, multi-unit franchise development, localized retail campaigns, and seasonal foot-traffic.",
        campaign="Retail Footfall & Franchise Campaign",
        post="Store Announcement / Territory Drop",
        asset="Franchise Disclosure Summary / Lookbook",
        offer="Grand Opening Special / Territory Application",
        cta="Explore Franchise Opportunity or Visit Store",
        audience="Franchise Operators, Local Shoppers, Multi-Unit Investors",
        funnel_stages=[
            {"id": "brand_footprint", "label": "Brand Momentum & Unit Economics", "channels": ["instagram", "facebook", "linkedin"]},
            {"id": "franchise_territory", "label": "Available Territories & Expansion", "channels": ["linkedin", "facebook"]},
            {"id": "grand_opening", "label": "Grand Opening & VIP Events", "channels": ["instagram", "facebook", "tiktok"]},
            {"id": "store_traffic", "label": "In-Store Foot-Traffic Drives", "channels": ["instagram", "facebook"]},
        ],
        content_pillars=[
            {
                "id": "franchise_unit_economics",
                "label": "Proven Multi-Unit Economics",
                "description": "Showcasing system-wide sales momentum, territory exclusivity, and franchisee support.",
                "hooks": ["Why multi-unit operators are adding 3 locations in their second operating year.", "Average store ramp-up timeline: from lease signing to positive cash flow."],
            },
            {
                "id": "local_retail_buzz",
                "label": "Grand Opening & Store Experience",
                "description": "Creating lines around the block with localized VIP drops and community celebrations.",
                "hooks": ["Doors open this Saturday at 9 AM: first 100 shoppers receive our limited-edition tote.", "See inside our newest flagship location in Downtown."],
            },
        ],
        prohibited_guarantees=[
            r"(?i)\bguaranteed\s+(franchise\s+profit|roi|sales)",
            r"(?i)\bget-rich\s+store\b",
        ],
        taboo_words=["guaranteed millionaire", "risk-free franchise", "instant retail wealth"],
        required_disclosures=[
            "This is not an offer to sell a franchise. Offers made only by Franchise Disclosure Document (FDD).",
            "Individual store results vary based on location, operator diligence, and local demographics.",
        ],
        visual_tokens={
            "aesthetic": "Vibrant storefront architecture, energetic shopper lifestyle, clean branded merchandise",
            "lighting": "Bright retail spotlighting, crisp natural daylight, punchy color pops",
            "color_palette": ["#E11D48", "#FB7185", "#FFF1F2", "#18181B"],
            "camera_framing": "Street-level storefront reveal, energetic store interior panning, customer smile close-ups",
            "motion_pace": "Fast, upbeat, lively rhythm",
        },
        industry_calendar_events=[
            {"month": "November", "name": "Black Friday & Cyber Week Peak", "hook": "Maximizing multi-channel foot traffic and average basket size."},
            {"month": "May", "name": "National Franchise Expo Season", "hook": "Securing prime multi-unit territories in high-growth metro submarkets."},
        ],
    ),

    # ── 10. CPG (Consumer Packaged Goods) ─────────────────────────────────────
    "cpg": _pack(
        "cpg",
        "CPG & Fast-Moving Consumer Goods",
        "Retail shelf placement, SKU velocity, organic ingredients, and omnichannel consumer engagement.",
        campaign="Brand Awareness & Shelf Velocity",
        post="Product Spotlight / Recipe / Demo",
        asset="Store Locator / Digital Coupon",
        offer="Buy One Get One / In-Store Rebate",
        cta="Find in Your Local Grocery Aisle",
        audience="Grocery Shoppers, Retail Buyers, Category Managers",
        funnel_stages=[
            {"id": "craving_awareness", "label": "Sensory Product Craving & Unboxing", "channels": ["instagram", "tiktok", "facebook"]},
            {"id": "ingredient_cleanliness", "label": "Clean Label & Nutrition Transparency", "channels": ["instagram", "facebook"]},
            {"id": "retail_locator", "label": "Store Shelf Locator (Target/Whole Foods/Walmart)", "channels": ["instagram", "facebook"]},
            {"id": "repurchase_loyalty", "label": "Digital Coupon & Review Sharing", "channels": ["instagram", "tiktok"]},
        ],
        content_pillars=[
            {
                "id": "clean_ingredients",
                "label": "Zero Artificial Additives & Clean Label",
                "description": "Highlighting certified organic, non-GMO, and sustainably sourced ingredients.",
                "hooks": ["Only 5 real kitchen ingredients you can actually pronounce.", "Why we ditched seed oils and artificial preservatives completely."],
            },
            {
                "id": "shelf_takeover",
                "label": "Now Available at Major Retailers",
                "description": "Directing followers to specific aisles in national supermarket chains.",
                "hooks": ["We just landed in 1,200 Whole Foods locations nationwide! Check aisle 4.", "Head to your local Target this weekend for our exclusive summer flavor drop."],
            },
        ],
        prohibited_guarantees=[
            r"(?i)\bcures\s+(disease|ailment|illness)",
            r"(?i)\b100%\s+guaranteed\s+weight\s+loss\b",
        ],
        taboo_words=["miracle cure food", "burns 10lbs overnight", "disease reversing snack"],
        required_disclosures=[
            "These statements have not been evaluated by the FDA. This product is not intended to diagnose, treat, cure, or prevent any disease.",
            "Available at participating retail stores while supplies last.",
        ],
        visual_tokens={
            "aesthetic": "Delicious macro food cinematography, crisp condensation droplets, vibrant fresh ingredients",
            "lighting": "Bright warm sunshine, high-key studio rim light, vibrant saturated color",
            "color_palette": ["#16A34A", "#FACC15", "#FEF08A", "#FFFFFF"],
            "camera_framing": "Slow-motion food pours, macro texture close-ups, hand-held unboxing",
            "motion_pace": "Sensory, mouth-watering, punchy kinetic cuts",
        },
        industry_calendar_events=[
            {"month": "March", "name": "Natural Products Expo West", "hook": "Unveiling next-generation functional snacks and clean beverage innovations."},
            {"month": "July", "name": "Summer BBQ & Picnic Season Drive", "hook": "The ultimate pantry essential for outdoor gatherings and cookouts."},
        ],
    ),

    # ── 11. Pharma & Life Sciences ────────────────────────────────────────────
    "pharma": _pack(
        "pharma",
        "Pharma & Healthcare Life Sciences",
        "Clinical education, approved patient materials, fair balance indications, and disease state awareness.",
        campaign="Disease Awareness & Clinical Education",
        post="Clinical Insight / Patient Story",
        asset="Disease State Factsheet / Discussion Guide",
        offer="Educational Webinar / Doctor Conversation Guide",
        cta="Download Doctor Discussion Guide",
        audience="Physicians (HCPs), Patients, Caregivers, Clinical Researchers",
        funnel_stages=[
            {"id": "disease_awareness", "label": "Disease State & Symptom Literacy", "channels": ["linkedin", "facebook", "youtube"]},
            {"id": "clinical_evidence", "label": "Peer-Reviewed Clinical Data (HCP Only)", "channels": ["linkedin"]},
            {"id": "patient_journey", "label": "Compliant Patient Journey & Caregiver Voice", "channels": ["facebook", "youtube"]},
            {"id": "doctor_dialogue", "label": "Doctor Conversation Guide Download", "channels": ["facebook", "linkedin"]},
        ],
        content_pillars=[
            {
                "id": "unmet_medical_need",
                "label": "Understanding Chronic Symptom Progression",
                "description": "Educating patients and caregivers on early diagnostic markers and progression flags.",
                "hooks": ["Recognizing the early markers of progressive neuropathy before irreversible loss.", "Why 40% of patients delay discussing this symptom with their physician."],
            },
            {
                "id": "mechanism_of_action",
                "label": "Mechanism of Action & Clinical Pathway",
                "description": "Scientific visualization of receptor binding and cellular cascades for medical audiences.",
                "hooks": ["Targeting the IL-23 pathway: molecular insights from Phase 3 trials.", "How dual-inhibitor mechanisms differentiate in refractory cohorts."],
            },
        ],
        prohibited_guarantees=[
            r"(?i)\bguaranteed\s+(cure|recovery|remission)",
            r"(?i)\b100%\s+safe\s+with\s+no\s+side\s+effects\b",
            r"(?i)\bmiracle\s+(drug|treatment|cure)",
            r"(?i)\breplace(s)?\s+your\s+doctor\b",
        ],
        taboo_words=["miracle cure", "zero side effects", "100% cure rate", "instant recovery", "foolproof therapy"],
        required_disclosures=[
            "INDICATION & IMPORTANT SAFETY INFORMATION: Please see full Prescribing Information and Medication Guide.",
            "This information is educational and not medical advice. Consult your licensed healthcare provider.",
            "Report adverse events to FDA MedWatch or manufacturer safety hotline.",
        ],
        visual_tokens={
            "aesthetic": "Calm medical documentary, empathic human care, clinical laboratory teals and whites",
            "lighting": "Clean, soft natural daylight, respectful non-dramatic interior lighting",
            "color_palette": ["#0284C7", "#0EA5E9", "#F0F9FF", "#334155"],
            "camera_framing": "Gentle medium shots of doctor-patient conversation, clean scientific microscopy renderings",
            "motion_pace": "Reassuring, respectful, serene pacing",
        },
        industry_calendar_events=[
            {"month": "April", "name": "World Health Day & Parkinson's Awareness Month", "hook": "Expanding disease literacy and empowering early physician consultations."},
            {"month": "October", "name": "Breast Cancer Awareness Month", "hook": "Promoting annual clinical mammograms and genetic risk counseling."},
        ],
    ),

    # ── 12. Telecom ───────────────────────────────────────────────────────────
    "telecom": _pack(
        "telecom",
        "Telecommunications & Fiber Networks",
        "Dedicated fiber, low-latency 5G, enterprise SD-WAN, and unified voice solutions.",
        campaign="Connectivity & Speed Campaign",
        post="Network Latency / Coverage Update",
        asset="Bandwidth Sizing Matrix",
        offer="Free Fiber Site Survey / SLA Review",
        cta="Check Address Fiber Feasibility",
        audience="IT Directors, Network Engineers, Remote Enterprises",
        funnel_stages=[
            {"id": "bandwidth_bottleneck", "label": "Latency & Bottleneck Awareness", "channels": ["linkedin"]},
            {"id": "sla_reliability", "label": "99.999% SLA & Redundant Fiber", "channels": ["linkedin"]},
            {"id": "feasibility_check", "label": "Commercial Address Feasibility Check", "channels": ["linkedin", "facebook"]},
            {"id": "contract_upgrade", "label": "Quote & Fiber Turn-Up Consultation", "channels": ["linkedin"]},
        ],
        content_pillars=[
            {
                "id": "low_latency_fiber",
                "label": "Sub-5ms Latency & Symmetrical Up/Down",
                "description": "Eliminating VoIP jitter, video buffer delays, and cloud backup stalls.",
                "hooks": ["Why asymmetrical cable internet is throttling your team's cloud sync speeds.", "What true sub-5 millisecond ping means for real-time video and VoIP clarity."],
            },
            {
                "id": "sdwan_failover",
                "label": "Dual-Carrier Redundant Failover",
                "description": "Automatic 4G/5G failover keeping retail registers and branches online during fiber cuts.",
                "hooks": ["A backhoe severed the fiber line at 10 AM. Here is how automatic LTE failover prevented downtime.", "SLA guarantee: what 99.999% uptime requires in physical ring architecture."],
            },
        ],
        prohibited_guarantees=[
            r"(?i)\bzero\s+ping\s+latency\b",
            r"(?i)\bnever\s+goes\s+down\b",
        ],
        taboo_words=["infinite speed", "zero ping", "magic wireless"],
        required_disclosures=[
            "Actual speeds and fiber availability vary by physical service address.",
            "SLA terms apply to dedicated enterprise ethernet circuits.",
        ],
        visual_tokens={
            "aesthetic": "High-tech fiber optics, pulsing light conduits, modern server racks, sleek city skylines",
            "lighting": "Deep blue and neon cyan light trails, illuminated network LED indicators",
            "color_palette": ["#020617", "#06B6D4", "#3B82F6", "#F8FAFC"],
            "camera_framing": "Sweeping city nightscape with illuminated data lines, macro glowing fiber strands",
            "motion_pace": "Fast, kinetic, optical pulse speed",
        },
        industry_calendar_events=[
            {"month": "February", "name": "Mobile World Congress (MWC)", "hook": "Next-generation private 5G networks and enterprise wireless slicing."},
            {"month": "October", "name": "National Cyber Security Month (Network Perimeter)", "hook": "Locking down enterprise DNS and DDoS mitigation at the circuit level."},
        ],
    ),

    # ── 13. Public Sector ─────────────────────────────────────────────────────
    "public_sector": _pack(
        "public_sector",
        "Public Sector & Government Solutions",
        "Civic engagement, grant programs, municipal infrastructure, and citizen portal services.",
        campaign="Civic Engagement & Initiative Campaign",
        post="Public Service Announcement / Program Notice",
        asset="Citizen Guide / RFP Schedule",
        offer="Public Informational Hearing / Portal Sign-up",
        cta="Access Citizen Portal or Submit Feedback",
        audience="Citizens, Municipal Leaders, Contractors, Civic Advocates",
        funnel_stages=[
            {"id": "public_notice", "label": "Public Notice & Transparency", "channels": ["facebook", "x", "linkedin"]},
            {"id": "program_eligibility", "label": "Program Criteria & Eligibility", "channels": ["facebook", "instagram"]},
            {"id": "community_input", "label": "Public Comment & Town Hall", "channels": ["facebook", "x"]},
            {"id": "portal_adoption", "label": "Digital Service Adoption", "channels": ["facebook", "instagram"]},
        ],
        content_pillars=[
            {
                "id": "civic_transparency",
                "label": "Infrastructure Investment & Milestone Updates",
                "description": "Reporting progress on clean water, bridge repairs, and municipal transit expansion.",
                "hooks": ["Phase 2 of the Downtown Transit Revitalization begins Monday: here is what drivers need to know.", "Where local infrastructure tax dollars were allocated this fiscal year."],
            },
            {
                "id": "citizen_accessibility",
                "label": "Paperless Digital Citizen Services",
                "description": "Permit renewals, park bookings, and utility payments from your smartphone.",
                "hooks": ["Skip the city hall line: renew your residential parking permit in 90 seconds online.", "Applying for municipal small-business assistance grants."],
            },
        ],
        prohibited_guarantees=[
            r"(?i)\bguaranteed\s+(grant\s+award|permit\s+approval)",
            r"(?i)\bendorse(s)?\s+political\s+candidate\b",
        ],
        taboo_words=["guaranteed permit", "political bias", "skip government rules"],
        required_disclosures=[
            "Equal opportunity public agency. Services provided without regard to race, color, or origin.",
            "All grants, permits, and bids subject to formal administrative review and statutory criteria.",
        ],
        visual_tokens={
            "aesthetic": "Dignified civic spaces, community parks, municipal libraries, accessible modern interfaces",
            "lighting": "Natural daylight, open and transparent public atmosphere",
            "color_palette": ["#1E3A8A", "#1D4ED8", "#F3F4F6", "#FFFFFF"],
            "camera_framing": "Wide municipal plaza views, diverse community members, clear civic signage",
            "motion_pace": "Clear, accessible, steady and inclusive",
        },
        industry_calendar_events=[
            {"month": "September", "name": "National Voter Registration & Civic Engagement Day", "hook": "Make your voice heard in upcoming municipal elections."},
            {"month": "January", "name": "Municipal Fiscal Budget Hearings", "hook": "Participate in open public comment sessions for city department planning."},
        ],
    ),

    # ── 14. Energy & Utilities ────────────────────────────────────────────────
    "energy": _pack(
        "energy",
        "Clean Energy, Solar & Utilities",
        "Commercial solar PPA, battery energy storage systems (BESS), EV fleet chargers, and peak-shaving tariffs.",
        campaign="Energy Savings & Sustainability Campaign",
        post="Grid / Tariff Analysis",
        asset="Solar Payback & IRR Model",
        offer="Complimentary Site Solar Audit",
        cta="Request Commercial Solar & Tariff Feasibility",
        audience="Commercial Real Estate Owners, Facility Managers, Sustainability Officers",
        funnel_stages=[
            {"id": "tariff_pain", "label": "Demand Charge & Tariff Spikes", "channels": ["linkedin"]},
            {"id": "solar_bess_solution", "label": "Solar + Storage Peak Shaving", "channels": ["linkedin"]},
            {"id": "tax_incentives", "label": "IRA Tax Credits & Accelerated Depreciation", "channels": ["linkedin"]},
            {"id": "site_audit", "label": "Site Solar & Battery Feasibility", "channels": ["linkedin"]},
        ],
        content_pillars=[
            {
                "id": "peak_shaving_bess",
                "label": "Peak Demand Charge Elimination",
                "description": "Using commercial battery storage to discharge during 4 PM–9 PM peak utility tariff windows.",
                "hooks": ["Why demand charges account for up to 60% of commercial electricity bills.", "How commercial battery storage shaved $14,000/mo off a distribution warehouse's peak bill."],
            },
            {
                "id": "solar_ira_credits",
                "label": "30% ITC Solar Tax Credits + MACRS",
                "description": "Unlocking federal clean energy credits to achieve a sub-4-year payback.",
                "hooks": ["The 30% Investment Tax Credit math that makes rooftop solar cash-flow positive in year one.", "Transforming idle warehouse roof acreage into a clean revenue asset."],
            },
        ],
        prohibited_guarantees=[
            r"(?i)\bzero\s+electric\s+bill\s+forever\b",
            r"(?i)\bguaranteed\s+(100%|free)\s+electricity\b",
        ],
        taboo_words=["free electricity forever", "zero bills guaranteed", "off-grid magic"],
        required_disclosures=[
            "Actual energy production and utility savings depend on solar irradiance, roof orientation, and utility tariff rate changes.",
            "Tax credits subject to IRS qualification; consult your qualified tax professional.",
        ],
        visual_tokens={
            "aesthetic": "Gleaming commercial rooftop solar arrays, clean energy inverters, wind turbines under blue sky",
            "lighting": "Brilliant natural sunlight, clean blue sky flare, modern clean architecture",
            "color_palette": ["#059669", "#10B981", "#E0F2FE", "#0F172A"],
            "camera_framing": "High-altitude drone sweep across clean solar installations, close-up of digital energy meter",
            "motion_pace": "Expansive, majestic, forward-looking renewable energy rhythm",
        },
        industry_calendar_events=[
            {"month": "April", "name": "Earth Day & Sustainability Action Month", "hook": "Decarbonizing facility footprints while cutting operational energy costs."},
            {"month": "September", "name": "RE+ (Clean Energy & Solar Conference)", "hook": "Latest battery storage chemistry and commercial microgrid topologies."},
        ],
    ),

    # ── 15. Media & Advertising ───────────────────────────────────────────────
    "media": _pack(
        "media",
        "Media, Content & Advertising",
        "Audience syndication, programmatic flights, connected TV (CTV), and brand sponsorship campaigns.",
        campaign="Media Flight & Sponsorship Campaign",
        post="Audience Reach / Flight Case Study",
        asset="Media Kit & Rate Card",
        offer="Custom Flight Proposal",
        cta="Book Q3 Brand Sponsorship Flight",
        audience="Brand Marketers, Media Planners, CMOs, Agency Buyers",
        funnel_stages=[
            {"id": "audience_demographics", "label": "Audience Scale & Affluence Demographics", "channels": ["linkedin"]},
            {"id": "engagement_rates", "label": "Verified Attention & Retention Metrics", "channels": ["linkedin", "x"]},
            {"id": "flight_case_study", "label": "Omnichannel Campaign ROI", "channels": ["linkedin"]},
            {"id": "flight_reservation", "label": "Reserve Sponsorship Flight", "channels": ["linkedin"]},
        ],
        content_pillars=[
            {
                "id": "verified_attention",
                "label": "High-Attention Contextual Sponsorships",
                "description": "Moving beyond cheap banner impressions to high-dwell-time podcast and video sponsorships.",
                "hooks": ["Why 90% of programmatic display ads are ignored — and where high-intent buyers actually engage.", "The sponsorship format delivering a 4.2x higher recall than pre-roll video."],
            },
            {
                "id": "ctv_programmatic",
                "label": "Connected TV (CTV) Household Retargeting",
                "description": "Syncing streaming TV spots with second-screen mobile conversions.",
                "hooks": ["How household IP targeting connects living room CTV ads to mobile purchases in 12 minutes.", "Measuring real foot-traffic uplift from streaming audio campaigns."],
            },
        ],
        prohibited_guarantees=[
            r"(?i)\bguaranteed\s+viral\b",
            r"(?i)\bguaranteed\s+(1m|10m)\s+impressions\s+for\s+free\b",
        ],
        taboo_words=["guaranteed viral post", "infinite free clicks", "secret bot impressions"],
        required_disclosures=[
            "Impressions and reach metrics verified by third-party measurement partners (Nielsen / Comscore).",
            "Sponsorship flights subject to inventory availability and editorial approval.",
        ],
        visual_tokens={
            "aesthetic": "High-production studio cameras, glowing studio monitors, sleek editorial typography",
            "lighting": "Moody neon studio lighting, dramatic key light, cinematic editorial grain",
            "color_palette": ["#18181B", "#A855F7", "#EC4899", "#FAFAFA"],
            "camera_framing": "Broadcast camera rigs, director monitor viewpoints, cinematic close-ups",
            "motion_pace": "Dynamic, rhythmic, broadcast-grade cut tempo",
        },
        industry_calendar_events=[
            {"month": "May", "name": "Upfronts & NewFronts Season", "hook": "Securing premium digital and streaming video inventory for the upcoming broadcast year."},
            {"month": "June", "name": "Cannes Lions Festival of Creativity", "hook": "Celebrating breakthrough storytelling and high-impact brand creative."},
        ],
    ),

    # ── 17. Restaurant & Food Service ─────────────────────────────────────────
    "restaurant": _pack(
        "restaurant",
        "Restaurant, Dining & Catering",
        "Culinary highlights, chef specials, private dining, weekend reservations, and catering bookings.",
        campaign="Dining Experience & Reservation Drive",
        post="Menu Teaser / Chef Story",
        asset="Private Event Menu / Wine List",
        offer="Complimentary Dessert / Table Reservation",
        cta="Reserve Table on OpenTable / Resy",
        audience="Foodies, Corporate Event Planners, Couples, Families",
        funnel_stages=[
            {"id": "culinary_craving", "label": "Mouthwatering Dish & Sizzle Reel", "channels": ["instagram", "tiktok"]},
            {"id": "chef_craft", "label": "Chef Craft & Farm-to-Table Origin", "channels": ["instagram", "facebook"]},
            {"id": "weekend_urgency", "label": "Weekend Table Availability", "channels": ["instagram", "facebook"]},
            {"id": "private_events", "label": "Corporate Catering & Private Dining", "channels": ["linkedin", "facebook"]},
        ],
        content_pillars=[
            {
                "id": "signature_dish",
                "label": "Signature Dish & Culinary Technique",
                "description": "Showcasing artisanal plating, flame searing, fresh pasta rolling, and sommelier pairings.",
                "hooks": ["Slow-braised for 14 hours in Chianti: our signature short rib melting under your fork.", "Watch our pasta master roll fresh tagliatelle daily at 6 AM."],
            },
            {
                "id": "weekend_dining_vibe",
                "label": "Atmosphere, Craft Cocktails & Weekend Energy",
                "description": "Dim candlelight, house-infused mixology, jazz acoustics, and patio seating under bistro lights.",
                "hooks": ["Your Friday evening sanctuary: smoked rosemary mezcal and fresh oysters on the patio.", "Weekend dinner service is 85% booked: reserve your table before Friday."],
            },
        ],
        prohibited_guarantees=[
            r"(?i)\bguaranteed\s+(best\s+food\s+in\s+the\s+world)\b",
            r"(?i)\bzero\s+calorie\s+rich\s+dessert\b",
        ],
        taboo_words=["cure food", "miracle diet burger", "zero wait time guaranteed on Saturday night"],
        required_disclosures=[
            "Please notify your server of any dietary allergies. Consuming raw or undercooked meats may increase risk of foodborne illness.",
            "Reservations held for 15 minutes past scheduled time.",
        ],
        visual_tokens={
            "aesthetic": "Intimate dining ambiance, sizzling grill pans, rustic wood tables, glowing candlelight",
            "lighting": "Warm amber candlelight, dramatic restaurant kitchen backlighting, rich moody shadows",
            "color_palette": ["#451A03", "#B45309", "#FDE68A", "#1C1917"],
            "camera_framing": "Sensory macro food close-ups, overhead feast flat-lays, cocktail pour slow-motion",
            "motion_pace": "Sensual, rhythmic, appetizing cuts",
        },
        industry_calendar_events=[
            {"month": "February", "name": "Valentine's Day Prix Fixe Reservation Rush", "hook": "An unforgettable 5-course candlelit tasting menu for two."},
            {"month": "November", "name": "Holiday Party & Corporate Catering Season", "hook": "Host your company celebration in our private wine cellar dining room."},
        ],
    ),

    # ── 18. B2B E-Commerce & Wholesale ────────────────────────────────────────
    "ecommerce": _pack(
        "ecommerce",
        "B2B Wholesale & E-Commerce",
        "Bulk wholesale catalogs, tier pricing, merchant dropshipping, net-30 terms, and container volume replenishment.",
        campaign="Wholesale Catalog & Bulk Order Drive",
        post="SKU Highlight / Tier Price Drop",
        asset="Wholesale Price Book & Line Sheet",
        offer="Volume Discount / Net-30 Account",
        cta="Download Line Sheet or Open Wholesale Account",
        audience="Retail Store Buyers, E-Commerce Merchants, Procurement Leads",
        funnel_stages=[
            {"id": "catalog_release", "label": "New Season Wholesale Line Sheet", "channels": ["linkedin", "facebook"]},
            {"id": "margin_calculator", "label": "Wholesale Markup & Gross Margin", "channels": ["linkedin"]},
            {"id": "bulk_tier_discount", "label": "Volume Tiers & Fast Restock Delivery", "channels": ["linkedin", "facebook"]},
            {"id": "po_fulfillment", "label": "Purchase Order (PO) & Net Terms Sign-Up", "channels": ["linkedin"]},
        ],
        content_pillars=[
            {
                "id": "retail_margin_calc",
                "label": "65%+ Keystoning Retail Margins",
                "description": "Showing retail buyers how our wholesale unit cost delivers superior shelf gross margin.",
                "hooks": ["Why specialty boutiques are averaging 68% gross margin on this SKU line.", "Volume pricing table: cut your per-unit cost by 22% on pallet orders."],
            },
            {
                "id": "fast_edi_replenishment",
                "label": "Stock Availability & 48-Hour EDI Dispatch",
                "description": "Domestic fulfillment warehouses ensuring retail buyers never experience stockouts.",
                "hooks": ["Zero stockouts during Q4: 100,000 units in stock across our Chicago and Dallas hubs.", "How automated EDI 850 purchase order integration streamlines wholesale billing."],
            },
        ],
        prohibited_guarantees=[
            r"(?i)\bguaranteed\s+(100%|instant)\s+resale\s+profit\b",
            r"(?i)\bfree\s+inventory\s+forever\b",
        ],
        taboo_words=["get rich dropshipping", "guaranteed sellout without effort", "zero risk stock"],
        required_disclosures=[
            "Wholesale accounts subject to business verification and minimum order quantities (MOQ).",
            "Net-30 payment terms subject to commercial credit approval.",
        ],
        visual_tokens={
            "aesthetic": "Organized warehouse logistics, clean retail display shelves, crisp product packaging",
            "lighting": "Clean bright warehouse lighting, high-definition studio product lighting",
            "color_palette": ["#1E293B", "#2563EB", "#60A5FA", "#FFFFFF"],
            "camera_framing": "Sleek product line-up array, organized pallet wrapping, warehouse forklift automation",
            "motion_pace": "Fast, organized, commercial efficiency tempo",
        },
        industry_calendar_events=[
            {"month": "August", "name": "Q4 Holiday Wholesale Pre-Booking Window", "hook": "Lock in wholesale container allocations before peak seasonal stockouts."},
            {"month": "January", "name": "Spring Retail Restock & Line Sheet Launch", "hook": "Fresh SKUs and volume tier promotions for the new retail season."},
        ],
    ),
}

PACK_ORDER: List[str] = list(PACKS)
