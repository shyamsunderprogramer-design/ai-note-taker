"""Video clip management and highlight reel generation endpoints."""
import logging
import time
import uuid
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from routes.deps import require_authentication
from security import ErrorCode, error_response
from security.auth import User

logger = logging.getLogger("routes.video")

try:
    from modules.ai.highlight_reel import highlight_reel_generator
    HAS_HIGHLIGHT_REEL = True
except ImportError:
    HAS_HIGHLIGHT_REEL = False

router = APIRouter()

# In-memory stores (production: database)
_video_clips: Dict[str, dict] = {}
_highlight_reels: Dict[str, dict] = {}
_captured_slides: Dict[str, List[dict]] = {}


@router.post("/video/clips")
async def create_video_clip(
    body: dict,
    user: User = Depends(require_authentication),
):
    """Create a video clip from a transcript section."""
    conversation_id = body.get("conversation_id")
    start_time = body.get("start_time", 0)
    end_time = body.get("end_time", 0)
    title = body.get("title", "Untitled Clip")

    if not conversation_id:
        return error_response(ErrorCode.VALIDATION_ERROR, "conversation_id required", status_code=400)
    if end_time <= start_time:
        return error_response(ErrorCode.VALIDATION_ERROR, "end_time must be greater than start_time", status_code=400)

    clip_id = str(uuid.uuid4())[:8]
    clip = {
        "id": clip_id,
        "conversation_id": conversation_id,
        "start_time": start_time,
        "end_time": end_time,
        "duration_seconds": end_time - start_time,
        "title": title,
        "created_by": user.id,
        "created_at": time.time(),
    }
    _video_clips[clip_id] = clip

    return clip


@router.get("/video/clips/{conversation_id}")
async def list_video_clips(
    conversation_id: str,
    user: User = Depends(require_authentication),
):
    """List all clips for a conversation."""
    clips = [
        c for c in _video_clips.values()
        if c["conversation_id"] == conversation_id
    ]
    clips.sort(key=lambda x: x["start_time"])
    return {"clips": clips, "total": len(clips)}


@router.post("/video/highlight-reel")
async def generate_highlight_reel(
    body: dict,
    user: User = Depends(require_authentication),
):
    """Generate an AI-selected highlight reel from conversation messages."""
    conversation_id = body.get("conversation_id")
    messages = body.get("messages", [])
    max_duration = body.get("max_duration_seconds", 120)
    style = body.get("style", "balanced")

    if not conversation_id:
        return error_response(ErrorCode.VALIDATION_ERROR, "conversation_id required", status_code=400)

    if not HAS_HIGHLIGHT_REEL:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Highlight reel module not available", status_code=503)

    clips = highlight_reel_generator.generate(messages, max_duration, style)
    reel_id = str(uuid.uuid4())[:8]

    reel = {
        "id": reel_id,
        "conversation_id": conversation_id,
        "style": style,
        "max_duration_seconds": max_duration,
        "clips": clips,
        "total_clips": len(clips),
        "total_duration": sum(c["end"] - c["start"] for c in clips),
        "created_by": user.id,
        "created_at": time.time(),
    }
    _highlight_reels[reel_id] = reel

    return reel


@router.get("/video/highlight-reel/{reel_id}")
async def get_highlight_reel(reel_id: str, user: User = Depends(require_authentication)):
    """Get highlight reel details."""
    reel = _highlight_reels.get(reel_id)
    if not reel:
        raise HTTPException(status_code=404, detail="Highlight reel not found")
    return reel


@router.post("/video/slides/capture")
async def capture_slide(
    body: dict,
    user: User = Depends(require_authentication),
):
    """Capture a slide from a video frame at a given timestamp."""
    conversation_id = body.get("conversation_id")
    timestamp = body.get("timestamp", 0)

    if not conversation_id:
        return error_response(ErrorCode.VALIDATION_ERROR, "conversation_id required", status_code=400)

    slide_id = str(uuid.uuid4())[:8]
    slide = {
        "id": slide_id,
        "conversation_id": conversation_id,
        "timestamp": timestamp,
        "image_data": None,
        "ocr_text": "",
        "created_by": user.id,
        "created_at": time.time(),
    }

    if conversation_id not in _captured_slides:
        _captured_slides[conversation_id] = []
    _captured_slides[conversation_id].append(slide)

    return slide


@router.get("/video/slides/{conversation_id}")
async def list_slides(
    conversation_id: str,
    user: User = Depends(require_authentication),
):
    """List captured slides for a conversation."""
    slides = _captured_slides.get(conversation_id, [])
    return {"slides": slides, "total": len(slides)}