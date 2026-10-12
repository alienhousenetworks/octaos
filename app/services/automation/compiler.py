"""
OctaOS Flow Compiler.
Compiles canonical AutomationIR into the Activepieces execution engine schema.
"""
from __future__ import annotations

import logging
from typing import Any, Dict
from app.services.automation.base import AutomationIR, StepIR

logger = logging.getLogger(__name__)

# Standard package naming mapping for Activepieces pieces
ACTIVEPIECES_PIECE_MAPPING: Dict[str, str] = {
    "octaos": "@octaos/piece-octaos",
    "slack": "@activepieces/piece-slack",
    "hubspot": "@activepieces/piece-hubspot",
    "google_sheets": "@activepieces/piece-google-sheets",
    "gmail": "@activepieces/piece-gmail",
    "salesforce": "@activepieces/piece-salesforce",
    "telegram": "@activepieces/piece-telegram",
    "whatsapp": "@activepieces/piece-whatsapp",
    "webhook": "@activepieces/piece-webhook",
    "http": "@activepieces/piece-http",
    "code": "@activepieces/piece-code",
}


class FlowCompiler:
    """
    Translates OctaOS canonical AutomationIR into Activepieces Flow schema.
    """

    @classmethod
    def compile_to_activepieces(cls, ir: AutomationIR) -> Dict[str, Any]:
        """
        Compiles AutomationIR into the Activepieces Flow Version structure.
        """
        # 1. Compile Trigger
        trigger_piece = "@octaos/piece-octaos" if ir.trigger.type == "octaos_event" else "@activepieces/piece-webhook"
        trigger_action = ir.trigger.event or "catch_webhook"

        trigger_def: Dict[str, Any] = {
            "name": "trigger_step",
            "type": "PIECE_TRIGGER",
            "displayName": ir.trigger.display_name or f"OctaOS Event: {ir.trigger.event or ir.trigger.type}",
            "settings": {
                "pieceName": trigger_piece,
                "pieceVersion": "1.0.0",
                "triggerName": trigger_action,
                "input": ir.trigger.config or {},
            },
            "valid": True,
        }

        # 2. Compile Steps (Linked list in Activepieces)
        current_parent = trigger_def
        for idx, step in enumerate(ir.steps):
            piece_package = ACTIVEPIECES_PIECE_MAPPING.get(step.piece, f"@activepieces/piece-{step.piece}")
            action_def: Dict[str, Any] = {
                "name": f"step_{idx + 1}_{step.id}",
                "type": "PIECE",
                "displayName": step.display_name or f"{step.piece.capitalize()}: {step.action}",
                "settings": {
                    "pieceName": piece_package,
                    "pieceVersion": "1.0.0",
                    "actionName": step.action,
                    "input": step.parameters or {},
                },
                "valid": True,
            }
            current_parent["nextAction"] = action_def
            current_parent = action_def

        flow_schema = {
            "displayName": ir.name,
            "description": ir.description or "",
            "trigger": trigger_def,
            "metadata": {
                "octaos_ir_version": "1.0",
                "category": ir.category,
                "risk_level": ir.risk_level.value if hasattr(ir.risk_level, "value") else str(ir.risk_level),
                "requires_approval": ir.requires_approval,
            },
        }
        return flow_schema
