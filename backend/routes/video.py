"""Video clip management and highlight reel generation endpoints."""
import logging
import time
import uuid
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException

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


# ═══════════════════════════════════════════════════════════════════════════════
# VIDEO RECORDING (T23)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/recordings/start")
async def start_recording(
    body: dict,
    user: User = Depends(require_authentication),
):
    """Start a screen/camera recording session."""
    try:
        from modules.video.recording_manager import get_manager
        manager = get_manager()
        session = manager.start(
            user_id=user.id,
            title=body.get("title", ""),
            source=body.get("source", "screen"),
            metadata=body.get("metadata", {}),
        )
        return {"status": "recording", "session": {"id": session.id, "title": session.title, "source": session.source}}
    except ImportError:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Recording manager not available", status_code=503)
    except Exception as e:
        logger.error("[Recording] Start error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.post("/recordings/{session_id}/stop")
async def stop_recording(
    session_id: str,
    body: dict,
    user: User = Depends(require_authentication),
):
    """Stop a recording session."""
    try:
        from modules.video.recording_manager import get_manager
        manager = get_manager()
        session = manager.stop(
            session_id,
            duration_seconds=body.get("duration_seconds", 0),
            size_bytes=body.get("size_bytes", 0),
        )
        if not session:
            raise HTTPException(status_code=404, detail="Recording session not found")
        return {"status": "completed", "session": {"id": session.id, "duration_seconds": session.duration_seconds}}
    except ImportError:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Recording manager not available", status_code=503)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[Recording] Stop error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.get("/recordings")
async def list_recordings(
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(require_authentication),
):
    """List recordings for the current user."""
    try:
        from modules.video.recording_manager import get_manager
        manager = get_manager()
        sessions = manager.list_for_user(user.id, limit=limit, offset=offset)
        return {
            "recordings": [
                {"id": s.id, "title": s.title, "source": s.source, "status": s.status,
                 "duration_seconds": s.duration_seconds, "created_at": s.created_at.isoformat() if s.created_at else None}
                for s in sessions
            ],
            "total": len(sessions),
        }
    except ImportError:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Recording manager not available", status_code=503)
    except Exception as e:
        logger.error("[Recording] List error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.get("/recordings/{session_id}")
async def get_recording(
    session_id: str,
    user: User = Depends(require_authentication),
):
    """Get recording session details."""
    try:
        from modules.video.recording_manager import get_manager
        manager = get_manager()
        session = manager.get(session_id)
        if not session or session.user_id != user.id:
            raise HTTPException(status_code=404, detail="Recording not found")
        return {
            "id": session.id,
            "title": session.title,
            "source": session.source,
            "status": session.status,
            "duration_seconds": session.duration_seconds,
            "size_bytes": session.size_bytes,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "metadata": session.metadata,
        }
    except ImportError:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Recording manager not available", status_code=503)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[Recording] Get error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.get("/recordings/search")
async def search_recordings(
    q: str,
    user: User = Depends(require_authentication),
):
    """Search recordings by title."""
    try:
        from modules.video.recording_manager import get_manager
        manager = get_manager()
        sessions = manager.search(user.id, q)
        return {
            "recordings": [
                {"id": s.id, "title": s.title, "status": s.status,
                 "duration_seconds": s.duration_seconds}
                for s in sessions
            ],
            "total": len(sessions),
        }
    except ImportError:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Recording manager not available", status_code=503)
    except Exception as e:
        logger.error("[Recording] Search error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.get("/recordings/{session_id}/export")
async def export_recording(
    session_id: str,
    format: str = "json",
    user: User = Depends(require_authentication),
):
    """Export recording metadata."""
    try:
        from modules.video.recording_manager import get_manager
        manager = get_manager()
        session = manager.get(session_id)
        if not session or session.user_id != user.id:
            raise HTTPException(status_code=404, detail="Recording not found")
        result = manager.export(session_id, format=format)
        return result
    except ImportError:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Recording manager not available", status_code=503)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[Recording] Export error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.delete("/recordings/{session_id}")
async def delete_recording(
    session_id: str,
    user: User = Depends(require_authentication),
):
    """Delete a recording session."""
    try:
        from modules.video.recording_manager import get_manager
        manager = get_manager()
        session = manager.get(session_id)
        if not session or session.user_id != user.id:
            raise HTTPException(status_code=404, detail="Recording not found")
        manager.delete(session_id)
        return {"status": "deleted", "id": session_id}
    except ImportError:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Recording manager not available", status_code=503)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[Recording] Delete error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)