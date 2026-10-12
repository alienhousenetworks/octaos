"""Base interfaces and protocol for multimodal AI provider adapters."""
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional, Protocol, runtime_checkable
from pydantic import BaseModel, Field


class ModalityType(str, Enum):
    TEXT_TO_TEXT = "text_to_text"
    TEXT_TO_IMAGE = "text_to_image"
    IMAGE_TO_IMAGE = "image_to_image"
    TEXT_TO_VIDEO = "text_to_video"
    IMAGE_TO_VIDEO = "image_to_video"


class ModelInfo(BaseModel):
    provider: str
    slug: str
    display_name: str
    modalities: List[str] = Field(default_factory=list)  # list of ModalityType values
    supports_image_input: bool = False
    context_length: Optional[int] = None
    pricing: Dict[str, Any] = Field(default_factory=dict)
    capabilities: Dict[str, Any] = Field(default_factory=dict)
    status: str = "available"  # available | incompatible | not_found | unverified | disabled
    source: str = "curated"  # curated | custom
    last_verified_at: Optional[datetime] = None
    last_error: Optional[str] = None


class TextReq(BaseModel):
    model: str
    prompt: str
    system_prompt: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = 4096
    response_format: Optional[Dict[str, Any]] = None
    images: Optional[List[Dict[str, Any]]] = None  # for vision/multimodal text models


class TextResult(BaseModel):
    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    model_used: str
    raw_response: Optional[Dict[str, Any]] = None


class ImageReq(BaseModel):
    model: str
    prompt: str
    negative_prompt: Optional[str] = None
    aspect_ratio: str = "1:1"
    width: Optional[int] = 1024
    height: Optional[int] = 1024
    reference_image_url: Optional[str] = None  # for image-to-image or editing
    steps: Optional[int] = 28
    guidance_scale: Optional[float] = 3.5


class ImageResult(BaseModel):
    image_url: str  # Direct or data URI
    cost_usd: float = 0.0
    model_used: str
    raw_response: Optional[Dict[str, Any]] = None


class VideoReq(BaseModel):
    model: str
    prompt: str
    negative_prompt: Optional[str] = None
    aspect_ratio: str = "16:9"
    duration_seconds: int = 5
    reference_image_url: Optional[str] = None  # for image-to-video animation
    camera_movement: Optional[str] = None


class JobHandle(BaseModel):
    job_id: str
    provider: str
    model: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class JobStatus(BaseModel):
    job_id: str
    status: str  # "queued", "in_progress", "completed", "failed"
    result_url: Optional[str] = None
    error: Optional[str] = None
    progress_pct: Optional[float] = None
    cost_usd: float = 0.0


@runtime_checkable
class ProviderAdapter(Protocol):
    name: str

    async def list_models(self, api_key: str) -> List[ModelInfo]:
        """Fetch and normalize all available models from this provider."""
        ...

    async def generate_text(self, req: TextReq, api_key: str) -> TextResult:
        """Execute text generation."""
        ...

    async def generate_image(self, req: ImageReq, api_key: str) -> ImageResult:
        """Execute image generation (text-to-image or image+text-to-image)."""
        ...

    async def submit_video(self, req: VideoReq, api_key: str) -> JobHandle:
        """Submit an asynchronous video generation task."""
        ...

    async def poll_video(self, handle: JobHandle, api_key: str) -> JobStatus:
        """Poll video job status."""
        ...
