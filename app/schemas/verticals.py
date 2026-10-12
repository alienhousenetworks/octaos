from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime

class LeadBase(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    source: Optional[str] = None
    personal_email: Optional[str] = None
    company_email: Optional[str] = None
    mobile_no: Optional[str] = None
    company_contact_no: Optional[str] = None
    need_of_what: Optional[str] = None
    how_much: Optional[str] = None
    why: Optional[str] = None
    target_context: Optional[str] = None
    priority: Optional[str] = "medium"
    status: Optional[str] = "captured"
    score: Optional[int] = 0
    assigned_to: Optional[str] = "Sales AI Agent"
    data: Optional[dict] = None

class LeadCreate(LeadBase):
    pass

class Lead(LeadBase):
    id: str
    tenant_id: str
    score: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ContentPostBase(BaseModel):
    platform: str
    content: str
    scheduled_at: Optional[datetime] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    media_prompt: Optional[str] = None
    media_prompt_enabled: Optional[bool] = False
    image_prompt: Optional[str] = None
    image_prompt_enabled: Optional[bool] = False
    video_prompt: Optional[str] = None
    video_prompt_enabled: Optional[bool] = False
    remotion_prompt: Optional[str] = None
    remotion_prompt_enabled: Optional[bool] = False
    remotion_provider: Optional[str] = "gemini"
    remotion_model: Optional[str] = "gemini-2.5-flash"
    is_manual_media: Optional[bool] = False
    day: Optional[int] = None

class ContentPostCreate(ContentPostBase):
    pass

class ContentPostManualMultiCreate(BaseModel):
    platforms: List[str] = ["linkedin"]
    content: str
    tags: Optional[List[str]] = []
    scheduled_at: Optional[datetime] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    is_manual_media: Optional[bool] = True
    publish_mode: str = "schedule"  # "now" | "schedule" | "draft"
    day: Optional[int] = 1
    image_prompt: Optional[str] = None
    image_prompt_enabled: Optional[bool] = False
    video_prompt: Optional[str] = None
    video_prompt_enabled: Optional[bool] = False
    remotion_prompt: Optional[str] = None
    remotion_prompt_enabled: Optional[bool] = False

class ContentPost(ContentPostBase):
    id: str
    tenant_id: str
    status: str
    approval_status: str
    created_at: datetime
    published_at: Optional[datetime] = None
    external_post_id: Optional[str] = None
    external_url: Optional[str] = None
    impressions: Optional[float] = 0
    reach: Optional[float] = 0
    engagement: Optional[float] = 0
    likes: Optional[float] = 0
    comments: Optional[float] = 0
    shares: Optional[float] = 0
    clicks: Optional[float] = 0
    ctr: Optional[float] = 0
    engagement_rate: Optional[float] = 0
    performance_score: Optional[float] = 0
    learning_tags: Optional[List[str]] = None
    insights_synced_at: Optional[datetime] = None
    used_model: Optional[str] = None
    fallback_reason: Optional[str] = None
    cost_usd: Optional[float] = 0.0

    class Config:
        from_attributes = True


class ModelSelection(BaseModel):
    provider: str = "auto"  # auto | openrouter | together
    model: Optional[str] = None  # None = Auto/curated default
    allow_fallback: bool = True


class CampaignCreate(BaseModel):
    topic: str
    days: int = 30
    platforms: List[str] = ["linkedin", "instagram", "facebook"]
    content_format: str = "social_posts"  # social_posts | blog_articles | video_first | omnichannel_mix
    text: ModelSelection = ModelSelection()
    image: ModelSelection = ModelSelection()
    video: ModelSelection = ModelSelection()
    reference_image_url: Optional[str] = None
    budget_cap_usd: Optional[float] = None
    # Backward compatibility fields
    text_provider: Optional[str] = "auto"
    text_model: Optional[str] = None
    image_provider: Optional[str] = "together"
    video_provider: Optional[str] = "together"
    generate_images: bool = True
    generate_videos: bool = False
    generate_remotion: bool = False
    remotion_provider: Optional[str] = "gemini"
    remotion_model: Optional[str] = "gemini-2.5-flash"
    # Cadence and Multi-Slot Scheduling
    posts_per_day: int = 1  # 1 (Peak Slot), 2 (Morning + Evening), 3 (Omnichannel Horizon)
    target_time_slots: Optional[List[str]] = None  # e.g., ["09:00", "17:00"]
    @validator("days")
    def validate_days(cls, v):
        if v < 1 or v > 30:
            raise ValueError("Campaign duration must be between 1 and 30 days.")
        return v


class ModelValidateRequest(BaseModel):
    provider: str
    modality: str  # text, image, video
    model: str
    mode: Optional[str] = None  # text_to_text, text_to_image, image_to_image, text_to_video, image_to_video


class ModelValidateResponse(BaseModel):
    status: str  # available | incompatible | not_found | no_key | unverified
    message: str
    display_name: Optional[str] = None
    capabilities: Optional[dict] = None
    pricing: Optional[dict] = None
    context_length: Optional[int] = None
    suggestions: List[str] = []
    link: Optional[str] = None


class CustomModelCreate(BaseModel):
    provider: str
    slug: str
    modality: str
    mode: Optional[str] = None


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result_url: Optional[str] = None
    error: Optional[str] = None
    progress_pct: Optional[float] = None
    cost_usd: float = 0.0
    current_stage: Optional[str] = None
    stages: Optional[List[Dict[str, Any]]] = None
    stage_logs: Optional[List[Dict[str, Any]]] = None
    kind: Optional[str] = None
    topic: Optional[str] = None
    days: Optional[int] = None

class CandidateBase(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = "sourced"
    scorecard: Optional[dict] = None

class CandidateCreate(CandidateBase):
    pass

class Candidate(CandidateBase):
    id: str
    tenant_id: str
    created_at: datetime

    class Config:
        from_attributes = True

class MeetingMessage(BaseModel):
    sender: str
    content: str
    timestamp: Optional[str] = None

class MeetingActionItem(BaseModel):
    id: str
    assigned_to: str
    description: str
    status: str # pending, completed, failed

class AgentMeetingBase(BaseModel):
    title: str
    trigger_type: str
    trigger_id: Optional[str] = None
    participants: List[str]

class AgentMeetingCreate(AgentMeetingBase):
    pass

class AgentMeeting(AgentMeetingBase):
    id: str
    tenant_id: str
    status: str
    current_phase: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    total_tokens: Optional[int] = 0
    total_cost_usd: Optional[float] = 0.0
    failure_reason: Optional[str] = None
    context_summary: Optional[str] = None
    transcript: List[dict] = []
    action_items: List[dict] = []
    created_at: datetime

    class Config:
        from_attributes = True


class BusinessProfileBase(BaseModel):
    company_name: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    service_description: Optional[str] = None
    target_countries: Optional[List[str]] = None
    target_industries: Optional[List[str]] = None
    target_company_size: Optional[str] = None
    target_budget_range: Optional[str] = None
    target_decision_makers: Optional[List[str]] = None
    usp: Optional[str] = None
    case_studies: Optional[str] = None
    offer_details: Optional[str] = None
    calendars: Optional[List[str]] = None
    communication_channels: Optional[List[str]] = None
    extra_context: Optional[str] = None
    v3_workflow_status: Optional[dict] = None
    sales_emails: Optional[List[str]] = None
    support_emails: Optional[List[str]] = None
    lead_freshness: Optional[str] = "30_days"

class BusinessProfileCreate(BusinessProfileBase):
    pass

class BusinessProfile(BusinessProfileBase):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


