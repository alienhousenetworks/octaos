"""
OctaOS Enterprise Automation Templates.
Deterministic, battle-tested business automation blueprints matching Principle #17.
Enables instant parameter-filling before falling back to free-form AI synthesis.
"""
from typing import Any, Dict, List
from app.services.automation.base import AutomationIR, TriggerIR, StepIR, RiskLevel

ENTERPRISE_TEMPLATES: List[Dict[str, Any]] = [
    {
        "id": "tpl_lead_qualification_slack_crm",
        "name": "Qualified Lead Instant Alert & CRM Deal Creation",
        "slug": "lead-qualification-slack-crm",
        "category": "sales",
        "description": "When a prospect reaches qualified status in OctaOS Sales, instantly notify #sales-pipeline in Slack, provision a deal in HubSpot, and dispatch an intro email.",
        "icon": "Target",
        "keywords": ["lead", "sales", "slack", "hubspot", "crm", "qualification", "deal"],
        "required_connections": ["slack", "hubspot", "gmail", "octaos"],
        "risk_level": "low",
        "requires_approval": False,
        "default_ir": AutomationIR(
            name="Qualified Lead Instant Alert & CRM Deal Creation",
            slug="qualified-lead-alert-crm",
            category="sales",
            description="Automatic notifications and CRM sync upon lead qualification.",
            risk_level=RiskLevel.LOW,
            requires_approval=False,
            trigger=TriggerIR(
                type="octaos_event",
                event="lead.qualified",
                display_name="OctaOS: Lead Qualified",
                config={"min_score": 70},
            ),
            steps=[
                StepIR(
                    id="step_slack_alert",
                    piece="slack",
                    action="send_message",
                    display_name="Slack: Notify #sales-pipeline",
                    parameters={
                        "channel": "#sales-pipeline",
                        "text": "🎯 *New Qualified Lead Alert!*\n*Name:* {{trigger.name}}\n*Company:* {{trigger.company}}\n*Score:* {{trigger.score}}/100\n*Email:* {{trigger.email}}",
                    },
                ),
                StepIR(
                    id="step_hubspot_deal",
                    piece="hubspot",
                    action="create_deal",
                    display_name="HubSpot: Create Sales Deal",
                    parameters={
                        "dealname": "Deal: {{trigger.company}} - {{trigger.name}}",
                        "pipeline": "default",
                        "dealstage": "appointmentscheduled",
                        "amount": "{{trigger.estimated_value || 5000}}",
                    },
                ),
                StepIR(
                    id="step_email_intro",
                    piece="gmail",
                    action="send_email",
                    display_name="Gmail: Send Outreach Intro",
                    parameters={
                        "to": "{{trigger.email}}",
                        "subject": "Quick intro regarding {{trigger.company}} x OctaOS",
                        "body": "Hi {{trigger.name}},\n\nSaw your team is scaling RevOps. Would love to share how OctaOS automates enterprise sales.\n\nBest,\nSales Team",
                    },
                ),
            ],
            required_connections=["slack", "hubspot", "gmail", "octaos"],
        ).model_dump(),
    },
    {
        "id": "tpl_support_ticket_escalation",
        "name": "High-Priority Support Escalation & AI Triage",
        "slug": "support-ticket-escalation",
        "category": "support",
        "description": "When a customer support ticket is marked urgent or escalated, trigger real-time Slack notification to engineers and invoke OctaOS Support AI Agent for diagnostics.",
        "icon": "AlertTriangle",
        "keywords": ["support", "ticket", "escalation", "urgent", "slack", "triage", "ai agent"],
        "required_connections": ["slack", "octaos"],
        "risk_level": "medium",
        "requires_approval": False,
        "default_ir": AutomationIR(
            name="High-Priority Support Escalation & AI Triage",
            slug="support-escalation-ai-triage",
            category="support",
            description="Immediate triage and alerting for escalated customer tickets.",
            risk_level=RiskLevel.MEDIUM,
            requires_approval=False,
            trigger=TriggerIR(
                type="octaos_event",
                event="ticket.escalated",
                display_name="OctaOS: Ticket Escalated",
                config={"severity": "critical"},
            ),
            steps=[
                StepIR(
                    id="step_slack_urgent",
                    piece="slack",
                    action="send_message",
                    display_name="Slack: Alert #support-critical",
                    parameters={
                        "channel": "#support-critical",
                        "text": "🚨 *P1 Support Escalation Detected!*\n*Ticket ID:* #{{trigger.ticket_id}}\n*Customer:* {{trigger.customer_name}}\n*Issue:* {{trigger.subject}}\n*Summary:* {{trigger.description}}",
                    },
                ),
                StepIR(
                    id="step_agent_triage",
                    piece="octaos",
                    action="trigger_agent",
                    display_name="OctaOS: Run Support Agent Diagnostic",
                    parameters={
                        "agent_slug": "support_agent",
                        "task": "diagnose_ticket",
                        "ticket_id": "{{trigger.ticket_id}}",
                    },
                ),
            ],
            required_connections=["slack", "octaos"],
        ).model_dump(),
    },
    {
        "id": "tpl_deal_won_onboarding",
        "name": "Deal Won Customer Onboarding & Celebration",
        "slug": "deal-won-onboarding",
        "category": "sales",
        "description": "Celebrate closed deals in company Slack, append new account to Google Sheets Ledger, and initialize automated customer onboarding.",
        "icon": "Trophy",
        "keywords": ["deal won", "close", "google sheets", "slack", "celebration", "onboarding"],
        "required_connections": ["slack", "google_sheets", "octaos"],
        "risk_level": "low",
        "requires_approval": False,
        "default_ir": AutomationIR(
            name="Deal Won Customer Onboarding & Celebration",
            slug="deal-won-customer-onboarding",
            category="sales",
            description="Broadcast closed deal and sync ledger.",
            risk_level=RiskLevel.LOW,
            requires_approval=False,
            trigger=TriggerIR(
                type="octaos_event",
                event="deal.won",
                display_name="OctaOS: Deal Won",
                config={},
            ),
            steps=[
                StepIR(
                    id="step_slack_celebrate",
                    piece="slack",
                    action="send_message",
                    display_name="Slack: Broadcast in #general",
                    parameters={
                        "channel": "#general",
                        "text": "🎉 *DEAL CLOSED!* Welcome {{trigger.company}} to the family!\n*ARR:* ${{trigger.deal_amount}}\n*Account Owner:* {{trigger.owner_name}} 🚀",
                    },
                ),
                StepIR(
                    id="step_sheets_append",
                    piece="google_sheets",
                    action="append_row",
                    display_name="Google Sheets: Append to Client Registry",
                    parameters={
                        "spreadsheet_id": "client_master_ledger",
                        "row_values": ["{{trigger.company}}", "{{trigger.deal_amount}}", "{{trigger.owner_name}}", "{{timestamp}}"],
                    },
                ),
            ],
            required_connections=["slack", "google_sheets", "octaos"],
        ).model_dump(),
    },
    {
        "id": "tpl_high_risk_financial_approval",
        "name": "High-Value Transaction / Refund Governance & HITL",
        "slug": "high-risk-financial-approval",
        "category": "executive",
        "description": "Enforce Human-In-The-Loop approval when refund or payout exceeds $1,000 before side-effect execution.",
        "icon": "ShieldCheck",
        "keywords": ["refund", "financial", "approval", "hitl", "governance", "payment"],
        "required_connections": ["octaos", "slack"],
        "risk_level": "high",
        "requires_approval": True,
        "default_ir": AutomationIR(
            name="High-Value Transaction Governance & HITL",
            slug="financial-governance-hitl",
            category="executive",
            description="Enforces strict dual approval before financial mutation.",
            risk_level=RiskLevel.HIGH,
            requires_approval=True,
            trigger=TriggerIR(
                type="octaos_event",
                event="payment.refund_requested",
                display_name="OctaOS: Refund Requested",
                config={"threshold_usd": 1000},
            ),
            steps=[
                StepIR(
                    id="step_hitl_approval",
                    piece="octaos",
                    action="request_approval",
                    display_name="OctaOS: Stage HITL Approval Request",
                    parameters={
                        "title": "Refund Approval: {{trigger.customer_name}} (${{trigger.amount}})",
                        "risk_level": "high",
                        "description": "Refund request exceeds $1,000 threshold. Finance executive sign-off required.",
                    },
                ),
                StepIR(
                    id="step_slack_warn",
                    piece="slack",
                    action="send_message",
                    display_name="Slack: Alert #finance-approvals",
                    parameters={
                        "channel": "#finance-approvals",
                        "text": "⚠️ *Pending HITL Financial Approval*\n*Customer:* {{trigger.customer_name}}\n*Amount:* ${{trigger.amount}}\nReview at: /app/approvals",
                    },
                ),
            ],
            required_connections=["octaos", "slack"],
        ).model_dump(),
    },
]


def find_matching_template(prompt: str) -> Dict[str, Any] | None:
    """Matches user prompt against predefined enterprise templates based on keywords."""
    p_lower = prompt.lower()
    best_match = None
    max_hits = 0

    for tpl in ENTERPRISE_TEMPLATES:
        hits = sum(1 for kw in tpl["keywords"] if kw in p_lower)
        if hits > max_hits and hits >= 2:
            max_hits = hits
            best_match = tpl

    return best_match
