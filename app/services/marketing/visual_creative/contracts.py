"""Pydantic schemas and contracts for Universal Visual Creative Director."""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
import uuid


class VisualIntentInputContract(BaseModel):
    """Normalized input contract matching OctaOS SKILL.md specification."""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    deliverable: str = Field("image", description="image|video|animated|edit|storyboard|prompt_only")
    subject: str = Field(..., description="What must be shown or focal entity")
    purpose: str = Field("campaign promotion", description="Why the visual exists")
    audience: str = Field("general", description="Intended viewer or ICP")
    platform: str = Field("instagram", description="Target platform (instagram, linkedin, youtube, etc.)")
    style_direction: List[str] = Field(default_factory=list, description="High-level creative style traits")
    emotion: str = Field("composed and authoritative", description="Intended feeling or tone")
    must_preserve: List[str] = Field(default_factory=list, description="Fixed locks: identity, product silhouette, text")
    must_include: List[str] = Field(default_factory=list, description="Mandatory elements, logos, or props")
    must_avoid: List[str] = Field(default_factory=list, description="Explicit exclusions or known negative artifacts")
    aspect_ratio: str = Field("1:1", description="Target aspect ratio: 1:1, 16:9, 9:16, 4:5")
    duration_seconds: Optional[int] = Field(None, description="Duration in seconds if video")
    frame_rate: Optional[int] = Field(None, description="Video target fps e.g. 24")
    resolution: Optional[str] = Field(None, description="e.g. 1080p, 4k")
    language: str = Field("en", description="Detected or specified language")
    brand_constraints: Dict[str, Any] = Field(default_factory=dict)
    reference_assets: List[str] = Field(default_factory=list, description="URLs or paths of reference media")
    tool_constraints: Dict[str, Any] = Field(default_factory=dict)
    budget_or_latency: str = Field("standard", description="standard|economy|high_fidelity")
    assumptions: List[str] = Field(default_factory=list)

    @field_validator("style_direction", "must_preserve", "must_include", "must_avoid", mode="before")
    @classmethod
    def normalize_list_fields(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        if isinstance(v, list):
            return [str(x) for x in v if x]
        return []


class CreativeSpecialist(BaseModel):
    """Specialist role reasoning lens dynamically assembled for the brief."""
    role_id: str
    role_name: str
    discipline: str
    key_recommendation: str = ""


class CreativeBrief(BaseModel):
    """Structured one-page art direction brief produced by the Creative Director."""
    concept: str = Field(..., description="One-sentence creative concept")
    focal_subject: str
    visual_hierarchy: str = "Subject primary, clean atmospheric environment secondary"
    composition: str = "Centered with 40% negative space on right"
    camera_viewpoint: str = "Eye-level medium-wide shot"
    lighting_setup: str = "Soft directional key with subtle rim lighting"
    color_palette: List[str] = Field(default_factory=list)
    materials_and_surfaces: str = "Tactile organic textures, accurate physical refraction"
    emotional_mood: str
    selected_specialists: List[str] = Field(default_factory=list)
    positive_prompt_blueprint: str = ""
    negative_constraints: List[str] = Field(default_factory=list)
    delivery_specs: Dict[str, Any] = Field(default_factory=dict)


class QualityCriteriaScore(BaseModel):
    """Individual quality gate score on a 0 to 4 scale."""
    criterion_id: str
    name: str
    score: int = Field(..., ge=0, le=4, description="0=failed, 1=major defect, 2=flawed, 3=professional, 4=exceptional")
    weight: float = Field(..., ge=0.0, le=1.0)
    inspected: bool = True
    notes: str = ""


class QualityReviewScorecard(BaseModel):
    """Multimodal inspection quality review matching SKILL.md weighted criteria."""
    criteria: List[QualityCriteriaScore] = Field(default_factory=list)
    weighted_score: float = Field(0.0, ge=0.0, le=100.0)
    critical_blockers: List[str] = Field(default_factory=list)
    defects: List[Dict[str, Any]] = Field(default_factory=list)
    inspected: bool = False
    passed: bool = True
    summary: str = ""


class RevisionItem(BaseModel):
    """Record of a targeted correction cycle."""
    iteration: int
    diagnosed_defect: str
    targeted_fix: str
    previous_score: float
    new_score: float


class VisualRunRecord(BaseModel):
    """Complete auditable visual generation record compatible with OctaOS contracts."""
    request_id: str
    deliverable_type: str = "image"
    status: str = "completed"  # planned|generating|needs_review|completed|partial|failed
    creative_brief: Optional[CreativeBrief] = None
    selected_specialists: List[str] = Field(default_factory=list)
    selected_adapter: Optional[str] = None
    selected_model: Optional[str] = None
    generation_plan: List[Dict[str, Any]] = Field(default_factory=list)
    assets: List[Dict[str, Any]] = Field(default_factory=list)
    primary_asset_url: Optional[str] = None
    quality_review: QualityReviewScorecard = Field(default_factory=QualityReviewScorecard)
    revisions: List[RevisionItem] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    requires_approval: bool = False
    cost_usd: float = 0.0
    next_action: Optional[str] = None
