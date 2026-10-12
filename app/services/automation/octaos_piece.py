"""
OctaOS Native Automation Piece Specification (@octaos/piece-octaos).
Exposes native OctaOS triggers and actions as standard automation building blocks (Principle #11).
"""
from typing import Any, Dict, List

OCTAOS_PIECE_METADATA = {
    "name": "@octaos/piece-octaos",
    "displayName": "OctaOS Enterprise Core",
    "version": "1.0.0",
    "description": "Native triggers and actions for OctaOS CRM, Support, AI Agents, and Executive Governance.",
    "logoUrl": "https://octaos.org/favicon.ico",
    "auth": {
        "type": "SECRET_TEXT",
        "displayName": "OctaOS Internal Token",
        "required": True,
    },
    "triggers": [
        {
            "name": "lead.created",
            "displayName": "New Lead Ingested",
            "description": "Fires when a new prospect is added to the OctaOS Sales pipeline.",
            "sampleData": {"lead_id": "lead_123", "name": "Sarah Connor", "company": "Cyberdyne", "email": "sarah@cyberdyne.io"},
        },
        {
            "name": "lead.qualified",
            "displayName": "Lead Qualified",
            "description": "Fires when a lead score crosses the qualification threshold.",
            "sampleData": {"lead_id": "lead_123", "name": "Sarah Connor", "company": "Cyberdyne", "score": 85, "estimated_value": 15000},
        },
        {
            "name": "deal.created",
            "displayName": "Deal Room Provisioned",
            "description": "Fires when a high-value deal room is opened.",
            "sampleData": {"deal_id": "deal_456", "company": "Stark Industries", "value": 75000},
        },
        {
            "name": "deal.won",
            "displayName": "Deal Won (Closed)",
            "description": "Fires when a deal transitions to Closed-Won status.",
            "sampleData": {"deal_id": "deal_456", "company": "Stark Industries", "deal_amount": 75000, "owner_name": "Alex Vance"},
        },
        {
            "name": "ticket.created",
            "displayName": "Support Ticket Created",
            "description": "Fires when a customer submits a support inquiry.",
            "sampleData": {"ticket_id": "tick_789", "customer_name": "Bruce Wayne", "subject": "Billing inquiry"},
        },
        {
            "name": "ticket.escalated",
            "displayName": "Support Ticket Escalated (P1/Urgent)",
            "description": "Fires when SLA breach or urgent escalation is flagged.",
            "sampleData": {"ticket_id": "tick_789", "customer_name": "Bruce Wayne", "subject": "System downtime", "description": "Payment gateway timeout"},
        },
        {
            "name": "payment.received",
            "displayName": "Payment Succeeded",
            "description": "Fires when an invoice or subscription payment is confirmed.",
            "sampleData": {"payment_id": "pay_999", "amount": 1200, "currency": "USD", "customer_email": "finance@waynecorp.com"},
        },
        {
            "name": "approval.requested",
            "displayName": "Executive Approval Required",
            "description": "Fires when a sensitive action is queued in the HITL review queue.",
            "sampleData": {"approval_id": "appr_111", "title": "Large Refund Sign-Off", "risk_level": "high"},
        },
    ],
    "actions": [
        {
            "name": "create_lead",
            "displayName": "Create Lead in OctaOS",
            "description": "Adds a new lead to the OctaOS waterfall enrichment pipeline.",
            "parameters": {"name": {"type": "string", "required": True}, "email": {"type": "string", "required": True}, "company": {"type": "string"}},
        },
        {
            "name": "update_lead",
            "displayName": "Update Lead Status",
            "description": "Updates lead score, stage, or tags in OctaOS.",
            "parameters": {"lead_id": {"type": "string", "required": True}, "stage": {"type": "string"}},
        },
        {
            "name": "trigger_ai_agent",
            "displayName": "Invoke OctaOS Specialized AI Agent",
            "description": "Dispatches a dedicated task to Sales, Support, Marketing, or HR AI Agent.",
            "parameters": {"agent_slug": {"type": "string", "required": True}, "task": {"type": "string", "required": True}},
        },
        {
            "name": "request_approval",
            "displayName": "Stage HITL Approval Request",
            "description": "Stages a human review item into the OctaOS Executive Approval queue.",
            "parameters": {"title": {"type": "string", "required": True}, "risk_level": {"type": "string"}},
        },
        {
            "name": "send_notification",
            "displayName": "Send In-App Notification",
            "description": "Sends an instant alert to the OctaOS Notification bell and dashboard.",
            "parameters": {"message": {"type": "string", "required": True}, "severity": {"type": "string"}},
        },
    ],
}
