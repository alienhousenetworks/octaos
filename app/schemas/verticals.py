from pydantic import BaseModel
from typing import Optional, List
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

class LeadCreate(LeadBase):
    pass

class Lead(LeadBase):
    id: str
    tenant_id: str
    score: int
    status: str
    data: Optional[dict] = None
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
    is_manual_media: Optional[bool] = False
    day: Optional[int] = None

class ContentPostCreate(ContentPostBase):
    pass

class ContentPost(ContentPostBase):
    id: str
    tenant_id: str
    status: str
    approval_status: str
    created_at: datetime

    class Config:
        from_attributes = True

class CampaignCreate(BaseModel):
    topic: str
    days: int = 30
    platforms: List[str] = ["linkedin", "instagram", "facebook"]
    text_provider: str = "gemini"
    text_model: Optional[str] = None
    image_provider: str = "openai"
    video_provider: str = "pika"
    generate_images: bool = True
    generate_videos: bool = True

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
    context_summary: Optional[str] = None
    transcript: List[dict] = []
    action_items: List[dict] = []
    created_at: datetime

    class Config:
        from_attributes = True

