"""Video Generation Worker (Server-Side GPU Pool).

Deploy on GPU server with Wan 2.1 1.3B / LTX-Video 2B.
Does NOT download any weights at import time.
"""
import os
from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="OctaOS Video Worker", version="0.1.0")
VIDEO_MODEL = os.getenv("VIDEO_MODEL", "wan2.1-t2v-1.3b")


class VideoRequest(BaseModel):
    model: str = VIDEO_MODEL
    prompt: str
    image_url: Optional[str] = None
    num_frames: int = 49
    fps: int = 16


@app.get("/health")
def health():
    return {"status": "ok", "worker": "video", "model": VIDEO_MODEL}


@app.post("/generate")
def generate(req: VideoRequest):
    return {
        "status": "queued",
        "model": req.model,
        "prompt": req.prompt,
        "num_frames": req.num_frames,
        "fps": req.fps,
        "asset_url": None,
    }
