"""
Route module for the Voice Agent endpoints (Phase 4 unique-to-main).
Voice agent provides real-time voice interaction with VAD, interruption
detection, and AI responses.

Endpoints:
  POST /voice-agent/start
  POST /voice-agent/stop
  GET  /voice-agent/status
  WS   /ws/voice-agent
"""
import base64
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, WebSocket

from security import ErrorCode, error_response
from security.auth import User
from security import get_current_user

# Local require_authentication (mirrors routes/auth.py pattern)
import os
from fastapi import status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends as _Depends

_security_bearer = HTTPBearer(auto_error=False)
_AUTH_REQUIRED = os.getenv("AUTH_REQUIRED", "true").lower() == "true"


async def get_token_from_request(credentials: HTTPAuthorizationCredentials = _Depends(_security_bearer)) -> str:
    if credentials:
        return credentials.credentials
    return None


async def require_authentication(token: str = _Depends(get_token_from_request)):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = get_current_user(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

logger = logging.getLogger("routes.voice_agent")

router = APIRouter()

# Voice agent module — may be missing in some deployments
try:
    from modules.voice.voice_agent import (
        VoiceAgent, create_session, process_audio_chunk,
        end_session, get_status,
    )
    VOICE_AGENT_AVAILABLE = True
except ImportError as e:
    VOICE_AGENT_AVAILABLE = False
    logger.warning("[VoiceAgent] Module not available: %s", str(e))


@router.post("/voice-agent/start")
async def voice_agent_start(user: User = Depends(require_authentication)):
    """Start a new voice agent session."""
    if not VOICE_AGENT_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Voice agent not available", status_code=503)
    result = await create_session(user.id)
    return result


@router.post("/voice-agent/stop")
async def voice_agent_stop(user: User = Depends(require_authentication)):
    """Stop the current voice agent session."""
    if not VOICE_AGENT_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Voice agent not available", status_code=503)
    result = await end_session("current")
    return result


@router.get("/voice-agent/status")
async def voice_agent_status():
    """Get voice agent availability status."""
    if not VOICE_AGENT_AVAILABLE:
        return {"available": False, "error": "Voice agent module not installed"}
    return get_status()


@router.websocket("/ws/voice-agent")
async def ws_voice_agent(ws: WebSocket):
    """
    T17: Real-time voice agent WebSocket.
    Receives audio chunks, returns VAD + AI response actions.
    """
    token = ws.query_params.get("token")
    if _AUTH_REQUIRED:
        if not token:
            await ws.accept()
            await ws.send_text(json.dumps({"error": {"code": "AUTH_REQUIRED", "message": "Authentication required. Pass ?token=xxx in WebSocket URL."}}))
            await ws.close(code=4001)
            return
        user = get_current_user(token)
        if not user:
            await ws.accept()
            await ws.send_text(json.dumps({"error": {"code": "INVALID_TOKEN", "message": "Invalid authentication token"}}))
            await ws.close(code=4001)
            return

    await ws.accept()

    if not VOICE_AGENT_AVAILABLE:
        await ws.send_text(json.dumps({"error": {"code": "MODULE_NOT_AVAILABLE", "message": "Voice agent module not installed"}}))
        await ws.close(code=4002)
        return

    agent = VoiceAgent()
    await agent.start_session(user.id if 'user' in dir() else "anonymous")

    try:
        while True:
            message = await ws.receive_text()
            try:
                data = json.loads(message)
                msg_type = data.get("type", "audio")

                if msg_type == "audio":
                    audio_b64 = data.get("audio", "")
                    audio_bytes = base64.b64decode(audio_b64) if audio_b64 else b""
                    result = await agent.process_audio(audio_bytes)
                    await ws.send_text(json.dumps(result))

                elif msg_type == "config":
                    config_updates = data.get("config", {})
                    for key, value in config_updates.items():
                        if hasattr(agent.config, key):
                            setattr(agent.config, key, value)
                    await ws.send_text(json.dumps({
                        "action": "config_updated",
                        "config": {
                            "voice": agent.config.voice,
                            "enable_interruption": agent.config.enable_interruption,
                        }
                    }))

                elif msg_type == "speak":
                    text = data.get("text", "")
                    success = await agent.speak_text(text)
                    await ws.send_text(json.dumps({"action": "speak_result", "success": success}))

                elif msg_type == "ping":
                    await ws.send_text(json.dumps({"action": "pong"}))

                else:
                    await ws.send_text(json.dumps({"action": "unknown_type", "received_type": msg_type}))

            except Exception as e:
                logger.error("[WS VoiceAgent] Error: %s", str(e))
                await ws.send_text(json.dumps({"error": "An internal error occurred"}))

    except Exception:
        pass
    finally:
        await agent.end_session()
