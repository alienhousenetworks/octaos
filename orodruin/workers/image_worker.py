"""Image Generation Worker (Server-Side GPU Pool).

Deploy on GPU server with Diffusers (SD 1.5 / Sana 1.6B / FLUX.1-schnell).
Does NOT download any weights at import time.
"""
import os
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="OctaOS Image Worker", version="0.1.0")
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "sd15")


class ImageRequest(BaseModel):
    model: str = IMAGE_MODEL
    prompt: str
    negative_prompt: str = ""
    width: int = 1024
    height: int = 1024


@app.get("/health")
def health():
    return {"status": "ok", "worker": "image", "model": IMAGE_MODEL}


@app.post("/generate")
def generate(req: ImageRequest):
    # Server runtime loads pipeline lazily when GPU inference is enabled
    return {
        "status": "queued",
        "model": req.model,
        "prompt": req.prompt,
        "width": req.width,
        "height": req.height,
        "asset_url": None,
    }
