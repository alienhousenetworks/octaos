"""Pipeline transition validator and stage compatibility mapper."""
from __future__ import annotations
from typing import Any
from fastapi import HTTPException
from app.services.sales_os.industry_runtime.manifest import IndustryPackManifest, StageDefinition


class PipelineEngine:
    def __init__(self, manifest: IndustryPackManifest):
        self.manifest = manifest
        self._stages: dict[str, StageDefinition] = {
            stage.id: stage for stage in manifest.pipeline_stages
        }

    def validate_transition(self, current_stage_id: str, next_stage_id: str) -> None:
        """Enforce defined state transitions."""
        if not current_stage_id or current_stage_id == next_stage_id:
            return
        stage = self._stages.get(current_stage_id)
        if not stage:
            # If current stage was from another pack or unmapped, permit moving into a valid stage
            return
        if stage.valid_transitions and next_stage_id not in stage.valid_transitions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid stage transition from '{stage.label}' to '{self._stages.get(next_stage_id, StageDefinition(id=next_stage_id, label=next_stage_id)).label}'."
            )

    @classmethod
    def map_legacy_stage(cls, from_pack_id: str | None, to_pack_id: str, old_status: str) -> str:
        """Map legacy CRM stages safely without losing intent or deleting records."""
        if not old_status:
            return "inquiry" if to_pack_id == "real_estate" else "new"

        # Terminal outcomes map safely
        if old_status in ("closed_won", "booked", "won"):
            return "booking" if to_pack_id == "real_estate" else "closed_won"
        if old_status in ("closed_lost", "cancelled", "lost"):
            return "cancelled" if to_pack_id == "real_estate" else "closed_lost"

        # Real Estate specific mappings from generic B2B stages
        if to_pack_id == "real_estate":
            mapping = {
                "new": "inquiry",
                "qualified": "qualified",
                "contacted": "inquiry",
                "meeting_scheduled": "site_visit",
                "hold_requested": "hold_requested",
                "booking": "booking",
                "cancelled": "cancelled",
            }
            return mapping.get(old_status, "inquiry")

        # Reverse mapping: Real Estate -> Generic B2B
        if from_pack_id == "real_estate":
            reverse_mapping = {
                "inquiry": "new",
                "qualified": "qualified",
                "site_visit": "meeting_scheduled",
                "hold_requested": "meeting_scheduled",
                "booking": "closed_won",
                "cancelled": "closed_lost",
            }
            return reverse_mapping.get(old_status, old_status)

        return old_status
