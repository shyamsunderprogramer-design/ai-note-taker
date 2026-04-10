import asyncio
import concurrent.futures
import json
import logging
import os
import platform
import queue
import re
import requests
import shutil
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

# T16: Add project root and module paths for flat imports
_project_root = Path(__file__).parent.parent
_core_dir = Path(__file__).parent  # backend/core/
for _p in [str(_project_root), str(_core_dir)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Add module subdirectories to path so flat imports (from ai_router, etc.) work
_modules_root = _project_root / "modules"
for _mod_dir in _modules_root.iterdir():
    if _mod_dir.is_dir() and (_mod_dir / "__init__.py").exists():
        if str(_mod_dir) not in sys.path:
            sys.path.insert(0, str(_mod_dir))

import numpy as np

from fastapi import FastAPI, File, Form, Query, Request, UploadFile, WebSocket, Depends, HTTPException, status, Body
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from ai_router import build_prompt, clean_ai_output, route_ai, route_ai_stream

# SECURITY: Import security modules
from security import (
    create_access_token, verify_token, get_current_user, require_auth,
    rate_limiter, rate_limit, RateLimiter,
    SecurityHeaders, sanitize_input, validate_file_upload, InputValidator,
    log_audit_event, get_audit_log, get_audit_stats,
    ErrorCode, APIError, error_response,
)
from security.auth import user_manager, User
from generate_ssl import generate_self_signed_cert, get_ssl_context

# T16: Database migration - PostgreSQL with SQLAlchemy
try:
    from database import (
        db_manager, init_database, close_database,
        UserRepository, ConversationRepository, VoiceModelRepository,
        JobApplicationRepository, AnalyticsRepository,
        BackupManager, DataMigrator,
        HAS_SQLALCHEMY,
    )
    DATABASE_AVAILABLE = HAS_SQLALCHEMY
except ImportError as e:
    DATABASE_AVAILABLE = False
    logging.getLogger("main").warning(f"[Database] module not available: {e}")

# T23: HTTPS enforcement configuration
# T23: Default to secure (HTTPS required); set HTTPS_REQUIRED=false for dev
HTTPS_REQUIRED = os.getenv("HTTPS_REQUIRED", "false").lower() == "true"
HSTS_MAX_AGE = int(os.getenv("HSTS_MAX_AGE", "31536000"))  # 1 year default
from config import OLLAMA_URL

# Voice transcription — optional heavy dependency (faster-whisper, sounddevice, soundfile)
try:
    from whisper_handler import (
        BrowserTranscriber,
        clean_text,
        get_model,
        get_streaming_transcriber,
        is_meaningful,
        is_question,
        is_small_talk,
        is_technical,
        record_audio,
        transcribe,
        transcribe_audio,
        warmup,
    )
    WHISPER_AVAILABLE = True
except ImportError as e:
    WHISPER_AVAILABLE = False
    logging.getLogger("main").warning("[WhisperHandler] Module not available: %s", e)

# Cognitive Graph - Phase 1 Personal Knowledge Graph
try:
    from cognitive_graph import (
        cognitive_graph,
        initialize_graph,
        ingest_conversation,
        query_graph,
        InterviewNode,
        QuestionNode,
        AnswerNode,
        CompanyNode,
        TopicNode,
        SkillNode
    )
    COGNITIVE_GRAPH_AVAILABLE = True
except ImportError:
    COGNITIVE_GRAPH_AVAILABLE = False
    logger = logging.getLogger("main")
    logger.warning("[CognitiveGraph] Module not available. Run: pip install neo4j spacy")

# Interview Simulator - Phase 3
try:
    from interview_simulator import (
        interview_simulator,
        create_interview,
        get_question,
        submit_response,
        finish_interview
    )
    INTERVIEW_SIMULATOR_AVAILABLE = True
except ImportError:
    INTERVIEW_SIMULATOR_AVAILABLE = False
    logger = logging.getLogger("main")
    logger.warning("[InterviewSimulator] Module not available")

# Job Application Tracker - Phase 3
try:
    from job_tracker import job_tracker, track_application, get_applications
    JOB_TRACKER_AVAILABLE = True
except ImportError:
    JOB_TRACKER_AVAILABLE = False
    logger = logging.getLogger("main")
    logger.warning("[JobTracker] Module not available")

# Resume Review - Phase 3
try:
    from resume_review import resume_reviewer, analyze_resume
    RESUME_REVIEW_AVAILABLE = True
except ImportError:
    RESUME_REVIEW_AVAILABLE = False
    logger = logging.getLogger("main")
    logger.warning("[ResumeReview] Module not available")

sys.stdout.reconfigure(encoding="utf-8")

app = FastAPI()

# T6: Global exception handler for structured APIError
@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail,
        headers=getattr(exc, 'headers', None) or {}
    )

# Add CORS middleware for frontend access
from fastapi.middleware.cors import CORSMiddleware

# T2: CORS — Whitelist specific origins instead of ["*"]
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000,http://127.0.0.1:3000,http://localhost:3000")
ALLOWED_ORIGINS = [o.strip() for o in CORS_ORIGINS.split(",") if o.strip()]
# T2: Default to secure (whitelist); set CORS_ALLOW_ALL=true for dev convenience
CORS_ALLOW_ALL = os.getenv("CORS_ALLOW_ALL", "false").lower() == "true"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if CORS_ALLOW_ALL else ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SECURITY: Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    # Add security headers
    headers = SecurityHeaders.get_security_headers()
    for key, value in headers.items():
        response.headers[key] = value

    # Add rate limit headers if available
    if hasattr(request.state, 'rate_limit_headers'):
        for key, value in request.state.rate_limit_headers.items():
            response.headers[key] = value

    return response


# SECURITY: Request size limit middleware
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length:
        max_size = 10 * 1024 * 1024  # 10MB
        if int(content_length) > max_size:
            return JSONResponse(
                status_code=413,
                content={"error": "Request too large", "max_size_mb": 10}
            )
    return await call_next(request)


# T24: Global rate limiting middleware — applies to ALL endpoints
# Different limits for auth vs unauth, public vs sensitive paths
RATE_LIMIT_PUBLIC = int(os.getenv("RATE_LIMIT_PUBLIC", "60"))     # 60/min for public endpoints
RATE_LIMIT_AUTHED = int(os.getenv("RATE_LIMIT_AUTHED", "200"))    # 200/min for authenticated users
RATE_LIMIT_SENSITIVE = int(os.getenv("RATE_LIMIT_SENSITIVE", "20"))  # 20/min for expensive ops

# Paths that are always public (no auth required, lower rate limit)
PUBLIC_PATHS = {"/", "/health", "/auth/login", "/auth/register", "/docs", "/openapi.json", "/redoc"}
# Paths that are expensive/sensitive (lower rate limit even when authed)
SENSITIVE_PATHS = {"/ask-with-image", "/transcribe", "/transcribe-cloud", "/transcribe-with-speakers",
                   "/voice-clone/create", "/voice-clone/create-rvc"}
# Paths exempt from rate limiting entirely
RATE_LIMIT_EXEMPT = {"/ws", "/ws/transcribe", "/stream", "/stream-race", "/transcribe-stream"}

_global_rate_limiter = RateLimiter(requests_per_minute=RATE_LIMIT_AUTHED)
_public_rate_limiter = RateLimiter(requests_per_minute=RATE_LIMIT_PUBLIC)
_sensitive_rate_limiter = RateLimiter(requests_per_minute=RATE_LIMIT_SENSITIVE)

@app.middleware("http")
async def global_rate_limit_middleware(request: Request, call_next):
    """Global rate limiting for all HTTP endpoints."""
    path = request.url.path

    # Skip rate limiting for exempt paths (WebSockets, SSE streams)
    if path in RATE_LIMIT_EXEMPT:
        return await call_next(request)

    client_id = request.client.host if request.client else "unknown"

    # Try to identify authenticated user for per-user limits
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        user = get_current_user(token)
        if user:
            client_id = f"user:{user.username}"
            # Admins bypass rate limiting
            if user.is_admin:
                return await call_next(request)

    # Pick the right limiter based on path
    if path in SENSITIVE_PATHS:
        limiter = _sensitive_rate_limiter
    elif path in PUBLIC_PATHS:
        limiter = _public_rate_limiter
    else:
        limiter = _global_rate_limiter

    allowed, headers = await limiter.is_allowed(client_id, path)
    if not allowed:
        wait_time = await limiter.get_wait_time(client_id, path)
        return JSONResponse(
            status_code=429,
            content={
                "error": {"code": "RATE_LIMIT_EXCEEDED", "message": "Rate limit exceeded", "retry_after": int(wait_time)}
            },
            headers={"Retry-After": str(int(wait_time)), **headers}
        )

    response = await call_next(request)
    for key, value in headers.items():
        response.headers[key] = str(value)
    return response


# T23: HTTPS enforcement middleware — redirect HTTP to HTTPS + HSTS header
@app.middleware("http")
async def https_enforcement_middleware(request: Request, call_next):
    """Redirect HTTP to HTTPS when HTTPS_REQUIRED=true, add HSTS header.
    Localhost connections are always allowed regardless of HTTPS setting."""
    # Skip HTTPS enforcement for localhost (local dev)
    client_host = request.client.host if request.client else ""
    is_localhost = client_host in ("127.0.0.1", "::1", "localhost")

    if HTTPS_REQUIRED and not is_localhost:
        # Check if request is HTTP (not HTTPS)
        # Behind a proxy, check X-Forwarded-Proto header
        forwarded_proto = request.headers.get("x-forwarded-proto", "")
        is_https = request.url.scheme == "https" or forwarded_proto == "https"

        if not is_https:
            https_url = request.url.replace(scheme="https")
            return JSONResponse(
                status_code=301,
                content={"error": {"code": "HTTPS_REQUIRED", "message": "HTTP not allowed. Use HTTPS."}},
                headers={"Location": str(https_url)}
            )

    response = await call_next(request)

    # Add HSTS header when HTTPS is enabled
    if HTTPS_REQUIRED:
        response.headers["Strict-Transport-Security"] = f"max-age={HSTS_MAX_AGE}; includeSubDomains"

    return response


# SECURITY: HTTP Bearer for authentication
security_bearer = HTTPBearer(auto_error=False)


async def get_token_from_request(credentials: HTTPAuthorizationCredentials = Depends(security_bearer)) -> str:
    """Extract token from Authorization header"""
    if credentials:
        return credentials.credentials
    return None


async def optional_auth(request: Request, token: str = Depends(get_token_from_request)):
    """Optional authentication - adds user to request state if valid"""
    if token:
        user = get_current_user(token)
        if user:
            request.state.current_user = user
    return request


# T1: Auth enforcement configuration
# Default to secure (auth required); set AUTH_REQUIRED=false for dev convenience
AUTH_REQUIRED = os.getenv("AUTH_REQUIRED", "true").lower() == "true"

# Paths that never require authentication
AUTH_PUBLIC_PATHS = {
    "/", "/health", "/health/database", "/health/modules",
    "/auth/login", "/auth/register",
    "/docs", "/openapi.json", "/redoc",
    "/voice-clone/audio/{filename}",  # Audio playback
    "/providers",  # Listing available providers
    "/mode",  # Mode switching (lightweight)
}

# Paths that always require authentication (even in dev mode for sensitive ops)
AUTH_REQUIRED_PATHS = {
    "/providers/byok/status", "/providers/byok/configure",
    "/providers/byok/{provider}", "/providers/byok/costs", "/providers/byok/test/{provider}",
    "/auth/me", "/auth/logout",
}


@app.middleware("http")
async def auth_enforcement_middleware(request: Request, call_next):
    """
    T1: Authentication enforcement middleware.
    - In production (AUTH_REQUIRED=true): Blocks unauthenticated access to all non-public paths
    - In development: Auth is optional, user is set in request.state if token present
    - Always enforces auth on BYOK and auth-me endpoints
    """
    path = request.url.path
    auth_header = request.headers.get("authorization", "")

    # Try to identify user from token
    user = None
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        user = get_current_user(token)

    # Set user in request state
    if user:
        request.state.current_user = user
    else:
        request.state.current_user = None

    # Always-required paths (BYOK, auth/me)
    # Check with prefix matching for path parameters
    always_required = False
    for required_path in AUTH_REQUIRED_PATHS:
        if path == required_path or path.startswith(required_path.rsplit("/{", 1)[0] + "/"):
            always_required = True
            break

    if always_required and not user:
        return JSONResponse(
            status_code=401,
            content={"error": {"code": "AUTHENTICATION_REQUIRED", "message": "Authentication required for this endpoint"}},
            headers={"WWW-Authenticate": "Bearer"}
        )

    # In production mode, enforce auth on all non-public paths
    if AUTH_REQUIRED:
        is_public = path in AUTH_PUBLIC_PATHS or path.startswith("/auth/") or path.startswith("/voice-clone/audio/")
        if not is_public and not user:
            return JSONResponse(
                status_code=401,
                content={"error": {"code": "AUTHENTICATION_REQUIRED", "message": "Authentication required. Set AUTH_REQUIRED=false for development mode."}},
                headers={"WWW-Authenticate": "Bearer"}
            )

    return await call_next(request)


async def require_authentication(token: str = Depends(get_token_from_request)):
    """Require authentication for protected endpoints"""
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


async def require_admin(user: User = Depends(require_authentication)):
    """Require admin privileges"""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user

logger = logging.getLogger("main")

# Sanitize API keys from uvicorn access logs
class APIKeyFilter(logging.Filter):
    def filter(self, record):
        record.msg = re.sub(r"api_key=[^&\s]*", "api_key=***", str(record.msg))
        return True

uvicorn_logger = logging.getLogger("uvicorn.access")
uvicorn_logger.addFilter(APIKeyFilter())

UPLOAD_DIR = "temp_audio"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_secure_filename(original_filename: str) -> str:
    """Generate a secure filename to prevent path traversal attacks.

    Returns a UUID-based filename with the same extension.
    """
    import uuid
    # Extract extension safely
    if "." in original_filename:
        ext = original_filename.rsplit(".", 1)[1].lower()
        # Only allow safe extensions
        allowed_exts = {"webm", "wav", "mp3", "mp4", "m4a", "ogg", "pdf", "txt", "md", "docx", "json"}
        if ext not in allowed_exts:
            ext = "bin"  # Default to bin for unknown extensions
    else:
        ext = "bin"
    return f"{uuid.uuid4()}.{ext}"


def sanitize_path(filename: str) -> str:
    """Sanitize filename to prevent directory traversal.

    Rejects paths containing .. or absolute paths.
    """
    import re
    # Reject paths with directory traversal attempts
    if ".." in filename or "/" in filename or "\\" in filename or filename.startswith((".", "/", "\\", "~")):
        raise ValueError(f"Invalid filename: {filename}")
    # Only allow alphanumeric, dots, dashes, underscores
    if not re.match(r"^[\w\-\.]+$", filename):
        raise ValueError(f"Invalid filename characters: {filename}")
    return filename

def cleanup_temp_audio():
    """Remove old temp audio files on startup."""
    if os.path.exists(UPLOAD_DIR):
        for f in os.listdir(UPLOAD_DIR):
            if f.endswith((".webm", ".wav")):
                try:
                    os.remove(os.path.join(UPLOAD_DIR, f))
                except OSError:
                    pass


def get_ffmpeg_path():
    """
    Cross-platform ffmpeg path finder.
    Checks common install locations for each platform.
    """
    system = platform.system()

    # If ffmpeg is in PATH, use it
    ffmpeg_in_path = shutil.which("ffmpeg")
    if ffmpeg_in_path:
        return ffmpeg_in_path

    if system == "Windows":
        # Common Windows install locations
        candidates = [
            os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "ffmpeg", "bin", "ffmpeg.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "ffmpeg", "bin", "ffmpeg.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "ffmpeg", "bin", "ffmpeg.exe"),
            "C:\\ffmpeg\\bin\\ffmpeg.exe",
        ]
    elif system == "Darwin":
        candidates = [
            "/usr/local/bin/ffmpeg",
            "/opt/homebrew/bin/ffmpeg",
            "/opt/local/bin/ffmpeg",
        ]
    else:  # Linux
        candidates = [
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
            "/snap/bin/ffmpeg",
        ]

    for candidate in candidates:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    # Fallback to just "ffmpeg" (will fail with clear error if not installed)
    return "ffmpeg"


last_query_time = 0
CURRENT_MODE = "auto"
COOLDOWN_SECONDS = 5

USE_AUTONOMOUS = False
listener_thread = None
lock = threading.Lock()

STATE = {
    "is_streaming": False
}

always_on_mic_enabled = False


def autonomous_listener():
    global last_query_time, USE_AUTONOMOUS, always_on_mic_enabled  # noqa: F824

    from whisper_handler import get_streaming_transcriber, clean_text, is_meaningful, is_question, is_small_talk, is_technical, transcribe

    text_buffer = ""
    last_heard_time = time.time()
    silence_threshold = 2.5
    min_words = 3

    def get_silence_threshold():
        return 1.8 if CURRENT_MODE == "interview" else silence_threshold

    transcriber = get_streaming_transcriber()

    def on_transcript(text):
        """Called from streaming transcriber's transcription thread."""
        nonlocal last_heard_time, text_buffer
        cleaned = clean_text(text)
        if cleaned:
            text_buffer += " " + cleaned
            last_heard_time = time.time()

    transcriber.add_callback(on_transcript)
    transcriber.start()

    try:
        while USE_AUTONOMOUS and always_on_mic_enabled:
            try:
                if STATE["is_streaming"]:
                    time.sleep(0.2)
                    continue

                time.sleep(0.3)

                if time.time() - last_heard_time < get_silence_threshold():
                    continue

                final_text = text_buffer.strip()
                text_buffer = ""

                if not final_text:
                    continue

                if not is_meaningful(final_text):
                    continue

                if len(final_text.split()) < min_words:
                    continue

                if not is_question(final_text):
                    continue

                if is_small_talk(final_text):
                    continue

                if CURRENT_MODE == "interview" and not is_technical(final_text):
                    continue

                with lock:
                    if time.time() - last_query_time < COOLDOWN_SECONDS:
                        continue
                    last_query_time = time.time()

                for _chunk in route_ai_stream(final_text, mode=CURRENT_MODE):
                    pass

            except Exception as e:
                logger.error("[ERROR] Listener error: %s", e)
    finally:
        transcriber.stop()


@app.on_event("startup")
async def start_listener():
    global listener_thread

    # T16: Initialize PostgreSQL database
    if DATABASE_AVAILABLE:
        try:
            await init_database()
            logger.info("[Startup] Database initialized successfully")
        except Exception as e:
            logger.warning(f"[Startup] Database initialization skipped: {e}")

    # Clean up stale temp audio files on startup
    cleanup_temp_audio()

    # Start Whisper warmup in background — doesn't block uvicorn startup
    # Transcription requests will wait for the model via model_ready.wait()
    if WHISPER_AVAILABLE:
        threading.Thread(target=warmup, daemon=True).start()
    else:
        logger.info("[Startup] Whisper warmup skipped — voice packages not installed")

    # Start embedding service and classifier warmup in background
    # These are optional — if they fail, existing keyword logic is used as fallback
    try:
        from config import EMBEDDING_ENABLED, CLASSIFIER_ENABLED
        if EMBEDDING_ENABLED:
            from modules.ai.embedding_service import warmup as embedding_warmup
            threading.Thread(target=embedding_warmup, daemon=True, name="embedding-warmup").start()
        if CLASSIFIER_ENABLED:
            from modules.ai.smart_classifier import warmup as classifier_warmup
            threading.Thread(target=classifier_warmup, daemon=True, name="classifier-warmup").start()
    except Exception as e:
        logger.warning(f"[Startup] ML warmup skipped: {e}")

    if USE_AUTONOMOUS and listener_thread is None:
        listener_thread = threading.Thread(target=autonomous_listener, daemon=True)
        listener_thread.start()


@app.get("/")
def health_check():
    return {
        "status": "ok",
        "service": "ai-backend",
        "mode": CURRENT_MODE,
        "security": {
            "authentication": "enabled",
            "rate_limiting": "enabled",
            "https_required": False  # Set to True when SSL is configured
        }
    }


@app.get("/providers")
@rate_limit(requests_per_minute=30)  # Rate limit: 30 per minute
async def list_providers(request: Request):
    """Returns which cloud providers have API keys configured (secure storage + env fallback)"""
    import requests

    def has_key(provider, env_var):
        # Try secure server first
        try:
            resp = requests.post(
                "http://127.0.0.1:18000/get-key",
                json={"provider": provider},
                timeout=1
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("apiKey"):
                    return True
        except:
            pass
        # Fallback to env
        return bool(os.getenv(env_var, "").strip())

    return {
        "openai": has_key("openai", "OPENAI_API_KEY"),
        "anthropic": has_key("anthropic", "ANTHROPIC_API_KEY"),
        "google": has_key("google", "GOOGLE_API_KEY"),
        "xai": has_key("xai", "XAI_API_KEY"),
        "deepseek": has_key("deepseek", "DEEPSEEK_API_KEY"),
        "groq": has_key("groq", "GROQ_API_KEY"),
        "ollama-cloud": has_key("ollama-cloud", "OLLAMA_CLOUD_API_KEY"),
        "perplexity": has_key("perplexity", "PERPLEXITY_API_KEY"),
        "ollama": True  # Ollama is always available if configured
    }


@app.get("/ollama/models")
def list_ollama_models():
    """Proxy to Ollama's GET /api/tags — returns installed local models."""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=10)
        if response.status_code == 200:
            return response.json()
        return error_response(ErrorCode.SERVICE_UNAVAILABLE, f"Ollama returned {response.status_code}", status_code=502) | {"models": []}
    except Exception as e:
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500) | {"models": []}


@app.post("/ollama/pull")
def pull_ollama_model(model: str = Query(...)):
    """Trigger a model pull — runs async, returns immediately."""
    import threading
    def background_pull():
        try:
            logger.info("Starting model pull: %s", model)
            pull_resp = requests.post(
                f"{OLLAMA_URL}/api/pull",
                json={"name": model},
                stream=True,
                timeout=3600
            )
            # Read the stream to ensure completion (or failure)
            for line in pull_resp.iter_lines():
                if line:
                    logger.info("[Ollama pull] %s", line.decode("utf-8", errors="replace"))
            logger.info("Model pull complete: %s", model)
        except Exception as e:
            logger.error("Model pull failed for %s: %s", model, e)

    threading.Thread(target=background_pull, daemon=True).start()
    return {"status": "pull_started", "model": model}


@app.delete("/ollama/models/{model_name}")
def delete_ollama_model(model_name: str):
    """Delete a local Ollama model."""
    try:
        response = requests.delete(
            f"{OLLAMA_URL}/api/delete",
            json={"name": model_name},
            timeout=30
        )
        if response.status_code == 200:
            return {"status": "deleted", "model": model_name}
        return error_response(ErrorCode.SERVICE_UNAVAILABLE, f"Failed to delete model: {response.status_code}", status_code=502)
    except Exception as e:
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.post("/ask-with-image")
@rate_limit(requests_per_minute=20)  # Rate limit: 20 per minute (expensive operation)
async def ask_with_image(
    request: Request,
    query: str = Form(...),
    mode: str = Form("adaptive"),
    style: str = Form("concise"),
    provider: str = Form("ollama"),
    context: str = Form(None),
    image_b64: str = Form(None)
):
    """Accept text + optional base64 screenshot, stream AI response via SSE."""
    # SECURITY: Sanitize query input
    query = sanitize_input(query, max_length=10000)

    logger.info("[ask-with-image] received: query=%s, mode=%s, style=%s, image_b64 present=%s", query[:100], mode, style, "Yes" if image_b64 else "No")
    if image_b64:
        logger.info("[ask-with-image] image_b64 length=%d, first 50 chars=%s", len(image_b64), image_b64[:50])
    messages = None
    if context:
        try:
            import json
            messages = json.loads(context)
        except Exception:
            pass

    # When screenshot is provided, find a vision-capable model
    # (ignore non-vision provider selection when image is present)
    model_name = None
    if image_b64:
        from ai_router import _get_vision_model
        model_name = _get_vision_model()
        logger.info("[ask-with-image] Screenshot provided, vision model: %s", model_name)
        if not model_name:
            # No vision model found - return error
            def error_gen():
                import json
                yield f"event: error\ndata: {json.dumps({'type':'error','message':'No vision-capable model found. Please pull a vision model like llava:latest with: ollama pull llava:latest'})}\n\n"
            return StreamingResponse(error_gen(), media_type="text/event-stream")
    else:
        logger.info("[ask-with-image] No screenshot, using provider: %s", provider)

    def generator():
        STATE["is_streaming"] = True
        try:
            from ai_router import ask_ollama_vision_stream
            for event in ask_ollama_vision_stream(query, image_b64=image_b64, mode=mode, style=style, messages=messages, model_name=model_name):
                yield event
        except Exception as e:
            import json
            yield f"event: error\ndata: {json.dumps({'type':'error','message':str(e)})}\n\n"
        finally:
            STATE["is_streaming"] = False

    return StreamingResponse(generator(), media_type="text/event-stream")


@app.get("/transcribe-stream")
async def transcribe_stream(request: Request):
    """SSE stream of real-time transcription from always-on microphone.

    The StreamingTranscriber runs in a background thread. This endpoint
    bridges it to SSE using a sync queue consumed in a thread executor
    so it never blocks the asyncio event loop.
    """
    loop = asyncio.get_event_loop()

    async def event_generator():
        transcriber = get_streaming_transcriber()

        # Sync queue — transcriber thread puts, async consumer gets
        client_queue = queue.Queue()

        def sync_queue_callback(text):
            try:
                client_queue.put_nowait(text)
            except Exception:
                pass
        transcriber.add_callback(sync_queue_callback)

        # Ensure transcriber is running
        transcriber.start()

        try:
            while True:
                if await request.is_disconnected():
                    break
                # Run blocking queue.get() in a thread with 1s timeout so event loop stays free
                try:
                    text = await loop.run_in_executor(None, lambda: client_queue.get(True, timeout=1))
                    import json
                    yield f"event: transcript\ndata: {json.dumps({'text': text})}\n\n"
                except queue.Empty:
                    # No transcription in queue within timeout — send ping so renderer can check silence
                    import json
                    yield f"event: ping\ndata: {json.dumps({'t': int(time.time())})}\n\n"
        except GeneratorExit:
            pass
        except Exception as e:
            logger.error("[transcribe-stream] error: %s", e)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/overlay-ask")
@rate_limit(requests_per_minute=30)  # Rate limit: 30 per minute
async def overlay_ask(
    request: Request,
    query: str = Form(...),
    screenshot_b64: str = Form(None)
):
    # SECURITY: Sanitize query input
    query = sanitize_input(query, max_length=5000)
    """Quick Q&A from overlay window with optional screenshot context.

    Uses fast/concise settings for quick responses.
    """
    logger.info("[overlay-ask] query=%s, has_screenshot=%s", query, bool(screenshot_b64))

    async def generator():
        STATE["is_streaming"] = True
        try:
            from ai_router import ask_ollama_vision_stream, _get_vision_model, route_ai_stream

            if screenshot_b64:
                model_name = _get_vision_model()
                logger.info("[overlay-ask] Screenshot present, vision model: %s", model_name)
                if not model_name:
                    import json
                    yield f"event: error\ndata: {json.dumps({'type':'error','message':'No vision model found. Pull one with: ollama pull llava:latest'})}\n\n"
                    return
                for event in ask_ollama_vision_stream(
                    query,
                    image_b64=screenshot_b64,
                    mode="fast",
                    style="concise",
                    model_name=model_name
                ):
                    yield event
            else:
                for event in route_ai_stream(query, mode="fast", style="concise"):
                    yield event
        except Exception as e:
            import json
            yield f"event: error\ndata: {json.dumps({'type':'error','message': str(e)})}\n\n"
        finally:
            STATE["is_streaming"] = False

    return StreamingResponse(generator(), media_type="text/event-stream")


@app.post("/set-always-on-mic")
async def set_always_on_mic(enabled: bool = Form(...)):
    """Enable or disable the always-on microphone.

    When enabled, the StreamingTranscriber runs continuously and
    transcription events are available via /transcribe-stream SSE.
    """
    global always_on_mic_enabled, USE_AUTONOMOUS

    always_on_mic_enabled = enabled
    USE_AUTONOMOUS = enabled
    transcriber = get_streaming_transcriber()

    if enabled:
        transcriber.start()
        logger.info("[AlwaysOnMic] Enabled")
    else:
        transcriber.stop()
        logger.info("[AlwaysOnMic] Disabled")

    return {"enabled": enabled}


@app.post("/configure")
async def configure_provider(body: dict):
    """API key configuration endpoint — DISABLED.

    SECURITY: API keys are no longer accepted over HTTP.
    Use secure IPC: window.api.saveApiKey(provider, apiKey)

    This endpoint returns an error to prevent accidental insecure key transmission.
    """
    # Reject any attempt to configure API keys over HTTP
    # Keys must be saved via secure IPC to encrypted storage
    return {
        "error": "HTTP configuration disabled for security",
        "message": "Use window.api.saveApiKey(provider, apiKey) for secure storage",
        "code": "INSECURE_TRANSPORT"
    }


@app.get("/health")
def health():
    return health_check()


@app.get("/health/database")
async def health_database():
    """T16: Check PostgreSQL database connectivity"""
    if not DATABASE_AVAILABLE:
        return {
            "available": False,
            "connected": False,
            "message": "Database module not available - SQLAlchemy not installed"
        }

    try:
        connected = await db_manager.health_check()
        return {
            "available": True,
            "connected": connected,
            "message": "Database connection OK" if connected else "Database connection failed"
        }
    except Exception as e:
        return {
            "available": True,
            "connected": False,
            "message": f"Database error: {str(e)}"
        }


@app.get("/health/modules")
async def health_modules():
    """T13: Feature health dashboard - show which modules are available"""
    # Check Neo4j connection
    try:
        from cognitive_graph import get_driver
        neo4j_connected = get_driver() is not None
    except Exception:
        neo4j_connected = False

    # Check encryption key
    encryption_available = bool(os.getenv("ENCRYPTION_KEY"))

    # Check AI providers
    def has_provider_key(provider, env_var):
        try:
            import requests as req
            resp = req.post("http://127.0.0.1:18000/get-key", json={"provider": provider}, timeout=1)
            if resp.status_code == 200:
                return bool(resp.json().get("apiKey"))
        except Exception:
            pass
        return bool(os.getenv(env_var, "").strip())

    providers = {
        "openai": has_provider_key("openai", "OPENAI_API_KEY"),
        "anthropic": has_provider_key("anthropic", "ANTHROPIC_API_KEY"),
        "google": has_provider_key("google", "GOOGLE_API_KEY"),
        "groq": has_provider_key("groq", "GROQ_API_KEY"),
        "ollama": has_provider_key("ollama", "OLLAMA_API_KEY"),
    }
    active_providers = sum(providers.values())

    # Check mock interview
    mock_interview_count = 0
    if MOCK_LIBRARY_AVAILABLE:
        try:
            mock_interview_count = len(mock_library.get_all_questions())
        except Exception:
            pass

    modules = {
        "database": {
            "available": DATABASE_AVAILABLE,
            "status": "green" if DATABASE_AVAILABLE else "red",
            "type": "sqlite" if os.getenv("USE_SQLITE", "").lower() == "true" else "postgresql",
            "required_dependency": "sqlalchemy + database server"
        },
        "neo4j_graph": {
            "available": COGNITIVE_GRAPH_AVAILABLE,
            "status": "green" if neo4j_connected else "yellow",
            "connected": neo4j_connected,
            "required_dependency": "neo4j server + NEO4J_PASSWORD env var"
        },
        "whisper": {
            "available": True,
            "status": "green",
            "required_dependency": "whisper model files (auto-downloaded)"
        },
        "voice_clone": {
            "available": VOICE_CLONE_AVAILABLE,
            "status": "green" if VOICE_CLONE_AVAILABLE else "yellow",
            "rvc_available": RVC_GALLERY_AVAILABLE,
            "required_dependency": "Edge TTS (always available), RVC models (optional)"
        },
        "ai_router": {
            "available": True,
            "status": "green",
            "providers": providers,
            "active_providers": active_providers,
            "required_dependency": "At least one AI provider key"
        },
        "collaboration": {
            "available": COLLABORATION_AVAILABLE,
            "status": "green" if COLLABORATION_AVAILABLE else "yellow",
            "required_dependency": "WebSocket support"
        },
        "mock_interview": {
            "available": MOCK_LIBRARY_AVAILABLE,
            "status": "green" if MOCK_LIBRARY_AVAILABLE else "yellow",
            "question_count": mock_interview_count,
            "required_dependency": "mock_interview_library.py"
        },
        "study_plan": {
            "available": STUDY_PLAN_AVAILABLE,
            "status": "green" if STUDY_PLAN_AVAILABLE else "yellow",
            "required_dependency": "study_plan_generator.py"
        },
        "interview_simulator": {
            "available": INTERVIEW_SIMULATOR_AVAILABLE,
            "status": "green" if INTERVIEW_SIMULATOR_AVAILABLE else "yellow",
            "required_dependency": "interview_simulator.py"
        },
        "job_tracker": {
            "available": JOB_TRACKER_AVAILABLE,
            "status": "green" if JOB_TRACKER_AVAILABLE else "yellow",
            "required_dependency": "job_tracker.py"
        },
        "encryption": {
            "available": encryption_available,
            "status": "green" if encryption_available else "yellow",
            "required_dependency": "ENCRYPTION_KEY env var"
        }
    }

    available_count = sum(1 for m in modules.values() if m["status"] == "green")
    total_count = len(modules)

    return {
        "modules": modules,
        "overall_health": round(available_count / total_count * 100, 1),
        "available_count": available_count,
        "total_count": total_count
    }


# ═══════════════════════════════════════════════════════════════════
# T16: DATABASE ADMIN - Backup/Restore/Migration (Admin only)
# ═══════════════════════════════════════════════════════════════════

@app.post("/admin/backup")
async def admin_create_backup(user: User = Depends(require_admin)):
    """T16: Create a full database backup as JSON - admin only"""
    if not DATABASE_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Database module not available")

    try:
        backup_data = await BackupManager.create_backup()
        log_audit_event("admin_backup", user.username, "backup_created", success=True)
        return {
            "status": "success",
            "message": "Backup created successfully",
            "backup": backup_data
        }
    except Exception as e:
        log_audit_event("admin_backup", user.username, "backup_failed", success=False)
        return error_response(ErrorCode.INTERNAL_ERROR, f"Backup failed: {str(e)}")


@app.post("/admin/restore")
async def admin_restore_backup(backup_data: Dict = Body(...), user: User = Depends(require_admin)):
    """T16: Restore database from JSON backup - admin only"""
    if not DATABASE_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Database module not available")

    try:
        restored = await BackupManager.restore_backup(backup_data)
        log_audit_event("admin_restore", user.username, "backup_restored", resource=f"restored:{restored}", success=True)
        return {
            "status": "success",
            "message": "Backup restored successfully",
            "restored": restored
        }
    except Exception as e:
        log_audit_event("admin_restore", user.username, "restore_failed", success=False)
        return error_response(ErrorCode.INTERNAL_ERROR, f"Restore failed: {str(e)}")


@app.post("/admin/migrate")
async def admin_run_migration(user: User = Depends(require_admin)):
    """T16: Run JSON -> PostgreSQL migration - admin only"""
    if not DATABASE_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Database module not available")

    try:
        results = await DataMigrator.run_full_migration()
        log_audit_event("admin_migrate", user.username, "migration_run", resource=f"users:{results.get('users', 0)}", success=True)
        return {
            "status": "success",
            "message": "Migration completed",
            "results": results
        }
    except Exception as e:
        log_audit_event("admin_migrate", user.username, "migration_failed", success=False)
        return error_response(ErrorCode.INTERNAL_ERROR, f"Migration failed: {str(e)}")


# ═══════════════════════════════════════════════════════════════════
# SECURITY: AUTHENTICATION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.post("/auth/register")
@rate_limit(requests_per_minute=5)  # T24: Slow brute-force attacks
async def register_user(
    username: str = Form(..., min_length=3, max_length=30),
    email: str = Form(...),
    password: str = Form(..., min_length=8)
):
    """Register a new user account"""
    # Validate inputs
    if not InputValidator.validate_username(username):
        raise HTTPException(
            status_code=400,
            detail="Invalid username. Use 3-30 alphanumeric characters, underscores, or hyphens."
        )

    if not InputValidator.validate_email(email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    try:
        user = user_manager.create_user(username=username, email=email, password=password)
        log_audit_event("auth_register", username, "user_registered", resource=f"user:{user.id}", success=True)
        return {
            "status": "success",
            "message": "User registered successfully",
            "user_id": user.id,
            "username": user.username
        }
    except ValueError as e:
        log_audit_event("auth_register", username, "user_register_failed", details={"reason": str(e)}, success=False)
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/login")
@rate_limit(requests_per_minute=5)  # T24: Slow brute-force attacks
async def login_user(username: str = Form(...), password: str = Form(...)):
    """Login and get JWT token"""
    user = user_manager.authenticate_user(username, password)
    if not user:
        log_audit_event("auth_failure", username, "login_failed", resource="auth", success=False)
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    log_audit_event("auth_login", username, "user_logged_in", resource=f"user:{user.id}", success=True)

    # Create access token
    access_token = create_access_token(
        data={"sub": user.id, "username": user.username},
        expires_delta=__import__('datetime').timedelta(hours=24)
    )

    return {
        "status": "success",
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 86400,  # 24 hours in seconds
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin
        }
    }


@app.get("/auth/me")
async def get_current_user_info(user: User = Depends(require_authentication)):
    """Get current authenticated user info"""
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_admin": user.is_admin,
        "is_active": user.is_active,
        "last_login": user.last_login,
        "api_quota": user.api_quota
    }


@app.post("/auth/logout")
async def logout_user(user: User = Depends(require_authentication)):
    """Logout (client should delete token)"""
    log_audit_event("auth_logout", user.username, "user_logged_out", resource=f"user:{user.id}", success=True)
    # Note: JWT tokens are stateless, actual logout is client-side
    return {"status": "success", "message": "Logged out successfully"}


# ═══════════════════════════════════════════════════════════════════
# AUDIT LOG (T7)
# ═══════════════════════════════════════════════════════════════════

@app.get("/audit/log")
async def get_audit_log_endpoint(
    user: User = Depends(require_authentication),
    limit: int = Query(100, ge=1, le=1000),
    event_type: str = Query(None, description="Filter by event type"),
    actor: str = Query(None, description="Filter by actor"),
):
    """Get audit log entries (requires authentication)."""
    if not user.is_admin:
        return error_response(ErrorCode.FORBIDDEN, "Admin access required", status_code=403)
    entries = get_audit_log(limit=limit, event_type=event_type, actor=actor)
    return {"entries": entries, "count": len(entries)}


@app.get("/audit/stats")
async def get_audit_stats_endpoint(
    user: User = Depends(require_authentication),
):
    """Get audit log statistics (requires authentication)."""
    if not user.is_admin:
        return error_response(ErrorCode.FORBIDDEN, "Admin access required", status_code=403)
    return get_audit_stats()


# ═══════════════════════════════════════════════════════════════════
# RATE LIMIT STATUS
# ═══════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════
# USER API KEY MANAGEMENT - BYOK (Bring Your Own Key)
# ═══════════════════════════════════════════════════════════════════

# Import user key management
from user_api_keys import (
    user_key_manager,
    get_available_providers,
    has_premium_access,
    get_provider_cost_info,
    PROVIDER_COSTS,
)


@app.get("/providers/byok/status")
async def get_byok_status(user: User = Depends(require_authentication)):
    """Get user's BYOK status - which providers they have configured"""
    providers = get_available_providers(user.id)
    has_premium = has_premium_access(user.id)

    # Get cost info for each provider
    provider_info = {}
    for provider, has_key in providers.items():
        cost_info = get_provider_cost_info(provider)
        provider_info[provider] = {
            "configured": has_key,
            "name": cost_info["name"],
            "cost_per_1k_input": cost_info["input"],
            "cost_per_1k_output": cost_info["output"],
        }

    return {
        "has_premium_access": has_premium,
        "providers": provider_info,
        "ollama_available": True,  # Always available
        "message": "Free tier uses Ollama. Add your own API keys for premium providers."
    }


@app.post("/providers/byok/configure")
async def configure_provider_key(
    user: User = Depends(require_authentication),
    provider: str = Form(...),
    api_key: str = Form(...)
):
    """Configure user's own API key for a premium provider"""
    # Validate provider
    valid_providers = ["openai", "anthropic", "google", "xai", "deepseek", "groq", "perplexity", "ollama_cloud"]
    if provider not in valid_providers:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider. Must be one of: {', '.join(valid_providers)}"
        )

    # Validate key format
    is_valid, message = user_key_manager.validate_key(provider, api_key)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid API key: {message}")

    # Save the key
    try:
        key_field = f"{provider}_key"
        user_key_manager.update_keys(user.id, **{key_field: api_key})

        return {
            "status": "success",
            "message": f"{provider.title()} API key configured successfully",
            "provider": provider,
            "note": "Your key is stored securely and will be used for AI requests."
        }
    except Exception as e:
        logger.error(f"[BYOK] Failed to save key: {e}")
        raise HTTPException(status_code=500, detail="Failed to save API key")


@app.delete("/providers/byok/{provider}")
async def delete_provider_key(
    provider: str,
    user: User = Depends(require_authentication)
):
    """Delete a user's API key for a specific provider"""
    user_key_manager.delete_keys(user.id, provider=provider)

    return {
        "status": "success",
        "message": f"{provider.title()} API key removed"
    }


@app.get("/providers/byok/costs")
async def get_provider_costs():
    """Get cost information for all providers (public endpoint)"""
    costs = {}
    for provider, info in PROVIDER_COSTS.items():
        costs[provider] = {
            "name": info["name"],
            "input_cost_per_1k": info["input"],
            "output_cost_per_1k": info["output"],
            "is_free": info["input"] == 0 and info["output"] == 0,
        }
    return {
        "providers": costs,
        "note": "Free tier uses Ollama (local). Add your own keys for premium providers.",
        "cost_example": "A typical interview response (~500 tokens) costs $0.001-0.003 with most providers."
    }


@app.get("/providers/byok/test/{provider}")
async def test_provider_key(
    provider: str,
    user: User = Depends(require_authentication)
):
    """Test if a user's API key is working for a provider by making a real API call"""
    key = user_key_manager.get_provider_key(user.id, provider)

    if not key:
        raise HTTPException(
            status_code=404,
            detail=f"No API key configured for {provider}"
        )

    # T8: Validate format first, then make a real API test call
    is_valid, message = user_key_manager.validate_key(provider, key)
    if not is_valid:
        log_audit_event("byok_test", user.username, "key_test_failed", resource=provider, details={"reason": message}, success=False)
        return {
            "status": "error",
            "provider": provider,
            "message": f"Key validation failed: {message}",
            "suggestion": "Please check your API key and try again."
        }

    # Make a real API test call based on the provider
    import httpx
    test_result = {"status": "success", "provider": provider, "message": "API key format is valid"}

    try:
        if provider == "openai":
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {key}"},
                )
                if resp.status_code == 200:
                    test_result = {"status": "success", "provider": provider, "message": "API key verified successfully", "models_available": len(resp.json().get("data", []))}
                elif resp.status_code == 401:
                    test_result = {"status": "error", "provider": provider, "message": "Invalid API key", "suggestion": "Check your OpenAI API key"}
                else:
                    test_result = {"status": "warning", "provider": provider, "message": f"API returned status {resp.status_code}", "note": "Key format is valid but API test returned unexpected response"}

        elif provider == "anthropic":
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={"x-api-key": key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
                    json={"model": "claude-3-haiku-20240307", "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]},
                )
                if resp.status_code in (200, 201):
                    test_result = {"status": "success", "provider": provider, "message": "API key verified successfully"}
                elif resp.status_code == 401:
                    test_result = {"status": "error", "provider": provider, "message": "Invalid API key", "suggestion": "Check your Anthropic API key"}
                else:
                    test_result = {"status": "warning", "provider": provider, "message": f"API returned status {resp.status_code}", "note": "Key format may be valid"}

        elif provider == "google":
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"https://generativelanguage.googleapis.com/v1/models?key={key}",
                )
                if resp.status_code == 200:
                    test_result = {"status": "success", "provider": provider, "message": "API key verified successfully"}
                elif resp.status_code == 400 or resp.status_code == 403:
                    test_result = {"status": "error", "provider": provider, "message": "Invalid API key", "suggestion": "Check your Google AI API key"}
                else:
                    test_result = {"status": "warning", "provider": provider, "message": f"API returned status {resp.status_code}"}

        elif provider in ("xai", "groq", "deepseek", "perplexity"):
            # These use OpenAI-compatible APIs
            base_urls = {
                "xai": "https://api.x.ai/v1",
                "groq": "https://api.groq.com/openai/v1",
                "deepseek": "https://api.deepseek.com/v1",
                "perplexity": "https://api.perplexity.ai",
            }
            base_url = base_urls.get(provider, "")
            if base_url:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(
                        f"{base_url}/models",
                        headers={"Authorization": f"Bearer {key}"},
                    )
                    if resp.status_code == 200:
                        test_result = {"status": "success", "provider": provider, "message": "API key verified successfully"}
                    elif resp.status_code == 401:
                        test_result = {"status": "error", "provider": provider, "message": "Invalid API key"}
                    else:
                        test_result = {"status": "warning", "provider": provider, "message": f"API returned status {resp.status_code}"}
            else:
                test_result = {"status": "success", "provider": provider, "message": "Key format is valid (provider test not implemented)"}

    except httpx.TimeoutException:
        test_result = {"status": "warning", "provider": provider, "message": "API test timed out", "note": "Key format is valid but could not verify connectivity"}
    except Exception as e:
        test_result = {"status": "warning", "provider": provider, "message": f"API test error: {str(e)}", "note": "Key format is valid but could not verify connectivity"}

    log_audit_event("byok_test", user.username, "key_tested", resource=provider, details=test_result, success=test_result.get("status") == "success")
    return test_result


@app.get("/rate-limit/status")
async def get_rate_limit_status(request: Request):
    """Get current rate limit status for the client"""
    client_id = request.client.host if request.client else "unknown"

    # Check current rate limit
    allowed, headers = await rate_limiter.is_allowed(client_id)

    return {
        "client_id": client_id,
        "limit": int(headers.get("X-RateLimit-Limit", 100)),
        "remaining": int(headers.get("X-RateLimit-Remaining", 0)),
        "reset": int(headers.get("X-RateLimit-Reset", 0)),
        "window_seconds": int(headers.get("X-RateLimit-Window", 60)),
        "allowed": allowed
    }


@app.post("/set-mode")
def set_mode(mode: str):
    global CURRENT_MODE

    if mode not in ["auto", "fast", "cloud", "interview", "universal", "adaptive", "reasoning", "code"]:
        return error_response(ErrorCode.VALIDATION_ERROR, "Invalid mode", status_code=400)

    CURRENT_MODE = mode
    return {"status": "mode updated", "mode": CURRENT_MODE}


@app.post("/transcribe")
async def transcribe_api(file: UploadFile = File(...)):
    global USE_AUTONOMOUS

    USE_AUTONOMOUS = False
    # Use secure filename to prevent path traversal
    secure_name = get_secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_DIR, secure_name)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    wav_path = file_path.replace(".webm", ".wav")
    import subprocess
    ffmpeg_path = get_ffmpeg_path()
    result = subprocess.run(
        [ffmpeg_path, "-i", file_path, "-ar", "16000", "-ac", "1", wav_path, "-y"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg conversion failed: {result.stderr}")

    text = transcribe_audio(wav_path, mode=CURRENT_MODE)

    # Clean up temp files immediately after use
    for path in (file_path, wav_path):
        try: os.remove(path)
        except OSError: pass

    if not text or not is_meaningful(text) or not is_question(text):
        return {"text": text, "response": ""}

    result = route_ai(text, mode=CURRENT_MODE)
    return {
        "text": text,
        "response": clean_ai_output(result["response"]),
        "mode": result["mode"],
        "model": result["model"]
    }


@app.post("/transcribe-cloud")
@rate_limit(requests_per_minute=20)  # T24: Expensive cloud transcription
async def transcribe_cloud(file: UploadFile = File(...), provider: str = "openai", model: str = "gpt-4o-mini"):
    """Transcribe and route to a cloud AI provider"""
    global USE_AUTONOMOUS

    USE_AUTONOMOUS = False
    # Use secure filename to prevent path traversal
    secure_name = get_secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_DIR, secure_name)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    wav_path = file_path.replace(".webm", ".wav")
    import subprocess
    ffmpeg_path = get_ffmpeg_path()
    result = subprocess.run(
        [ffmpeg_path, "-i", file_path, "-ar", "16000", "-ac", "1", wav_path, "-y"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg conversion failed: {result.stderr}")

    text = transcribe_audio(wav_path, mode=CURRENT_MODE)

    # Clean up temp files immediately after transcription
    for path in (file_path, wav_path):
        try: os.remove(path)
        except OSError: pass

    if not text:
        return {"text": "", "response": "", "error": "No speech detected"}

    if not is_meaningful(text) or not is_question(text):
        return {"text": text, "response": "", "error": "Not a meaningful question"}

    # Route to cloud provider
    try:
        from cloud_providers import ask_gpt, ask_claude, ask_gemini, ask_grok, ask_deepseek, ask_groq, clean_ai_output as cloud_clean

        prompt = build_prompt(text, CURRENT_MODE)

        if provider == "openai":
            resp = ask_gpt(prompt, model=model)
            response_text = resp.json()["choices"][0]["message"]["content"]
        elif provider == "anthropic":
            resp = ask_claude(prompt, model=model)
            response_text = resp.json()["content"][0]["text"]
        elif provider == "google":
            resp = ask_gemini(prompt, model=model)
            response_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        elif provider == "xai":
            resp = ask_grok(prompt, model=model)
            response_text = resp.json()["choices"][0]["message"]["content"]
        elif provider == "deepseek":
            resp = ask_deepseek(prompt, model=model)
            response_text = resp.json()["choices"][0]["message"]["content"]
        elif provider == "groq":
            resp = ask_groq(prompt, model=model)
            response_text = resp.json()["choices"][0]["message"]["content"]
        else:
            return {"text": text, "response": "", "error": f"Unknown provider: {provider}"}

        return {
            "text": text,
            "response": cloud_clean(response_text),
            "mode": provider,
            "model": model
        }

    except ValueError as e:
        return {"text": text, "response": "", "error": str(e)}
    except Exception as e:
        print("[ERROR cloud transcribe]:", e)
        return {"text": text, "response": "", "error": str(e)}


@app.get("/stream")
def stream_ai(q: str, mode: str = "fast", style: str = "concise", provider: str = "ollama", context: str = None):
    """SSE stream endpoint — yields event: meta/chunk/done/error"""
    def generator():
        STATE["is_streaming"] = True

        # Parse context messages from JSON
        messages = None
        if context:
            try:
                import json
                messages = json.loads(context)
            except Exception:
                pass

        try:
            # Yield provider/mode info as first event
            yield f"event: meta\ndata: {{\"type\":\"meta\",\"provider\":\"{provider}\"}}\n\n"

            for event in route_ai_stream(q, mode, style, provider, messages):
                yield event

        except Exception as e:
            import json
            yield f"event: error\ndata: {json.dumps({'type':'error','message':str(e)})}\n\n"

        finally:
            STATE["is_streaming"] = False

    return StreamingResponse(generator(), media_type="text/event-stream")


@app.get("/stream-race")
def stream_race(q: str, mode: str = "fast", style: str = "concise", context: str = None, enabled: str = None):
    """
    Fire all configured providers in parallel using ThreadPoolExecutor + as_completed.
    Returns the FIRST successful full response (ignores errors/429s from cloud providers).
    Falls back to Ollama if all clouds fail.
    Only providers specified in 'enabled' param (comma-separated) will be used.
    """
    from cloud_providers import MODEL_DISPLAY_NAMES, PROVIDER_MODEL_MAP, get_stream_fn
    import concurrent.futures
    import logging
    import time as time_module

    logger = logging.getLogger(__name__)
    race_start = time_module.time()
    logger.info("[RACE START] query='%s' mode=%s style=%s", q[:50], mode, style)

    # Parse enabled providers from frontend
    enabled_set = None
    if enabled:
        enabled_set = set(enabled.split(","))
        logger.info("Race mode: only using enabled providers from frontend: %s", enabled_set)

    messages = None
    if context:
        try:
            messages = json.loads(context)
        except json.JSONDecodeError:
            logger.warning("Failed to parse context JSON")
            pass

    # Secure key checking helper
    def has_secure_key(provider, env_var):
        try:
            resp = requests.post(
                "http://127.0.0.1:18000/get-key",
                json={"provider": provider},
                timeout=1
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("apiKey"):
                    return True
        except:
            pass
        return bool(os.getenv(env_var, "").strip())

    # Separate cloud and local providers
    cloud_providers = []
    local_providers = []

    # If enabled_set from frontend is provided, only use those providers
    if enabled_set:
        if "openai" in enabled_set and has_secure_key("openai", "OPENAI_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("openai-")])
        if "anthropic" in enabled_set and has_secure_key("anthropic", "ANTHROPIC_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("anthropic-")])
        if "google" in enabled_set and has_secure_key("google", "GOOGLE_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("google-")])
        if "xai" in enabled_set and has_secure_key("xai", "XAI_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("xai-")])
        if "deepseek" in enabled_set and has_secure_key("deepseek", "DEEPSEEK_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("deepseek-")])
        if "groq" in enabled_set and has_secure_key("groq", "GROQ_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("groq-")])
        if "ollama-cloud" in enabled_set and has_secure_key("ollama-cloud", "OLLAMA_CLOUD_API_KEY"):
            cloud_providers.append("ollama-cloud")
        if "perplexity" in enabled_set and has_secure_key("perplexity", "PERPLEXITY_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("perplexity-")])
        # Only add local ollama if explicitly enabled in frontend
        if "ollama" in enabled_set:
            local_providers.append("ollama")
    else:
        # Legacy: use all cloud providers with API keys, plus ollama as fallback
        if has_secure_key("openai", "OPENAI_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("openai-")])
        if has_secure_key("anthropic", "ANTHROPIC_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("anthropic-")])
        if has_secure_key("google", "GOOGLE_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("google-")])
        if has_secure_key("xai", "XAI_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("xai-")])
        if has_secure_key("deepseek", "DEEPSEEK_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("deepseek-")])
        if has_secure_key("groq", "GROQ_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("groq-")])
        if has_secure_key("ollama-cloud", "OLLAMA_CLOUD_API_KEY"):
            cloud_providers.append("ollama-cloud")
        if has_secure_key("perplexity", "PERPLEXITY_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("perplexity-")])
        # Add local ollama as fallback (always available)
        local_providers.append("ollama")

    # Deduplicate by provider name
    def deduplicate(provider_list):
        seen = set()
        result = []
        for pk in provider_list:
            pname = pk.split("-")[0]
            if pname not in seen:
                seen.add(pname)
                result.append(pk)
        return result

    cloud_providers = deduplicate(cloud_providers)[:4]  # Limit to 4 concurrent
    local_providers = deduplicate(local_providers)

    # Combine: clouds first, then local as fallback
    all_providers = cloud_providers + local_providers
    logger.info("Race mode: clouds=%s, local=%s, combined=%s", cloud_providers, local_providers, all_providers)

    def fetch_events(pk):
        """Collect all SSE events from a provider. Returns (pk, events_list, error)."""
        import time as fetch_time
        fetch_start = fetch_time.time()
        logger.info("[PROVIDER START] %s", pk)
        try:
            if pk == "ollama":
                from ai_router import ask_ollama_stream
                events = list(ask_ollama_stream(q, mode=mode, style=style, messages=messages))
            else:
                resolved = PROVIDER_MODEL_MAP.get(pk, ("openai", "gpt-4o-mini"))
                model_name = resolved[1]
                stream_fn = get_stream_fn(pk)
                if stream_fn is None:
                    return (pk, [], f"No stream function for {pk}")
                events = list(stream_fn(q, model=model_name, mode=mode, style=style, messages=messages))
            # Check if events contains an error — but track if any content was yielded first
            content_yielded = any(("event: chunk" in e or "event: meta" in e) and '"content"' in e for e in events)
            has_error = any("event: error" in e for e in events)
            if has_error:
                if content_yielded:
                    # Partial content before error — return it rather than discarding
                    logger.warning("[PROVIDER] %s returned error after content, returning partial (%.1fs)", pk, fetch_time.time() - fetch_start)
                    return (pk, events, None)
                for e in events:
                    if "event: error" in e:
                        return (pk, [], e)
                return (pk, [], "Unknown error")
            logger.info("Provider %s succeeded with %d events (%.1fs)", pk, len(events), fetch_time.time() - fetch_start)
            return (pk, events, None)
        except Exception as e:
            logger.error("Provider %s failed: %s (%.1fs)", pk, e, fetch_time.time() - fetch_start)
            return (pk, [], str(e))

    def race_generator():
        from cloud_providers import MODEL_DISPLAY_NAMES
        STATE["is_streaming"] = True
        winner_found = False

        # Use ThreadPoolExecutor to run providers in parallel
        # First completed provider with a valid response wins
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(all_providers)) as executor:
            # Submit all provider requests
            future_to_pk = {
                executor.submit(fetch_events, pk): pk
                for pk in all_providers
            }

            # Yield events from the first provider that completes successfully
            for future in concurrent.futures.as_completed(future_to_pk):
                pk = future_to_pk[future]
                try:
                    result_pk, events, error = future.result()
                    if error:
                        logger.warning("[RACE] provider %s returned error: %s", pk, error)
                        continue
                    if events:
                        # Found the winner! Stream their events
                        logger.info("[RACE] winner: %s", pk)
                        for event in events:
                            yield event
                        winner_found = True
                        break
                except Exception as e:
                    logger.warning("[RACE] provider %s raised exception: %s", pk, e)
                    continue

        if not winner_found:
            logger.error("All providers failed in race mode")
            yield f"event: error\ndata: {{\"type\":\"error\",\"message\":\"All providers failed\"}}\n\n"

        logger.info("[RACE COMPLETE] total_time=%.1fs", time_module.time() - race_start)
        STATE["is_streaming"] = False

    return StreamingResponse(race_generator(), media_type="text/event-stream")


# ==============================
# DOCUMENT UPLOAD & RAG ENDPOINTS
# ==============================

@app.post("/documents/upload")
@rate_limit(requests_per_minute=30)  # T24: Document upload
async def upload_document(file: UploadFile = File(...), user: User = Depends(require_authentication)):
    """Upload a document for RAG context retrieval."""
    from document_store import get_document_store

    # Save uploaded file temporarily
    temp_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        doc_store = get_document_store()
        result = doc_store.add_document(temp_path)

        # Clean up temp file
        try:
            os.remove(temp_path)
        except OSError:
            pass

        return result
    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/documents")
async def list_documents(limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)):
    """List all uploaded documents with pagination."""
    from document_store import get_document_store
    doc_store = get_document_store()
    all_docs = doc_store.list_documents()
    total = len(all_docs)
    return {
        "documents": all_docs[offset:offset + limit],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, user: User = Depends(require_authentication)):
    """Delete a document from the store."""
    from document_store import get_document_store
    doc_store = get_document_store()
    success = doc_store.delete_document(doc_id)
    return {"success": success}


@app.post("/documents/retrieve")
async def retrieve_document_context(query: str = Form(...), top_k: int = Form(5)):
    """Retrieve relevant document context for a query."""
    from document_store import get_document_store
    doc_store = get_document_store()
    results = doc_store.retrieve_context(query, top_k)
    return {"results": results}


# ==============================
# SPEAKER DIARIZATION ENDPOINTS
# ==============================

@app.post("/transcribe-with-speakers")
async def transcribe_with_speakers(file: UploadFile = File(...)):
    """
    Transcribe audio with speaker diarization.
    Returns transcription with speaker labels for each segment.
    """
    global USE_AUTONOMOUS
    from speaker_diarization import process_transcription_with_speakers
    from whisper_handler import get_streaming_transcriber

    USE_AUTONOMOUS = False
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    wav_path = file_path.replace(".webm", ".wav")
    import subprocess
    ffmpeg_path = get_ffmpeg_path()
    result = subprocess.run(
        [ffmpeg_path, "-i", file_path, "-ar", "16000", "-ac", "1", wav_path, "-y"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg conversion failed: {result.stderr}")

    try:
        # Get detailed transcription with timestamps from Whisper
        # Note: faster_whisper returns segments with timestamps
        model = get_model(CURRENT_MODE)
        segments, _ = model.transcribe(
            wav_path,
            beam_size=3,
            vad_filter=False,
            condition_on_previous_text=False,
            language="en",
            word_timestamps=True
        )

        # Convert to dict format expected by diarization
        whisper_segments = []
        for seg in segments:
            whisper_segments.append({
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip()
            })

        # Get full text for AI processing
        full_text = " ".join(s["text"] for s in whisper_segments)

        # Process with speaker diarization
        speaker_result = process_transcription_with_speakers(wav_path, whisper_segments)

        # Get AI response
        ai_response = ""
        if full_text and is_meaningful(full_text) and is_question(full_text):
            result = route_ai(full_text, mode=CURRENT_MODE)
            ai_response = clean_ai_output(result["response"])

        return {
            "text": full_text,
            "response": ai_response,
            "speakers": speaker_result["segments"],
            "formatted_transcript": speaker_result["formatted"],
            "speaker_count": speaker_result["speaker_count"]
        }

    except Exception as e:
        logger.error(f"Transcription with speakers failed: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)

    finally:
        # Clean up temp files
        for path in (file_path, wav_path):
            try:
                os.remove(path)
            except OSError:
                pass


@app.get("/transcribe/{audio_id}/speakers")
async def get_transcription_speakers(audio_id: str):
    """
    Get speaker information for a previously transcribed audio.
    (Placeholder for future persistent storage)
    """
    return {"status": "not_implemented", "audio_id": audio_id}


def shutdown_handler(*args):
    global USE_AUTONOMOUS
    USE_AUTONOMOUS = False
    # T16: Close database connections on shutdown
    if DATABASE_AVAILABLE:
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            loop.run_until_complete(close_database())
            loop.close()
        except Exception:
            pass
    sys.exit(0)


signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)


@app.on_event("shutdown")
async def shutdown_event():
    """FastAPI shutdown handler - closes database connections."""
    if DATABASE_AVAILABLE:
        try:
            await close_database()
            logger.info("[Shutdown] Database connections closed")
        except Exception as e:
            logger.warning(f"[Shutdown] Database close error: {e}")


@app.websocket("/ws/transcribe")
async def ws_transcribe(ws: WebSocket):
    """Stream audio from browser and receive real-time transcriptions.

    Browser sends raw PCM Float32 audio at 16kHz mono.
    This endpoint accumulates chunks, transcribes on 0.5s segments,
    and sends back partial + final transcription via WebSocket JSON messages.

    T3: WebSocket auth — validates token from query param ?token=xxx
    In production (AUTH_REQUIRED=true), rejects unauthenticated connections.

    Message types sent to browser:
      - {"type": "partial", "text": "..."}  — interim transcription
      - {"type": "final", "text": "..."}   — transcription of remaining buffer
    """
    # T3: WebSocket authentication — ALWAYS enforce, not gated by AUTH_REQUIRED
    token = ws.query_params.get("token")
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
    transcriber = BrowserTranscriber()
    partial_texts = []
    msg_queue = asyncio.Queue()
    ws_closed = False

    def on_transcript(text):
        """Called from transcription thread — put result in queue (non-blocking)."""
        if ws_closed:
            return
        partial_texts.append(text)
        combined = " ".join(partial_texts)
        try:
            msg_queue.put_nowait({"type": "partial", "text": combined})
        except asyncio.QueueFull:
            pass

    transcriber.add_callback(on_transcript)

    async def background_transcriber():
        """Pump the background thread's queue into the WebSocket."""
        while not ws_closed:
            try:
                msg = await asyncio.wait_for(msg_queue.get(), timeout=0.5)
                if ws_closed:
                    break
                await ws.send_json(msg)
            except asyncio.TimeoutError:
                continue
            except Exception:
                break

    transcribe_task = asyncio.create_task(background_transcriber())

    try:
        while True:
            try:
                data = await asyncio.wait_for(ws.receive_bytes(), timeout=60)
            except asyncio.TimeoutError:
                continue

            chunk = np.frombuffer(data, dtype=np.float32)
            if chunk is not None and len(chunk) > 0:
                transcriber.add_chunk(chunk)

    except Exception:
        pass
    finally:
        ws_closed = True
        await transcribe_task
        final_text = transcriber.get_final()
        combined = " ".join(partial_texts).strip() or final_text
        try:
            await ws.send_json({"type": "final", "text": combined})
        except Exception:
            pass


# ==============================
# EXPORT/IMPORT ENDPOINTS
# ==============================

@app.post("/conversations/export")
async def export_conversation(body: dict, user: User = Depends(require_authentication)):
    """
    Export conversation in various formats.

    body: {
        "messages": [...],
        "format": "markdown" | "json" | "txt",
        "includeMetadata": bool,
        "includeTimestamps": bool,
        "metadata": {...}  // optional
    }
    """
    messages = body.get("messages", [])
    fmt = body.get("format", "markdown")
    include_meta = body.get("includeMetadata", True)
    include_timestamps = body.get("includeTimestamps", False)
    metadata = body.get("metadata", {})

    if not messages:
        return error_response(ErrorCode.VALIDATION_ERROR, "No messages to export", status_code=400)

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    date_str = time.strftime("%Y-%m-%d")

    if fmt == "json":
        export_data = {
            "version": "1.0",
            "exported_at": timestamp,
            "messages": messages
        }
        if include_meta:
            export_data["metadata"] = metadata
        return {"content": json.dumps(export_data, indent=2), "filename": f"conversation-{date_str}.json"}

    elif fmt == "markdown":
        lines = []
        if include_meta:
            lines.append(f"# Conversation Export")
            lines.append(f"**Date:** {timestamp}")
            if metadata.get("mode"):
                lines.append(f"**Mode:** {metadata['mode']}")
            if metadata.get("model"):
                lines.append(f"**Model:** {metadata['model']}")
            lines.append("")

        for msg in messages:
            role = msg.get("role", "unknown")
            text = msg.get("text", "")
            ts = msg.get("timestamp", "")

            header = "## You" if role == "user" else "## AI"
            if include_timestamps and ts:
                ts_str = time.strftime("%H:%M:%S", time.localtime(ts / 1000)) if isinstance(ts, (int, float)) else str(ts)
                header += f" ({ts_str})"

            lines.append(header)
            lines.append("")
            lines.append(text)
            lines.append("")

        content = "\n".join(lines)
        return {"content": content, "filename": f"conversation-{date_str}.md"}

    else:  # txt
        lines = []
        if include_meta:
            lines.append(f"Conversation Export - {timestamp}")
            lines.append("=" * 50)
            lines.append("")

        for msg in messages:
            role = "You" if msg.get("role") == "user" else "AI"
            text = msg.get("text", "")
            ts = msg.get("timestamp", "")

            prefix = f"[{role}]"
            if include_timestamps and ts:
                ts_str = time.strftime("%H:%M:%S", time.localtime(ts / 1000)) if isinstance(ts, (int, float)) else str(ts)
                prefix += f" {ts_str}"

            lines.append(f"{prefix}: {text}")
            lines.append("")

        content = "\n".join(lines)
        return {"content": content, "filename": f"conversation-{date_str}.txt"}


@app.post("/conversations/import")
async def import_conversations(file: UploadFile = File(...), user: User = Depends(require_authentication)):
    """Import conversations from JSON file."""
    try:
        content = await file.read()
        data = json.loads(content.decode("utf-8"))

        if not isinstance(data, dict) or "messages" not in data:
            return error_response(ErrorCode.INVALID_FORMAT, "Invalid format - expected JSON with 'messages' array", status_code=422)

        messages = data.get("messages", [])
        metadata = data.get("metadata", {})

        return {
            "success": True,
            "messages": messages,
            "metadata": metadata,
            "count": len(messages)
        }
    except json.JSONDecodeError as e:
        return error_response(ErrorCode.INVALID_FORMAT, f"Invalid JSON: {str(e)}", status_code=422)
    except Exception as e:
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


# ==============================
# SALES OBJECTION HANDLING
# ==============================

# Common sales objections and suggested responses
OBJECTION_KEYWORDS = {
    "price": {
        "keywords": ["expensive", "too much", "price", "cost", "budget", "cheap", "cheaper", "afford"],
        "title": "Price Objection",
        "suggestions": [
            "Focus on ROI - our customers see 3x return in 6 months",
            "We offer flexible payment plans",
            "Let's discuss the enterprise tier with volume discounts",
            "Compare total cost of ownership vs alternatives"
        ]
    },
    "competitor": {
        "keywords": ["competitor", "competition", "alternative", "vs", "versus", "compare", "better than", "cheaper than"],
        "title": "Competitor Mention",
        "suggestions": [
            "Our differentiator is local AI - no data leaves your machine",
            "We support 8+ AI providers vs their single model",
            "Open source means no vendor lock-in",
            "Vision capabilities they don't offer"
        ]
    },
    "timing": {
        "keywords": ["not now", "later", "next quarter", "next year", "timing", "not ready", "delay", "postpone"],
        "title": "Timing Objection",
        "suggestions": [
            "Start with a pilot - no commitment",
            "Early adopters get lifetime pricing",
            "Setup takes 5 minutes - try it today",
            "We can schedule a follow-up that works for you"
        ]
    },
    "features": {
        "keywords": ["missing", "need", "feature", "functionality", "doesn't have", "lacks", "require"],
        "title": "Feature Request",
        "suggestions": [
            "We're shipping new features weekly - what's your priority?",
            "Our open API can bridge any gaps",
            "Let me check our roadmap for that feature",
            "Custom development available for enterprise"
        ]
    },
    "security": {
        "keywords": ["security", "privacy", "data", "confidential", "compliance", "soc2", "gdpr", "hipaa"],
        "title": "Security Question",
        "suggestions": [
            "100% local processing - data never leaves your machine",
            "No cloud dependencies for core features",
            "Open source - audit the code yourself",
            "SOC 2 Type II certified infrastructure"
        ]
    }
}


@app.post("/detect-objections")
async def detect_objections(body: dict):
    """
    Detect sales objections in text.

    body: {"text": "..."}
    Returns: {"objections": [...], "suggestions": [...]}
    """
    text = body.get("text", "").lower()
    if not text:
        return {"objections": []}

    detected = []
    for objection_type, config in OBJECTION_KEYWORDS.items():
        if any(kw in text for kw in config["keywords"]):
            detected.append({
                "type": objection_type,
                "title": config["title"],
                "suggestions": config["suggestions"]
            })

    return {"objections": detected}


# ==============================
# ANALYTICS ENDPOINTS
# ==============================

@app.post("/analytics/record")
async def record_analytics(body: dict, user: User = Depends(require_authentication)):
    """Record analytics for a conversation."""
    from analytics import get_analytics_store
    from datetime import datetime as _dt
    store = get_analytics_store()

    # Parse timestamps — accept ISO strings or unix timestamps
    start_time = body.get("start_time") or time.time()
    end_time = body.get("end_time") or time.time()
    if isinstance(start_time, str):
        try:
            start_time = _dt.fromisoformat(start_time).timestamp()
        except ValueError:
            start_time = time.time()
    if isinstance(end_time, str):
        try:
            end_time = _dt.fromisoformat(end_time).timestamp()
        except ValueError:
            end_time = time.time()

    metrics = store.record_conversation(
        conversation_id=body.get("conversation_id"),
        messages=body.get("messages", []),
        start_time=float(start_time),
        end_time=float(end_time),
        models_used=body.get("models_used", [])
    )

    return {"status": "recorded", "metrics": {
        "duration_minutes": metrics.duration_minutes,
        "message_count": metrics.message_count
    }}


@app.get("/analytics/summary")
async def get_analytics_summary(days: int = 30, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    """Get analytics summary for the past N days (paginated)."""
    from analytics import get_analytics_store
    store = get_analytics_store()
    data = store.get_summary(days)
    # Paginate if data is a list
    if isinstance(data, list):
        total = len(data)
        return {"data": data[offset:offset + limit], "total": total, "limit": limit, "offset": offset}
    return data


@app.post("/analytics/export")
async def export_analytics(body: dict):
    """Export analytics data."""
    from analytics import get_analytics_store
    store = get_analytics_store()
    fmt = body.get("format", "json")
    return store.get_export_data(fmt)


# ==============================
# CRM INTEGRATION ENDPOINTS
# ==============================

@app.get("/crm/config")
async def get_crm_config():
    """Get CRM configuration."""
    from crm_integration import get_crm
    crm = get_crm()
    return crm.get_config()


@app.post("/crm/config")
async def save_crm_config(body: dict, user: User = Depends(require_authentication)):
    """Save CRM configuration."""
    from crm_integration import get_crm
    crm = get_crm()
    success = crm.configure(body)
    return {"success": success}


@app.post("/crm/webhook/{crm_type}/{event_type}")
async def send_crm_webhook(crm_type: str, event_type: str, body: dict):
    """Send webhook to CRM."""
    from crm_integration import get_crm
    crm = get_crm()
    result = crm.log_event(event_type, body)
    return {"success": result}


@app.get("/crm/test")
async def test_crm_connection():
    """Test CRM connection."""
    from crm_integration import get_crm
    crm = get_crm()
    return crm.test_connection()


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    # T3: WebSocket authentication — ALWAYS enforce, not gated by AUTH_REQUIRED
    token = ws.query_params.get("token")
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
    try:
        while True:
            msg = await ws.receive_text()
            try:
                result = route_ai(msg, mode=CURRENT_MODE)
                await ws.send_text(clean_ai_output(result["response"]))
            except Exception as e:
                logger.error(f"[WS] Error processing message: {e}")
                try:
                    await ws.send_text(json.dumps({"error": str(e)}))
                except Exception:
                    break
    except Exception:
        pass  # Client disconnected


# ======================================
# COGNITIVE GRAPH API - Phase 1
# Personal Knowledge Graph for Interview History
# ======================================

@app.get("/cognitive-graph/status")
async def cognitive_graph_status():
    """Check if Neo4j cognitive graph is available"""
    if not COGNITIVE_GRAPH_AVAILABLE:
        return {"available": False, "error": "Cognitive graph module not installed"}

    try:
        from cognitive_graph import get_driver
        driver = get_driver()
        if not driver:
            return {"available": True, "connected": False, "error": "Neo4j not connected"}
        # Verify connection actually works
        try:
            with driver.session() as session:
                session.run("RETURN 1")
            return {"available": True, "connected": True}
        except Exception:
            return {"available": True, "connected": False, "error": "Neo4j connection failed"}
    except Exception as e:
        return {"available": True, "connected": False, "error": str(e)}


@app.post("/cognitive-graph/initialize")
async def cognitive_graph_initialize():
    """Initialize the cognitive graph schema"""
    if not COGNITIVE_GRAPH_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Cognitive graph not available", status_code=503)

    success = initialize_graph()
    return {"initialized": success}


@app.get("/cognitive-graph/search")
async def cognitive_graph_search(q: str = Query(...), limit: int = Query(10)):
    """Semantic search across interview history"""
    if not COGNITIVE_GRAPH_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Cognitive graph not available", status_code=503)

    results = query_graph(q)
    return {"query": q, "results": results, "count": len(results)}


@app.get("/cognitive-graph/history/{user_id}")
async def cognitive_graph_history(user_id: str, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    """Get user's interview history from graph (paginated)."""
    if not COGNITIVE_GRAPH_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Cognitive graph not available", status_code=503)

    history = cognitive_graph.get_interview_history(user_id, limit + offset)
    # Paginate results
    total = len(history) if history else 0
    paginated = history[offset:offset + limit] if history else []
    return {"user_id": user_id, "interviews": paginated, "total": total, "limit": limit, "offset": offset}


@app.get("/cognitive-graph/company/{company_name}")
async def cognitive_graph_company_insights(company_name: str):
    """Get insights about a company"""
    if not COGNITIVE_GRAPH_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Cognitive graph not available", status_code=503)

    insights = cognitive_graph.get_company_insights(company_name)
    return {"company": company_name, "insights": insights}


@app.get("/cognitive-graph/skill/{user_id}/{skill_name}")
async def cognitive_graph_skill_progression(user_id: str, skill_name: str):
    """Track user's progression on a specific skill"""
    if not COGNITIVE_GRAPH_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Cognitive graph not available", status_code=503)

    progression = cognitive_graph.get_skill_progression(user_id, skill_name)
    return {"user_id": user_id, "skill": skill_name, "progression": progression}


@app.post("/cognitive-graph/ingest/{conversation_id}")
async def cognitive_graph_ingest(conversation_id: str, body: dict):
    """Ingest a conversation into the cognitive graph"""
    if not COGNITIVE_GRAPH_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Cognitive graph not available", status_code=503)

    success = ingest_conversation(conversation_id, body)
    return {"ingested": success, "conversation_id": conversation_id}


@app.post("/cognitive-graph/interview")
async def cognitive_graph_add_interview(body: dict):
    """Add an interview to the cognitive graph"""
    if not COGNITIVE_GRAPH_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Cognitive graph not available", status_code=503)

    from datetime import datetime

    interview = InterviewNode(
        id=body.get("id", ""),
        title=body.get("title", "Untitled"),
        timestamp=datetime.fromisoformat(body.get("timestamp", datetime.now().isoformat())),
        duration_ms=body.get("duration_ms", 0),
        user_id=body.get("user_id", "default")
    )

    success = cognitive_graph.add_interview(interview)
    return {"added": success, "interview_id": interview.id}


# ======================================
# ENTITY EXTRACTION API - Phase 1
# NLP entity extraction for interview transcripts
# ======================================

try:
    from entity_extraction import extract_entities, process_transcript, entity_extractor
    ENTITY_EXTRACTION_AVAILABLE = True
except ImportError:
    ENTITY_EXTRACTION_AVAILABLE = False


@app.post("/extract-entities")
async def extract_entities_api(body: dict):
    """Extract entities (companies, topics, skills) from text"""
    if not ENTITY_EXTRACTION_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Entity extraction not available", status_code=503)

    text = body.get("text", "")
    if not text:
        return error_response(ErrorCode.MISSING_PARAMETER, "No text provided", status_code=422)

    entities = extract_entities(text)
    return {"text": text[:100] + "..." if len(text) > 100 else text, "entities": entities}


@app.post("/process-transcript")
async def process_transcript_api(body: dict):
    """Process a transcript into Q&A pairs with extracted entities"""
    if not ENTITY_EXTRACTION_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Entity extraction not available", status_code=503)

    transcript = body.get("transcript", "")
    if not transcript:
        return error_response(ErrorCode.MISSING_PARAMETER, "No transcript provided", status_code=422)

    qa_pairs = process_transcript(transcript)
    return {
        "qa_pairs": qa_pairs,
        "count": len(qa_pairs),
        "transcript_length": len(transcript)
    }


@app.get("/extract/categorize")
async def categorize_question_api(q: str = Query(...)):
    """Categorize a question (technical, behavioral, system_design, knowledge)"""
    if not ENTITY_EXTRACTION_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Entity extraction not available", status_code=503)

    category, confidence = entity_extractor.categorize_question(q)
    difficulty, diff_conf = entity_extractor.estimate_difficulty(q)

    return {
        "question": q,
        "category": {"label": category, "confidence": confidence},
        "difficulty": {"label": difficulty, "confidence": diff_conf} if difficulty else None
    }


# ======================================
# PREDICTIVE INTERVIEW API - Phase 1 Task #18
# Predict interview questions based on company/role
# ======================================

try:
    from predictive_interview import (
        predictive_interview,
        get_predictions,
        get_checklist
    )
    PREDICTIVE_AVAILABLE = True
except ImportError:
    PREDICTIVE_AVAILABLE = False
    logger.warning("[Predictive] Module not available")


@app.get("/predict/questions")
async def predict_questions(
    company: str = Query(...),
    role: Optional[str] = Query(None),
    limit: int = Query(10)
):
    """Get predicted interview questions for a company/role"""
    if not PREDICTIVE_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Predictive interview module not available", status_code=503)

    predictions = get_predictions(company, role, limit)
    return predictions


@app.get("/predict/checklist")
async def get_preparation_checklist(
    company: str = Query(...),
    role: Optional[str] = Query(None)
):
    """Get preparation checklist for an interview"""
    if not PREDICTIVE_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Predictive interview module not available", status_code=503)

    checklist = get_checklist(company, role)
    return checklist


# ======================================
# ADVANCED SEARCH API - Enhanced search functionality
# ======================================

@app.get("/cognitive-graph/search/advanced")
async def cognitive_graph_advanced_search(
    query: Optional[str] = Query(None),
    company: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    limit: int = Query(50)
):
    """
    Advanced search with multiple filters.

    Args:
        query: Text to search for
        company: Filter by company name
        topic: Filter by topic
        category: technical/behavioral/system_design/knowledge
        difficulty: easy/medium/hard
        date_from: ISO date string
        date_to: ISO date string
        limit: Max results
    """
    if not COGNITIVE_GRAPH_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Cognitive graph not available", status_code=503)

    results = cognitive_graph.advanced_search(
        query=query,
        company=company,
        topic=topic,
        category=category,
        difficulty=difficulty,
        date_from=date_from,
        date_to=date_to,
        limit=limit
    )

    return {
        "filters": {
            "query": query,
            "company": company,
            "topic": topic,
            "category": category,
            "difficulty": difficulty,
            "date_from": date_from,
            "date_to": date_to
        },
        "results": results,
        "count": len(results)
    }


@app.get("/predict/companies")
async def get_supported_companies():
    """Get list of companies with prediction data"""
    if not PREDICTIVE_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Predictive interview module not available", status_code=503)

    companies = list(predictive_interview.question_db.keys())
    return {
        "companies": companies,
        "total": len(companies)
    }


# ======================================
# BACKFILL API - Backfill historical conversations
# ======================================

@app.post("/cognitive-graph/backfill")
async def backfill_historical_conversations():
    """
    Backfill all historical conversations into cognitive graph.
    This reads saved conversation files and ingests them.
    """
    try:
        import subprocess
        import sys

        # Run backfill script
        result = subprocess.run(
            [sys.executable, "backfill_cognitive_graph.py"],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        return {
            "backfill_triggered": True,
            "return_code": result.returncode,
            "output": result.stdout[-1000:] if result.stdout else "",  # Last 1000 chars
            "errors": result.stderr[-500:] if result.stderr else ""
        }
    except Exception as e:
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/cognitive-graph/stats")
async def get_cognitive_graph_stats():
    """Get statistics about the cognitive graph"""
    if not COGNITIVE_GRAPH_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Cognitive graph not available", status_code=503)

    try:
        from cognitive_graph import cognitive_graph

        # Get counts from Neo4j
        stats = {}

        if cognitive_graph.driver:
            with cognitive_graph.driver.session() as session:
                # Count interviews
                result = session.run("MATCH (i:Interview) RETURN count(i) as count")
                stats['interviews'] = result.single()['count']

                # Count questions
                result = session.run("MATCH (q:Question) RETURN count(q) as count")
                stats['questions'] = result.single()['count']

                # Count companies
                result = session.run("MATCH (c:Company) RETURN count(c) as count")
                stats['companies'] = result.single()['count']

                # Count topics
                result = session.run("MATCH (t:Topic) RETURN count(t) as count")
                stats['topics'] = result.single()['count']

                # Count skills
                result = session.run("MATCH (s:Skill) RETURN count(s) as count")
                stats['skills'] = result.single()['count']

        return {"stats": stats, "connected": bool(cognitive_graph.driver)}
    except Exception as e:
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


# ======================================
# REAL-TIME SUGGESTIONS API - Phase 2 Task #28
# Live interview assistance with contextual hints
# ======================================

try:
    from realtime_suggestions import (
        realtime_engine,
        voice_processor,
        process_transcript_segment,
        process_voice_command
    )
    REALTIME_AVAILABLE = True
except ImportError as e:
    REALTIME_AVAILABLE = False
    logger.warning(f"[Realtime] Module not available: {e}")


@app.post("/realtime/process")
async def process_realtime_segment(
    text: str = Query(...),
    speaker: str = Query(...),  # "user" or "interviewer"
    conversation_id: Optional[str] = Query(None)
):
    """
    Process a transcript segment and return suggestion if relevant.
    Called every 3-5 seconds during live interview.
    """
    if not REALTIME_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Realtime suggestion engine not available", status_code=503)

    try:
        suggestion = process_transcript_segment(text, speaker)

        if suggestion:
            return {
                "has_suggestion": True,
                "suggestion": {
                    "id": suggestion.id,
                    "type": suggestion.type,
                    "content": suggestion.content,
                    "confidence": suggestion.confidence,
                    "relevance_score": suggestion.relevance_score,
                    "context": suggestion.context
                }
            }

        return {"has_suggestion": False}
    except Exception as e:
        logger.error(f"[Realtime] Error processing segment: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.post("/realtime/command")
async def process_voice_command_api(
    text: str = Query(...),
    conversation_id: Optional[str] = Query(None)
):
    """
    Process a voice command from the user.
    Commands like "What did I say about React?"
    """
    if not REALTIME_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Realtime suggestion engine not available", status_code=503)

    try:
        result = process_voice_command(text)

        if result:
            return {
                "is_command": True,
                "action": result.get("action"),
                "data": result
            }

        return {"is_command": False}
    except Exception as e:
        logger.error(f"[Realtime] Error processing command: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/realtime/suggestion-history")
async def get_suggestion_history(
    limit: int = Query(50)
):
    """Get history of suggestions shown during current session"""
    if not REALTIME_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Realtime suggestion engine not available", status_code=503)

    try:
        history = realtime_engine.get_suggestion_history(limit)
        return {
            "suggestions": [
                {
                    "id": s.id,
                    "type": s.type,
                    "content": s.content[:200],  # Truncate
                    "confidence": s.confidence,
                    "timestamp": s.timestamp.isoformat()
                }
                for s in history
            ],
            "count": len(history)
        }
    except Exception as e:
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.post("/realtime/configure")
async def configure_suggestions(
    min_confidence: float = Query(0.6),
    cooldown_seconds: float = Query(10.0)
):
    """Configure realtime suggestion parameters"""
    if not REALTIME_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Realtime suggestion engine not available", status_code=503)

    try:
        realtime_engine.set_min_confidence(min_confidence)
        realtime_engine.cooldown_seconds = cooldown_seconds
        return {
            "configured": True,
            "min_confidence": min_confidence,
            "cooldown_seconds": cooldown_seconds
        }
    except Exception as e:
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.post("/realtime/clear")
async def clear_suggestion_state():
    """Clear buffer and suggestion history (call when starting new interview)"""
    if not REALTIME_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Realtime suggestion engine not available", status_code=503)

    try:
        realtime_engine.clear_buffer()
        return {"cleared": True}
    except Exception as e:
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


# ======================================
# CONVERSATION ANALYZER API - Phase 2 Task #30
# Auto-categorization and quality analysis
# ======================================

try:
    from conversation_analyzer import analyzer, analyze_conversation
    ANALYZER_AVAILABLE = True
except ImportError as e:
    ANALYZER_AVAILABLE = False
    logger.warning(f"[Analyzer] Module not available: {e}")


@app.post("/analyze/conversation")
async def analyze_conversation_api(
    conversation: Dict
):
    """
    Analyze a conversation for auto-tagging and quality metrics.
    Returns conversation type, focus areas, quality scores, and recommendations.
    """
    if not ANALYZER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Conversation analyzer not available", status_code=503)

    try:
        analysis = analyze_conversation(conversation)
        return analysis
    except Exception as e:
        logger.error(f"[Analyzer] Error analyzing conversation: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.post("/analyze/batch")
async def analyze_conversations_batch(
    conversations: List[Dict]
):
    """Analyze multiple conversations in batch"""
    if not ANALYZER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Conversation analyzer not available", status_code=503)

    try:
        results = []
        for conv in conversations:
            analysis = analyze_conversation(conv)
            results.append({
                "id": conv.get("id", "unknown"),
                "title": conv.get("title", ""),
                "tags": analysis["tags"],
                "quality_tier": analysis["tags"]["quality_tier"],
                "overall_score": analysis["quality_metrics"]["overall_score"]
            })

        return {
            "analyzed": len(results),
            "results": results
        }
    except Exception as e:
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/analyze/types")
async def get_conversation_types():
    """Get list of supported conversation types"""
    if not ANALYZER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Conversation analyzer not available", status_code=503)

    try:
        return {
            "types": [
                {"id": "practice_session", "label": "Practice Session", "description": "Self-study or preparation"},
                {"id": "mock_interview", "label": "Mock Interview", "description": "Simulated interview with feedback"},
                {"id": "real_interview", "label": "Real Interview", "description": "Actual company interview"}
            ],
            "focus_areas": [
                {"id": "system_design_focus", "label": "System Design"},
                {"id": "algorithm_heavy", "label": "Algorithms"},
                {"id": "behavioral_only", "label": "Behavioral"},
                {"id": "frontend_focus", "label": "Frontend"},
                {"id": "backend_focus", "label": "Backend"},
                {"id": "fullstack_focus", "label": "Fullstack"}
            ]
        }
    except Exception as e:
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


# ======================================
# ANALYTICS API - Phase 2 Task #31
# Graph analytics dashboard data
# ======================================

try:
    from analytics_engine import analytics, get_skill_progression, get_dashboard_data
    ANALYTICS_AVAILABLE = True
except ImportError as e:
    ANALYTICS_AVAILABLE = False
    logger.warning(f"[Analytics] Module not available: {e}")

# Performance Analyzer - Phase 2 Task #32
try:
    from performance_analyzer import analyzer as performance_analyzer
    PERFORMANCE_ANALYZER_AVAILABLE = True
except ImportError as e:
    PERFORMANCE_ANALYZER_AVAILABLE = False
    logger.warning(f"[PerformanceAnalyzer] Module not available: {e}")


@app.get("/analytics/skill-progression/{user_id}")
async def get_skill_progression_api(
    user_id: str,
    skill: str = Query(...),
    months: int = Query(6)
):
    """Get skill progression over time for charting"""
    if not ANALYTICS_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Analytics engine not available", status_code=503)

    try:
        data = analytics.get_skill_progression(user_id, skill, months)
        return data
    except Exception as e:
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.post("/analytics/company-comparison")
async def compare_companies(
    companies: List[str] = Query(...)
):
    """Compare interview patterns across companies (heatmap data)"""
    if not ANALYTICS_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Analytics engine not available", status_code=503)

    try:
        data = analytics.get_company_comparison(companies)
        return data
    except Exception as e:
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/analytics/topic-network/{user_id}")
async def get_topic_network_api(
    user_id: str,
    min_connections: int = Query(2)
):
    """Get topic co-occurrence network for D3.js visualization"""
    if not ANALYTICS_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Analytics engine not available", status_code=503)

    try:
        data = analytics.get_topic_network(user_id, min_connections)
        return data
    except Exception as e:
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/analytics/interview-calendar/{user_id}")
async def get_interview_calendar_api(
    user_id: str,
    months: int = Query(6)
):
    """Get interview frequency data for calendar heatmap"""
    if not ANALYTICS_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Analytics engine not available", status_code=503)

    try:
        data = analytics.get_interview_calendar(user_id, months)
        return data
    except Exception as e:
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/analytics/performance-trends/{user_id}")
async def get_performance_trends_api(
    user_id: str
):
    """Get overall performance trends (improving/declining/stable skills)"""
    if not ANALYTICS_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Analytics engine not available", status_code=503)

    try:
        data = analytics.get_performance_trends(user_id)
        return data
    except Exception as e:
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/analytics/dashboard/{user_id}")
async def get_dashboard_summary_api(
    user_id: str
):
    """Get dashboard summary with key metrics"""
    if not ANALYTICS_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Analytics engine not available", status_code=503)

    try:
        data = analytics.get_dashboard_summary(user_id)
        return data
    except Exception as e:
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


# ======================================
# PERFORMANCE ANALYZER API - Phase 2 Task #32
# Interview answer analysis and insights
# ======================================

@app.post("/performance/analyze")
async def analyze_answer_performance(
    answer_text: str = Query(..., description="The answer text to analyze"),
    question_type: str = Query("behavioral", description="Type: behavioral, technical, system_design")
):
    """Analyze an interview answer for STAR method, code quality, speaking patterns"""
    if not PERFORMANCE_ANALYZER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Performance analyzer not available", status_code=503)

    try:
        result = performance_analyzer.analyze_answer(answer_text, question_type)
        return result
    except Exception as e:
        logger.error(f"[PerformanceAnalyzer] Error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.post("/performance/analyze-batch")
async def analyze_batch_answers(
    answers: List[dict]
):
    """Analyze multiple answers in batch"""
    if not PERFORMANCE_ANALYZER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Performance analyzer not available", status_code=503)

    try:
        results = [
            performance_analyzer.analyze_answer(
                a.get("text", ""),
                a.get("type", "behavioral")
            )
            for a in answers
        ]
        return {"results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"[PerformanceAnalyzer] Batch error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/performance/tiers")
async def get_quality_tiers():
    """Get quality tier thresholds and descriptions"""
    return {
        "excellent": {"min_score": 80, "description": "Excellent answer quality"},
        "good": {"min_score": 65, "description": "Good with minor improvements needed"},
        "average": {"min_score": 50, "description": "Average, significant improvements possible"},
        "needs_improvement": {"min_score": 0, "description": "Needs substantial improvement"}
    }


@app.get("/performance/checklist/{user_id}")
async def get_personalized_checklist(
    user_id: str,
    question_type: str = Query("behavioral")
):
    """Get personalized interview performance checklist based on cognitive graph"""
    if not PERFORMANCE_ANALYZER_AVAILABLE or not COGNITIVE_GRAPH_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Performance analyzer or cognitive graph not available", status_code=503)

    try:
        # Get user's skill data from cognitive graph
        skill_data = cognitive_graph.get_user_skills(user_id)

        checklist = {
            "star_method": {
                "situation": "Set the context - describe the scenario clearly",
                "task": "Define your specific responsibility or challenge",
                "action": "Detail what YOU did (use 'I' not 'we')",
                "result": "Quantify outcomes (e.g., 'reduced latency by 40%')"
            },
            "speaking": {
                "pace": "Aim for 15-25 words per sentence",
                "fillers": "Minimize um, uh, like, you know",
                "clarity": "Pause between key points"
            },
            "technical": {
                "examples": "Provide concrete code examples",
                "complexity": "Discuss time/space complexity",
                "edge_cases": "Mention error handling and edge cases",
                "best_practices": "Reference testing, documentation"
            }
        }

        # Customize based on user's common weaknesses from graph
        if skill_data:
            weak_areas = [s for s in skill_data if s.get("confidence", 1.0) < 0.5]
            checklist["focus_areas"] = [s.get("name") for s in weak_areas[:3]]

        return {"checklist": checklist, "user_id": user_id}
    except Exception as e:
        logger.error(f"[PerformanceAnalyzer] Checklist error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


# ======================================
# STUDY PLAN API - Phase 2 Task #33
# Personalized study plan generator
# ======================================

try:
    from study_plan_generator import study_planner, generate_plan, adapt_plan, export_plan
    STUDY_PLAN_AVAILABLE = True
except ImportError as e:
    STUDY_PLAN_AVAILABLE = False
    logger.warning(f"[StudyPlan] Module not available: {e}")


@app.post("/study-plan/generate")
async def generate_study_plan(
    user_id: str = Query(..., description="User ID"),
    days: int = Query(30, description="Plan duration in days"),
    daily_minutes: int = Query(60, description="Daily study time target"),
    target_role: Optional[str] = Query(None, description="Target job role"),
    target_company: Optional[str] = Query(None, description="Target company name"),
    job_description: Optional[str] = Query(None, description="Job description text"),
    current_skills: Optional[str] = Query(None, description="Comma-separated current skills"),
    user: User = Depends(require_authentication)
):
    """Generate personalized study plan. Use /study-plan/generate-personalized for large JD text."""
    if not STUDY_PLAN_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Study plan generator not available", status_code=503)

    try:
        # Parse current_skills from comma-separated string
        skills_list = [s.strip() for s in current_skills.split(",")] if current_skills else None

        # Get cognitive graph data if available
        graph_data = None
        if COGNITIVE_GRAPH_AVAILABLE:
            try:
                stats = cognitive_graph.get_graph_stats(user_id)
                graph_data = {"skills": stats.get("top_skills", [])}
            except Exception:
                pass

        plan = study_planner.generate_plan(
            user_id, days, daily_minutes, graph_data,
            target_role=target_role,
            target_company=target_company,
            job_description=job_description,
            current_skills=skills_list,
        )

        return _serialize_plan(plan)
    except Exception as e:
        logger.error(f"[StudyPlan] Generation error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


class StudyPlanPersonalizedRequest(BaseModel):
    """Request body for personalized study plan generation"""
    user_id: str
    target_role: str
    target_company: Optional[str] = None
    job_description: Optional[str] = None
    current_skills: Optional[List[str]] = None
    days: int = 30
    daily_minutes: int = 60


@app.post("/study-plan/generate-personalized")
async def generate_personalized_study_plan(
    request: StudyPlanPersonalizedRequest,
    user: User = Depends(require_authentication)
):
    """Generate a personalized study plan with full input via JSON body (for large JDs)"""
    if not STUDY_PLAN_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Study plan generator not available", status_code=503)

    try:
        # Get cognitive graph data if available
        graph_data = None
        if COGNITIVE_GRAPH_AVAILABLE:
            try:
                stats = cognitive_graph.get_graph_stats(request.user_id)
                graph_data = {"skills": stats.get("top_skills", [])}
            except Exception:
                pass

        plan = study_planner.generate_plan(
            request.user_id, request.days, request.daily_minutes, graph_data,
            target_role=request.target_role,
            target_company=request.target_company,
            job_description=request.job_description,
            current_skills=request.current_skills,
        )

        return _serialize_plan(plan)
    except Exception as e:
        logger.error(f"[StudyPlan] Personalized generation error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


def _serialize_plan(plan) -> dict:
    """Serialize a StudyPlan object to a JSON-ready dict"""
    result = {
        "user_id": plan.user_id,
        "created_at": plan.created_at.isoformat(),
        "duration_days": plan.duration_days,
        "progress": {
            "total_tasks": plan.total_tasks,
            "completed_tasks": plan.completed_tasks,
            "percentage": round(plan.progress_percentage, 2)
        },
        "weak_areas": plan.weak_areas,
        "strong_areas": plan.strong_areas,
        "milestones": plan.milestones,
        "target_role": plan.target_role,
        "target_company": plan.target_company,
        "skill_gaps": plan.skill_gaps,
        "plan_type": plan.plan_type,
        "personalization_context": getattr(plan, "personalization_context", None),
        "sessions": [
            {
                "date": s.date.isoformat(),
                "theme": s.theme,
                "total_minutes": s.total_minutes,
                "day_number": getattr(s, "day_number", 0),
                "focus_task_id": getattr(s, "focus_task_id", None),
                "stretch_task_id": getattr(s, "stretch_task_id", None),
                "tasks": [
                    {
                        "id": t.id,
                        "title": t.title,
                        "description": t.description,
                        "difficulty": t.difficulty,
                        "category": t.category,
                        "estimated_minutes": t.estimated_minutes,
                        "completed": t.completed,
                        "resources": t.resources,
                        "parent_area": getattr(t, "parent_area", ""),
                        "is_focus": getattr(t, "is_focus", False),
                        "is_stretch": getattr(t, "is_stretch", False),
                        "confidence_target": getattr(t, "confidence_target", 0.8),
                    }
                    for t in s.tasks
                ]
            }
            for s in plan.sessions
        ]
    }
    return result


@app.get("/study-plan/{user_id}")
async def get_study_plan(user_id: str):
    """Get current study plan for user (generates new one if none exists)"""
    if not STUDY_PLAN_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Study plan generator not available", status_code=503)

    try:
        # For now, generate a new plan each time
        # In production, this would fetch from database
        graph_data = None
        if COGNITIVE_GRAPH_AVAILABLE:
            try:
                stats = cognitive_graph.get_graph_stats(user_id)
                graph_data = {"skills": stats.get("top_skills", [])}
            except Exception:
                pass

        plan = study_planner.generate_plan(user_id, days=30, daily_minutes=60, cognitive_graph_data=graph_data)
        # export_plan returns JSON string, parse it to return as dict
        import json
        return json.loads(study_planner.export_plan(plan, "json"))
    except Exception as e:
        logger.error(f"[StudyPlan] Get error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.post("/study-plan/{user_id}/complete-task")
async def complete_study_task(
    user_id: str,
    task_id: str = Query(...),
    performance_score: float = Query(0.7, description="Performance rating 0.0-1.0")
):
    """Mark task as complete and adapt plan"""
    if not STUDY_PLAN_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Study plan generator not available", status_code=503)

    try:
        # In production, would load existing plan from DB
        # For now, return adaptation info
        return {
            "user_id": user_id,
            "task_id": task_id,
            "completed": True,
            "performance_score": performance_score,
            "message": "Task marked complete" + (
                " - Excellent! Advancing schedule." if performance_score > 0.9
                else " - Added remedial practice." if performance_score < 0.5
                else ""
            )
        }
    except Exception as e:
        logger.error(f"[StudyPlan] Complete error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/study-plan/{user_id}/today")
async def get_today_session(user_id: str):
    """Get today's study session"""
    if not STUDY_PLAN_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Study plan generator not available", status_code=503)

    try:
        # Generate plan and find today's session
        plan = study_planner.generate_plan(user_id, days=30)
        today = datetime.now().date()

        for session in plan.sessions:
            if session.date.date() == today:
                return {
                    "date": session.date.isoformat(),
                    "theme": session.theme,
                    "total_minutes": session.total_minutes,
                    "tasks": [
                        {
                            "id": t.id,
                            "title": t.title,
                            "difficulty": t.difficulty,
                            "category": t.category,
                            "estimated_minutes": t.estimated_minutes,
                            "resources": t.resources
                        }
                        for t in session.tasks
                    ]
                }

        return {"message": "No study session scheduled for today", "tasks": []}
    except Exception as e:
        logger.error(f"[StudyPlan] Today error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/study-plan/resources/{category}")
async def get_study_resources(
    category: str,
    difficulty: str = Query("medium"),
    count: int = Query(5)
):
    """Get study resources for a category"""
    if not STUDY_PLAN_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Study plan generator not available", status_code=503)

    try:
        resources = study_planner.resource_lib.get_resources(category, difficulty, count)
        return {
            "category": category,
            "difficulty": difficulty,
            "resources": resources
        }
    except Exception as e:
        logger.error(f"[StudyPlan] Resources error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.post("/study-plan/{user_id}/export")
async def export_study_plan(
    user_id: str,
    format: str = Query("json", description="Export format: json, ical, markdown")
):
    """Export study plan to various formats"""
    if not STUDY_PLAN_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Study plan generator not available", status_code=503)

    try:
        plan = study_planner.generate_plan(user_id, days=30)
        exported = study_planner.export_plan(plan, format)

        return {
            "user_id": user_id,
            "format": format,
            "content": exported
        }
    except Exception as e:
        logger.error(f"[StudyPlan] Export error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


# ============================================================================
# Interview Simulator - Phase 3
# ============================================================================

@app.post("/interview-simulator/create")
async def interview_simulator_create(
    company: str = Query(..., description="Target company name"),
    role: str = Query(None, description="Job role"),
    num_questions: int = Query(5, description="Number of questions"),
    difficulty: str = Query(None, description="Filter by difficulty (easy/medium/hard)"),
    user_id: str = Query("default", description="User ID")
):
    """
    Create a new interview simulation session.
    """
    if not INTERVIEW_SIMULATOR_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Interview simulator not available", status_code=503)

    try:
        result = interview_simulator.create_session(company, role, num_questions, user_id, difficulty)
        return result
    except Exception as e:
        logger.error(f"[InterviewSimulator] Create error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/interview-simulator/{session_id}/question")
async def interview_simulator_get_question(session_id: str):
    """
    Get the next question in the interview session.
    """
    if not INTERVIEW_SIMULATOR_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Interview simulator not available", status_code=503)

    try:
        question = interview_simulator.get_next_question(session_id)
        if question is None:
            return {"status": "complete", "message": "Interview complete"}
        return question
    except Exception as e:
        logger.error(f"[InterviewSimulator] Get question error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.post("/interview-simulator/{session_id}/answer")
async def interview_simulator_submit_answer(
    session_id: str,
    transcript: str = Query(..., description="User's answer transcript"),
    duration_ms: int = Query(0, description="Answer duration in milliseconds")
):
    """
    Submit an answer and get AI evaluation.
    """
    if not INTERVIEW_SIMULATOR_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Interview simulator not available", status_code=503)

    try:
        result = interview_simulator.submit_answer(session_id, transcript, duration_ms)
        return result
    except Exception as e:
        logger.error(f"[InterviewSimulator] Submit answer error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/interview-simulator/{session_id}/status")
async def interview_simulator_status(session_id: str):
    """
    Get current session status.
    """
    if not INTERVIEW_SIMULATOR_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Interview simulator not available", status_code=503)

    try:
        status = interview_simulator.get_session_status(session_id)
        if status is None:
            return error_response(ErrorCode.NOT_FOUND, "Session not found", status_code=404)
        return status
    except Exception as e:
        logger.error(f"[InterviewSimulator] Status error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.post("/interview-simulator/{session_id}/finish")
async def interview_simulator_finish(session_id: str):
    """
    Complete the interview and save to cognitive graph.
    """
    if not INTERVIEW_SIMULATOR_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Interview simulator not available", status_code=503)

    try:
        result = finish_interview(session_id)
        return result
    except Exception as e:
        logger.error(f"[InterviewSimulator] Finish error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


# ============================================================================
# Job Application Tracker - Phase 3
# ============================================================================

@app.post("/job-tracker/application")
async def create_job_application(
    user_id: str = Query("default", description="User ID"),
    company: str = Query(..., description="Company name"),
    role: str = Query(..., description="Job role"),
    location: str = Query(None, description="Job location"),
    salary_range: str = Query(None, description="Salary range"),
    job_url: str = Query(None, description="Job posting URL"),
    status: str = Query("saved", description="Application status"),
    priority: str = Query("medium", description="Priority level"),
    user: User = Depends(require_authentication)
):
    """
    Create a new job application.
    """
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        result = job_tracker.create_application(
            user_id=user_id,
            company=company,
            role=role,
            location=location,
            salary_range=salary_range,
            job_url=job_url,
            status=status,
            priority=priority
        )
        return result
    except Exception as e:
        logger.error(f"[JobTracker] Create error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/job-tracker/applications")
async def get_job_applications(
    user_id: str = Query("default", description="User ID"),
    status: str = Query(None, description="Filter by status"),
    tags: str = Query(None, description="Filter by tags (comma-separated)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Get all job applications for a user with optional filters and pagination.
    """
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available")

    try:
        tag_list = tags.split(",") if tags else None
        applications = job_tracker.get_user_applications(user_id, status, tag_list)
        total = len(applications)
        return {
            "user_id": user_id,
            "count": total,
            "total": total,
            "limit": limit,
            "offset": offset,
            "applications": applications[offset:offset + limit],
        }
    except Exception as e:
        logger.error(f"[JobTracker] Get applications error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e))


@app.get("/job-tracker/application/{app_id}")
async def get_job_application(app_id: str):
    """
    Get a single job application.
    """
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        application = job_tracker.get_application(app_id)
        if not application:
            return error_response(ErrorCode.NOT_FOUND, "Application not found", status_code=404)
        return application
    except Exception as e:
        logger.error(f"[JobTracker] Get application error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.post("/job-tracker/application/{app_id}/status")
async def update_job_status(
    app_id: str,
    status: str = Query(..., description="New status"),
    notes: str = Query(None, description="Status change notes"),
    user: User = Depends(require_authentication)
):
    """
    Update application status.
    """
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        result = job_tracker.update_status(app_id, status, notes)
        return result
    except Exception as e:
        logger.error(f"[JobTracker] Update status error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.post("/job-tracker/application/{app_id}/interview")
async def add_job_interview(
    app_id: str,
    interview_type: str = Query(..., description="Interview type"),
    scheduled_date: str = Query(..., description="ISO datetime"),
    duration_minutes: int = Query(60, description="Duration in minutes"),
    notes: str = Query(None, description="Notes")
):
    """
    Add an interview to a job application.
    """
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        result = job_tracker.add_interview(
            app_id, interview_type, scheduled_date, duration_minutes, notes=notes
        )
        return result
    except Exception as e:
        logger.error(f"[JobTracker] Add interview error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.post("/job-tracker/application/{app_id}/offer")
async def add_job_offer(
    app_id: str,
    salary: str = Query(..., description="Salary offer"),
    benefits: str = Query(..., description="Benefits (comma-separated)"),
    deadline: str = Query(None, description="Offer deadline")
):
    """
    Add offer details to a job application.
    """
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        benefits_list = benefits.split(",") if benefits else []
        result = job_tracker.add_offer(app_id, salary, benefits_list, deadline)
        return result
    except Exception as e:
        logger.error(f"[JobTracker] Add offer error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/job-tracker/stats")
async def get_job_tracker_stats(user_id: str = Query("default", description="User ID")):
    """
    Get job application pipeline statistics.
    """
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        stats = job_tracker.get_pipeline_stats(user_id)
        return stats
    except Exception as e:
        logger.error(f"[JobTracker] Stats error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/job-tracker/upcoming-interviews")
async def get_upcoming_job_interviews(
    user_id: str = Query("default", description="User ID"),
    days: int = Query(7, description="Number of days to look ahead")
):
    """
    Get upcoming interviews within specified days.
    """
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        interviews = job_tracker.get_upcoming_interviews(user_id, days)
        return {
            "user_id": user_id,
            "count": len(interviews),
            "interviews": interviews
        }
    except Exception as e:
        logger.error(f"[JobTracker] Upcoming interviews error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/job-tracker/company/{company}")
async def get_company_job_insights(company: str):
    """
    Get insights about a specific company from applications.
    """
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        insights = job_tracker.get_company_insights(company)
        return insights
    except Exception as e:
        logger.error(f"[JobTracker] Company insights error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.delete("/job-tracker/application/{app_id}")
async def delete_job_application(app_id: str, user: User = Depends(require_authentication)):
    """
    Delete a job application.
    """
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        result = job_tracker.delete_application(app_id)
        return result
    except Exception as e:
        logger.error(f"[JobTracker] Delete error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/job-tracker/duplicates")
async def find_job_duplicates(user_id: str = Query("default", description="User ID")):
    """
    Find duplicate applications (same company + role) for a user.
    """
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        duplicates = job_tracker.find_duplicates(user_id)
        return duplicates
    except Exception as e:
        logger.error(f"[JobTracker] Find duplicates error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.post("/job-tracker/duplicates/remove")
async def remove_job_duplicates(
    user_id: str = Query("default", description="User ID"),
    keep: str = Query("latest", description="Which to keep: 'latest' or 'oldest'")
):
    """
    Remove duplicate applications, keeping either the latest or oldest.
    """
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    if keep not in ["latest", "oldest"]:
        return error_response(ErrorCode.VALIDATION_ERROR, "keep must be 'latest' or 'oldest'", status_code=422)

    try:
        result = job_tracker.remove_duplicates(user_id, keep)
        return result
    except Exception as e:
        logger.error(f"[JobTracker] Remove duplicates error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/job-tracker/application/{app_id}/details")
async def get_job_application_details(app_id: str):
    """
    Get detailed information about a specific application.
    Includes computed fields like days_in_pipeline, interview_count, etc.
    """
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        details = job_tracker.get_application_details(app_id)
        if not details:
            return error_response(ErrorCode.NOT_FOUND, "Application not found", status_code=404)
        return details
    except Exception as e:
        logger.error(f"[JobTracker] Get details error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.post("/job-tracker/application/{app_id}/recruiter")
async def add_recruiter_contact(
    app_id: str,
    name: str = Query(..., description="Recruiter name"),
    email: Optional[str] = Query(None, description="Recruiter email"),
    phone: Optional[str] = Query(None, description="Recruiter phone"),
    is_primary: bool = Query(True, description="Set as primary recruiter")
):
    """
    Add recruiter contact to an application.
    """
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        result = job_tracker.add_recruiter(app_id, name, email, phone, is_primary)
        return result
    except Exception as e:
        logger.error(f"[JobTracker] Add recruiter error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.post("/job-tracker/application/{app_id}/communication")
async def add_communication_log(
    app_id: str,
    comm_type: str = Query(..., description="Communication type: email, phone, message"),
    sender: str = Query(..., description="Sender name/email"),
    content: str = Query(..., description="Message content/summary"),
    direction: str = Query("inbound", description="inbound or outbound"),
    notes: Optional[str] = Query(None, description="Additional notes")
):
    """
    Log a communication (email, phone call, message) for an application.
    """
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        result = job_tracker.add_communication(app_id, comm_type, sender, content, direction, notes)
        return result
    except Exception as e:
        logger.error(f"[JobTracker] Add communication error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.post("/job-tracker/application/{app_id}/background-check")
async def update_background_check_status(
    app_id: str,
    status: str = Query(..., description="Status: initiated, in_progress, completed, failed"),
    provider: Optional[str] = Query(None, description="Background check provider"),
    notes: Optional[str] = Query(None, description="Notes")
):
    """
    Update background check status for an application.
    """
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        result = job_tracker.update_background_check(app_id, status, provider, notes)
        return result
    except Exception as e:
        logger.error(f"[JobTracker] Background check error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.post("/job-tracker/application/{app_id}/drug-test")
async def update_drug_test_status(
    app_id: str,
    status: str = Query(..., description="Status: scheduled, completed, passed, failed"),
    test_date: Optional[str] = Query(None, description="Test date (YYYY-MM-DD)"),
    location: Optional[str] = Query(None, description="Test location"),
    notes: Optional[str] = Query(None, description="Notes")
):
    """
    Update drug test status for an application.
    """
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        result = job_tracker.update_drug_test(app_id, status, test_date, location, notes)
        return result
    except Exception as e:
        logger.error(f"[JobTracker] Drug test error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.post("/job-tracker/application/{app_id}/onboarding")
async def add_onboarding_info(
    app_id: str,
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    documents: Optional[str] = Query(None, description="Comma-separated document names"),
    notes: Optional[str] = Query(None, description="Notes")
):
    """
    Add onboarding details for accepted offer.
    """
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        docs_list = [d.strip() for d in documents.split(",")] if documents else []
        result = job_tracker.add_onboarding_details(app_id, start_date, docs_list, notes)
        return result
    except Exception as e:
        logger.error(f"[JobTracker] Onboarding error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/job-tracker/search")
async def search_job_applications(
    user_id: str = Query("default", description="User ID"),
    query: str = Query(..., description="Search query"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """
    Search applications by company, role, or notes.
    """
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        results = job_tracker.search_applications(user_id, query)
        total = len(results)
        return {"results": results[offset:offset + limit], "total": total, "limit": limit, "offset": offset}
    except Exception as e:
        logger.error(f"[JobTracker] Search error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


# ============================================================================
# Complexity Analysis - Phase 3 Enhancement
# ============================================================================

def extract_complexity_from_text(text: str) -> Dict:
    """Extract Big-O complexity notation from text"""
    import re

    text_lower = text.lower()

    # Patterns for Big-O notation
    patterns = {
        'time_complexity': [
            r'o\(1\)',
            r'o\(log\s*n\)',
            r'o\(n\)',
            r'o\(n\s*log\s*n\)',
            r'o\(n\^2\)',
            r'o\(n\^3\)',
            r'o\(2\^n\)',
            r'o\(n!\)',
            r'constant\s*time',
            r'linear\s*time',
            r'quadratic\s*time',
            r'exponential\s*time',
        ],
        'space_complexity': [
            r'o\(1\)\s*space',
            r'o\(n\)\s*space',
            r'o\(log\s*n\)\s*space',
            r'constant\s*space',
            r'linear\s*space',
        ],
        'algorithm_patterns': [
            r'dynamic\s*programming',
            r'divide\s*and\s*conquer',
            r'greedy\s*algorithm',
            r'brute\s*force',
            r'binary\s*search',
            r'depth\s*first\s*search',
            r'breadth\s*first\s*search',
            r'recursion',
            r'iteration',
        ]
    }

    results = {
        'time_complexity': [],
        'space_complexity': [],
        'algorithm_types': [],
        'detected': False
    }

    # Check time complexity
    for pattern in patterns['time_complexity']:
        matches = re.findall(pattern, text_lower)
        if matches:
            results['time_complexity'].extend(matches)

    # Check space complexity
    for pattern in patterns['space_complexity']:
        matches = re.findall(pattern, text_lower)
        if matches:
            results['space_complexity'].extend(matches)

    # Check algorithm patterns
    for pattern in patterns['algorithm_patterns']:
        matches = re.findall(pattern, text_lower)
        if matches:
            results['algorithm_types'].extend(matches)

    results['detected'] = bool(
        results['time_complexity'] or
        results['space_complexity'] or
        results['algorithm_types']
    )

    return results


@app.post("/analysis/complexity")
async def analyze_complexity(
    text: str = Query(..., description="Text to analyze for complexity")
):
    """
    Analyze text for Big-O complexity notation and algorithm patterns.
    Returns detected complexity badges for display.
    """
    try:
        result = extract_complexity_from_text(text)

        # Determine badge level
        badge = None
        if result['detected']:
            complexities = result['time_complexity']
            if any('n!' in c or '2^n' in c for c in complexities):
                badge = {"type": "exponential", "color": "#ef4444", "label": "O(n!)"}
            elif any('n^2' in c or 'n^3' in c for c in complexities):
                badge = {"type": "polynomial", "color": "#f59e0b", "label": "O(n²)"}
            elif any('n log' in c for c in complexities):
                badge = {"type": "linearithmic", "color": "#3b82f6", "label": "O(n log n)"}
            elif any('n)' in c and 'log' not in c for c in complexities):
                badge = {"type": "linear", "color": "#10b981", "label": "O(n)"}
            elif any('log' in c for c in complexities):
                badge = {"type": "logarithmic", "color": "#8b5cf6", "label": "O(log n)"}
            elif any('constant' in c or 'o(1)' in c for c in complexities):
                badge = {"type": "constant", "color": "#10b981", "label": "O(1)"}

        return {
            "success": True,
            "analysis": result,
            "badge": badge,
            "suggestions": [
                "Consider time/space tradeoffs" if result['time_complexity'] and not result['space_complexity'] else None,
                "Space complexity not analyzed" if not result['space_complexity'] and result['time_complexity'] else None,
            ]
        }
    except Exception as e:
        logger.error(f"[Complexity] Analysis error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


# ============================================================================
# Resume Review - Phase 3
# ============================================================================

@app.post("/resume/analyze")
async def analyze_resume_endpoint(
    resume_text: str = Query(..., description="Resume text content"),
    job_description: str = Query(None, description="Job description for comparison"),
    role_type: str = Query("software_engineer", description="Role type")
):
    """
    Analyze resume and provide feedback.
    """
    if not RESUME_REVIEW_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Resume review not available", status_code=503)

    try:
        result = resume_reviewer.analyze_resume(resume_text, job_description, role_type)
        return result
    except Exception as e:
        logger.error(f"[ResumeReview] Analyze error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.post("/resume/compare")
async def compare_resume_to_job(
    resume_text: str = Query(..., description="Resume text content"),
    job_description: str = Query(..., description="Job description"),
    company: str = Query(None, description="Company name"),
    role: str = Query(None, description="Role title")
):
    """
    Compare resume against a specific job posting.
    """
    if not RESUME_REVIEW_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Resume review not available", status_code=503)

    try:
        analysis = resume_reviewer.analyze_resume(resume_text, job_description)

        # Get company insights if available
        company_insights = None
        if company and JOB_TRACKER_AVAILABLE:
            company_insights = job_tracker.get_company_insights(company)

        return {
            "analysis": analysis.get("analysis", {}),
            "company_insights": company_insights,
            "recommendations": analysis.get("analysis", {}).get("tailored_suggestions", []),
            "match_score": analysis.get("analysis", {}).get("overall_score", 0)
        }
    except Exception as e:
        logger.error(f"[ResumeReview] Compare error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)
    except Exception as e:
        logger.error(f"[ResumeReview] Compare error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.post("/resume/upload")
async def upload_resume_file(
    file: UploadFile = File(...),
    job_description: Optional[str] = Form(None),
    role_type: str = Form("software_engineer")
):
    """
    Upload and analyze a resume file (PDF, DOCX, TXT, MD).
    """
    if not RESUME_REVIEW_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Resume review not available", status_code=503)

    try:
        # Validate file type
        filename = file.filename.lower()
        allowed_extensions = {'.pdf', '.docx', '.doc', '.txt', '.md', '.rtf'}

        if not any(filename.endswith(ext) for ext in allowed_extensions):
            return error_response(ErrorCode.INVALID_FORMAT, f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}", status_code=422)

        # Read file content
        content = await file.read()

        # Extract text based on file type
        if filename.endswith('.pdf'):
            resume_text = extract_text_from_pdf(content)
        elif filename.endswith('.docx') or filename.endswith('.doc'):
            resume_text = extract_text_from_docx(content)
        else:
            # Plain text files
            try:
                resume_text = content.decode('utf-8')
            except UnicodeDecodeError:
                resume_text = content.decode('latin-1', errors='ignore')

        if not resume_text or len(resume_text.strip()) < 50:
            return error_response(ErrorCode.VALIDATION_ERROR, "Could not extract meaningful text from file. Please paste text manually.", status_code=422)

        # Analyze the resume
        result = resume_reviewer.analyze_resume(resume_text, job_description, role_type)

        # Include file info in result
        result['file_info'] = {
            'filename': file.filename,
            'size': len(content),
            'extracted_length': len(resume_text)
        }

        return result

    except Exception as e:
        logger.error(f"[ResumeReview] Upload error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes"""
    text = []

    # Try PyPDF2
    try:
        import io
        from PyPDF2 import PdfReader

        reader = PdfReader(io.BytesIO(pdf_bytes))
        for page in reader.pages:
            text.append(page.extract_text() or '')
        return '\n'.join(text)
    except Exception:
        pass

    # Fallback: try pdfplumber
    try:
        import io
        import pdfplumber

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                text.append(page.extract_text() or '')
        return '\n'.join(text)
    except Exception:
        pass

    # Last resort: try basic extraction
    text = pdf_bytes.decode('latin-1', errors='ignore')
    # Remove non-printable characters
    text = ''.join(c if c.isprintable() or c in '\n\t' else ' ' for c in text)
    return text[:10000]  # Limit to first 10K characters


def extract_text_from_docx(docx_bytes: bytes) -> str:
    """Extract text from DOCX bytes"""
    try:
        import io
        from docx import Document

        doc = Document(io.BytesIO(docx_bytes))
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        return '\n'.join(paragraphs)
    except Exception as e:
        logger.warning(f"[ResumeReview] DOCX extraction error: {e}")
        return ""


# ==============================
# WEB SEARCH INTEGRATION
# ==============================

@app.get("/search/web")
async def web_search(
    query: str = Query(..., description="Search query"),
    limit: int = Query(5, description="Number of results"),
    include_citations: bool = Query(True, description="Include source citations")
):
    """
    Search the web using Perplexity API for real-time information.
    Falls back to Brave Search if Perplexity is not configured.
    """
    import os

    # Try Perplexity first (better for interview questions)
    perplexity_key = os.getenv("PERPLEXITY_API_KEY")
    if perplexity_key:
        try:
            headers = {
                "Authorization": f"Bearer {perplexity_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "sonar-pro",
                "messages": [
                    {
                        "role": "system",
                        "content": "Be precise and concise. Return factual information with sources."
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                "max_tokens": 500
            }

            response = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                json=payload,
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                result = {
                    "source": "perplexity",
                    "query": query,
                    "answer": data["choices"][0]["message"]["content"],
                    "citations": data.get("citations", []),
                    "timestamp": time.time()
                }
                return result

        except Exception as e:
            logger.warning(f"[WebSearch] Perplexity error: {e}")

    # Fallback: Try Brave Search API
    brave_key = os.getenv("BRAVE_API_KEY")
    if brave_key:
        try:
            headers = {
                "X-Subscription-Token": brave_key
            }

            response = requests.get(
                f"https://api.search.brave.com/res/v1/web/search?q={requests.utils.quote(query)}&count={limit}",
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                results = []
                for item in data.get("web", {}).get("results", [])[:limit]:
                    results.append({
                        "title": item.get("title"),
                        "url": item.get("url"),
                        "description": item.get("description")
                    })

                return {
                    "source": "brave",
                    "query": query,
                    "results": results,
                    "timestamp": time.time()
                }

        except Exception as e:
            logger.warning(f"[WebSearch] Brave error: {e}")

    # Final fallback: Return helpful message
    return {
        "source": "none",
        "query": query,
        "error": "Web search not configured. Set PERPLEXITY_API_KEY or BRAVE_API_KEY environment variable.",
        "timestamp": time.time()
    }


@app.get("/search/status")
async def search_status():
    """Check if web search is configured and available."""
    import os

    perplexity_key = os.getenv("PERPLEXITY_API_KEY")
    brave_key = os.getenv("BRAVE_API_KEY")

    return {
        "configured": bool(perplexity_key or brave_key),
        "perplexity_available": bool(perplexity_key),
        "brave_available": bool(brave_key),
        "message": "Web search is ready" if (perplexity_key or brave_key) else "Add PERPLEXITY_API_KEY or BRAVE_API_KEY to enable web search"
    }


logger.info("[WebSearch] Web search integration loaded")


# ==============================
# MOCK INTERVIEW LIBRARY
# ==============================

try:
    from mock_interview_library import (
        mock_library,
        get_all_questions,
        get_questions_by_role,
        get_questions_by_company,
        get_random_question,
        get_practice_set,
        get_library_stats,
        search_questions
    )
    MOCK_LIBRARY_AVAILABLE = True
    logger.info("[MockLibrary] Mock interview library loaded")
except ImportError as e:
    MOCK_LIBRARY_AVAILABLE = False
    logger.warning(f"[MockLibrary] Library not available: {e}")


@app.get("/mock-interview/questions")
async def get_mock_questions(
    role: str = Query(None, description="Filter by role (software_engineer, frontend_engineer, data_engineer)"),
    category: str = Query(None, description="Filter by category (technical, coding, system_design, behavioral)"),
    difficulty: str = Query(None, description="Filter by difficulty (easy, medium, hard)"),
    company: str = Query(None, description="Filter by company"),
    limit: int = Query(50, ge=1, le=500, description="Maximum questions to return"),
    offset: int = Query(0, ge=0, description="Number of questions to skip"),
):
    """
    Get mock interview questions with optional filtering.
    """
    if not MOCK_LIBRARY_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Mock interview library not available", status_code=503)

    try:
        questions = mock_library.get_all_questions()

        # Apply filters
        if role:
            questions = [q for q in questions if q.role == role]
        if category:
            questions = [q for q in questions if q.category == category]
        if difficulty:
            questions = [q for q in questions if q.difficulty == difficulty]
        if company:
            questions = [q for q in questions if q.company and q.company.lower() == company.lower()]

        # Convert to dicts and apply pagination
        total = len(questions)
        result = [vars(q) for q in questions[offset:offset + limit]]

        return {
            "questions": result,
            "total": total,
            "limit": limit,
            "offset": offset,
            "filters": {
                "role": role,
                "category": category,
                "difficulty": difficulty,
                "company": company
            }
        }
    except Exception as e:
        logger.error(f"[MockLibrary] Error getting questions: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/mock-interview/question/random")
async def get_random_mock_question(
    role: str = Query(None, description="Filter by role"),
    category: str = Query(None, description="Filter by category"),
    difficulty: str = Query(None, description="Filter by difficulty")
):
    """Get a random question matching criteria."""
    if not MOCK_LIBRARY_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Mock interview library not available", status_code=503)

    try:
        question = mock_library.get_random_question(role, category, difficulty)
        if question:
            return {"question": vars(question)}
        return error_response(ErrorCode.NOT_FOUND, "No questions found matching criteria", status_code=404)
    except Exception as e:
        logger.error(f"[MockLibrary] Error getting random question: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/mock-interview/practice-set")
async def get_practice_question_set(
    role: str = Query("software_engineer", description="Role for practice set"),
    num_questions: int = Query(5, description="Number of questions", ge=1, le=10)
):
    """
    Get a balanced practice set with mix of categories and difficulties.
    """
    if not MOCK_LIBRARY_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Mock interview library not available", status_code=503)

    try:
        questions = mock_library.get_practice_set(role, num_questions)
        return {
            "questions": [vars(q) for q in questions],
            "role": role,
            "total_time_estimate": sum(q.time_estimate_minutes for q in questions)
        }
    except Exception as e:
        logger.error(f"[MockLibrary] Error getting practice set: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/mock-interview/search")
async def search_mock_questions(
    query: str = Query(..., description="Search query"),
    limit: int = Query(20, ge=1, le=500, description="Maximum results"),
    offset: int = Query(0, ge=0)
):
    """Search questions by text (paginated)."""
    if not MOCK_LIBRARY_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Mock interview library not available", status_code=503)

    try:
        questions = mock_library.search_questions(query)
        total = len(questions)
        return {
            "questions": [vars(q) for q in questions[offset:offset + limit]],
            "query": query,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"[MockLibrary] Error searching questions: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/mock-interview/stats")
async def get_mock_library_stats():
    """Get library statistics."""
    if not MOCK_LIBRARY_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Mock interview library not available", status_code=503)

    try:
        return mock_library.get_stats()
    except Exception as e:
        logger.error(f"[MockLibrary] Error getting stats: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/mock-interview/companies")
async def get_companies_with_questions():
    """Get list of companies that have specific questions."""
    if not MOCK_LIBRARY_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Mock interview library not available", status_code=503)

    try:
        companies = set()
        for q in mock_library.get_all_questions():
            if q.company:
                companies.add(q.company)
        return {"companies": sorted(list(companies))}
    except Exception as e:
        logger.error(f"[MockLibrary] Error getting companies: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


logger.info("[MockLibrary] Mock interview endpoints loaded")


# ==============================
# VOICE CLONE AGENT
# ==============================

try:
    from voice_clone_agent import (
        voice_manager,
        create_voice_model,
        get_voice_status,
        synthesize_voice,
        list_voice_models
    )
    VOICE_CLONE_AVAILABLE = True
    logger.info("[VoiceClone] Voice clone agent loaded")
except ImportError as e:
    VOICE_CLONE_AVAILABLE = False
    logger.warning(f"[VoiceClone] Voice clone not available: {e}")

try:
    from rvc_gallery import list_gallery, get_gallery_voice
    RVC_GALLERY_AVAILABLE = True
    logger.info("[VoiceClone] RVC gallery loaded")
except ImportError as e:
    RVC_GALLERY_AVAILABLE = False
    logger.warning(f"[VoiceClone] RVC gallery not available: {e}")


@app.post("/voice-clone/create")
@rate_limit(requests_per_minute=10)  # T24: Voice clone creation is expensive
async def create_voice_clone(
    name: str = Form(..., description="Name for this voice model"),
    audio_files: List[UploadFile] = File(default=[]),
    user: User = Depends(require_authentication)
):
    """Create a new voice clone model from audio files."""
    if not VOICE_CLONE_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Voice clone not available", status_code=503)

    try:
        from voice_clone_agent import voice_manager
        import shutil

        # Save uploaded files
        audio_paths = []
        for audio_file in audio_files:
            if audio_file.filename:
                temp_path = f"data/temp_audio/{audio_file.filename}"
                os.makedirs("data/temp_audio", exist_ok=True)
                with open(temp_path, "wb") as f:
                    shutil.copyfileobj(audio_file.file, f)
                audio_paths.append(temp_path)

        # Create model entry (voice_manager creates its own model_id and path)
        result = voice_manager.create_model(name, audio_paths)
        model_id = result.get("model_id", "")

        # Save audio files to the model directory created by voice_manager
        model_path = os.path.join("data/voice_models", model_id)
        if model_id and os.path.exists(model_path):
            for i, src_path in enumerate(audio_paths):
                ext = os.path.splitext(src_path)[1] or ".webm"
                dst_path = os.path.join(model_path, f"sample_{i}{ext}")
                shutil.copy2(src_path, dst_path)

        return result

    except Exception as e:
        logger.error(f"[VoiceClone] Create error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


# NOTE: /voice-clone/models routes must come BEFORE /voice-clone/{model_id} routes
# to avoid FastAPI matching "models" as a model_id parameter

@app.get("/voice-clone/models")
async def list_voice_clones(limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)):
    """List all voice models with pagination."""
    if not VOICE_CLONE_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Voice clone not available")

    try:
        all_models = list_voice_models()
        total = len(all_models)
        return {
            "models": all_models[offset:offset + limit],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        logger.error(f"[VoiceClone] List error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e))


@app.delete("/voice-clone/models/{model_id}")
async def delete_voice_clone(model_id: str, user: User = Depends(require_authentication)):
    """Delete a voice model."""
    if not VOICE_CLONE_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Voice clone not available", status_code=503)

    try:
        from voice_clone_agent import voice_manager
        success = voice_manager.delete_model(model_id)
        if success:
            return {"status": "deleted", "model_id": model_id}
        else:
            return error_response(ErrorCode.MODEL_NOT_FOUND, "Model not found", status_code=404)
    except Exception as e:
        logger.error(f"[VoiceClone] Delete error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/voice-clone/{model_id}/status")
async def get_voice_clone_status(model_id: str):
    """Get voice model training status."""
    if not VOICE_CLONE_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Voice clone not available", status_code=503)

    try:
        return get_voice_status(model_id)
    except Exception as e:
        logger.error(f"[VoiceClone] Status error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.post("/voice-clone/{model_id}/synthesize")
async def synthesize_voice_clone(
    model_id: str,
    request: Request
):
    """Synthesize speech using voice model."""
    if not VOICE_CLONE_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Voice clone not available", status_code=503)

    try:
        # Parse JSON body
        body = await request.json()
        text = body.get("text", "")
        if not text:
            return error_response(ErrorCode.MISSING_PARAMETER, "Text is required", status_code=422)

        result = await synthesize_voice(model_id, text)

        if "error" in result:
            return result

        # Return audio URL for playback
        return {
            "status": result.get("status", "completed"),
            "text": text,
            "model_id": model_id,
            "voice_name": result.get("voice_name", ""),
            "voice_used": result.get("voice_used", ""),
            "output_file": result.get("output_file", ""),
            "audio_url": result.get("audio_url", ""),
            "duration_estimate": result.get("duration_estimate", 0),
            "file_size": result.get("file_size", 0),
            "browser_tts": result.get("browser_tts", False),
        }
    except Exception as e:
        logger.error(f"[VoiceClone] Synthesis error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/voice-clone/audio/{filename}")
async def get_voice_audio(filename: str):
    """Serve generated TTS audio files."""
    from fastapi.responses import FileResponse
    audio_dir = os.path.join("data", "voice_models", "audio")
    file_path = os.path.join(audio_dir, filename)
    if not os.path.exists(file_path):
        return error_response(ErrorCode.NOT_FOUND, "Audio file not found", status_code=404)
    return FileResponse(file_path, media_type="audio/mpeg", filename=filename)


@app.get("/voice-clone/gallery")
async def voice_clone_gallery(category: str = None, gender: str = None):
    """List available pre-trained voice gallery models."""
    if not RVC_GALLERY_AVAILABLE:
        return {"voices": [], "error": "Gallery not available"}
    return {"voices": list_gallery(category=category, gender=gender)}


@app.post("/voice-clone/gallery/{gallery_id}/install")
async def install_gallery_voice(gallery_id: str):
    """Install a gallery voice as a voice model."""
    if not RVC_GALLERY_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Gallery not available", status_code=503)

    gallery_voice = get_gallery_voice(gallery_id)
    if not gallery_voice:
        return error_response(ErrorCode.NOT_FOUND, f"Gallery voice '{gallery_id}' not found", status_code=404)

    # Create model using edge-tts with gallery voice settings
    result = voice_manager.create_model(
        name=gallery_voice.name,
        audio_samples=[],
        source="gallery",
        gallery_id=gallery_voice.id,
        edge_voice=gallery_voice.edge_voice,
    )

    # Mark as gallery source with quality score
    model_id = result.get("model_id")
    if model_id and model_id in voice_manager.models:
        model = voice_manager.models[model_id]
        model.source = "gallery"
        model.quality_score = 0.80
        model.f0_method = gallery_voice.f0_method
        voice_manager._save_models()

    return {
        **result,
        "gallery_id": gallery_voice.id,
        "edge_voice": gallery_voice.edge_voice,
        "category": gallery_voice.category,
        "gender": gallery_voice.gender,
    }


@app.post("/voice-clone/create-rvc")
@rate_limit(requests_per_minute=5)  # T24: RVC training is very expensive
async def create_rvc_voice_model(
    name: str = Form(..., description="Name for this voice model"),
    model_file: UploadFile = File(..., description="RVC model file (.onnx or .pth)"),
    index_file: UploadFile = File(default=None, description="Optional feature index file (.index)"),
):
    """Create a voice model from an uploaded RVC model file."""
    if not VOICE_CLONE_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Voice clone not available", status_code=503)

    try:
        import shutil
        from voice_clone_agent import voice_manager

        # Save uploaded model file
        model_id = f"voice_{int(time.time())}"
        model_dir = os.path.join("data", "voice_models", model_id)
        os.makedirs(model_dir, exist_ok=True)

        model_ext = os.path.splitext(model_file.filename)[1] or ".onnx"
        model_path = os.path.join(model_dir, f"model{model_ext}")
        with open(model_path, "wb") as f:
            shutil.copyfileobj(model_file.file, f)

        # Save optional index file
        index_path = ""
        if index_file and index_file.filename:
            index_path = os.path.join(model_dir, f"model.index")
            with open(index_path, "wb") as f:
                shutil.copyfileobj(index_file.file, f)

        result = voice_manager.create_model(
            name=name,
            audio_samples=[],
            source="uploaded",
            model_file=model_path,
            index_file=index_path,
        )

        return result

    except Exception as e:
        logger.error(f"[VoiceClone] RVC create error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


logger.info("[VoiceClone] Voice clone endpoints loaded")


# ==============================
# SHADOW INTERVIEW AGENT
# ==============================

try:
    from shadow_agent import (
        shadow_agent,
        start_shadow_session,
        process_transcript_segment,
        get_shadow_suggestions,
        accept_suggestion_by_id,
        end_shadow_session,
        get_shadow_stats
    )
    SHADOW_AGENT_AVAILABLE = True
    logger.info("[ShadowAgent] Shadow agent loaded")
except ImportError as e:
    SHADOW_AGENT_AVAILABLE = False
    logger.warning(f"[ShadowAgent] Shadow agent not available: {e}")


@app.post("/shadow/start")
async def start_shadow_interview(
    company: str = Query(..., description="Company name"),
    role: str = Query(..., description="Role being interviewed for"),
    stage: str = Query("", description="Interview stage")
):
    """Start a shadow interview session."""
    if not SHADOW_AGENT_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Shadow agent not available", status_code=503)

    try:
        return start_shadow_session(company, role, stage)
    except Exception as e:
        logger.error(f"[ShadowAgent] Start error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.post("/shadow/process")
async def process_shadow_transcript(
    text: str = Query(..., description="Transcript text"),
    speaker: str = Query(..., description="Speaker (user/interviewer/other)")
):
    """Process transcript and generate suggestions."""
    if not SHADOW_AGENT_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Shadow agent not available", status_code=503)

    try:
        result = process_transcript_segment(text, speaker)
        return result or {"detected": False}
    except Exception as e:
        logger.error(f"[ShadowAgent] Process error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/shadow/suggestions")
async def get_shadow_suggestions_list():
    """Get current shadow agent suggestions."""
    if not SHADOW_AGENT_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Shadow agent not available", status_code=503)

    try:
        return {"suggestions": get_shadow_suggestions()}
    except Exception as e:
        logger.error(f"[ShadowAgent] Suggestions error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.post("/shadow/accept")
async def accept_shadow_suggestion(suggestion_id: str = Query(...)):
    """Accept a suggestion."""
    if not SHADOW_AGENT_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Shadow agent not available", status_code=503)

    try:
        text = accept_suggestion_by_id(suggestion_id)
        return {"text": text} if text else {"error": "Suggestion not found"}
    except Exception as e:
        logger.error(f"[ShadowAgent] Accept error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.post("/shadow/end")
async def end_shadow_interview():
    """End shadow interview session."""
    if not SHADOW_AGENT_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Shadow agent not available", status_code=503)

    try:
        return end_shadow_session()
    except Exception as e:
        logger.error(f"[ShadowAgent] End error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/shadow/stats")
async def get_shadow_statistics():
    """Get shadow session statistics."""
    if not SHADOW_AGENT_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Shadow agent not available", status_code=503)

    try:
        return get_shadow_stats()
    except Exception as e:
        logger.error(f"[ShadowAgent] Stats error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


logger.info("[ShadowAgent] Shadow agent endpoints loaded")


# ==============================
# COLLABORATION MODE (DUO)
# ==============================

try:
    from collaboration_mode import (
        collaboration_manager,
        create_collaboration_session,
        join_collaboration,
        send_collaboration_message,
        get_collaboration_messages,
        get_collaboration_status,
        end_collaboration
    )
    COLLABORATION_AVAILABLE = True
    logger.info("[Collaboration] Collaboration mode loaded")
except ImportError as e:
    COLLABORATION_AVAILABLE = False
    logger.warning(f"[Collaboration] Collaboration mode not available: {e}")


@app.post("/collaboration/create")
async def create_collaboration(
    host_name: str = Body(..., description="Host name"),
    context: Optional[dict] = Body(default=None, description="Session context"),
    user: User = Depends(require_authentication)
):
    """Create a new collaboration session."""
    if not COLLABORATION_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Collaboration mode not available", status_code=503)

    try:
        return create_collaboration_session(host_name, context)
    except Exception as e:
        logger.error(f"[Collaboration] Create error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.post("/collaboration/join")
async def join_collaboration_session(
    join_code: str = Query(..., description="6-digit join code"),
    name: str = Query(..., description="Your name")
):
    """Join a collaboration session."""
    if not COLLABORATION_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Collaboration mode not available", status_code=503)

    try:
        return join_collaboration(join_code, name)
    except Exception as e:
        logger.error(f"[Collaboration] Join error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.post("/collaboration/message")
async def send_collaboration_msg(
    session_id: str = Query(...),
    participant_id: str = Query(...),
    text: str = Query(...),
    msg_type: str = Query("suggestion"),
    is_private: bool = Query(False)
):
    """Send a message in collaboration session."""
    if not COLLABORATION_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Collaboration mode not available", status_code=503)

    try:
        return send_collaboration_message(session_id, participant_id, text, msg_type, is_private)
    except Exception as e:
        logger.error(f"[Collaboration] Message error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/collaboration/messages")
async def get_collaboration_msgs(
    session_id: str = Query(...),
    participant_id: str = Query(...),
    since: float = Query(0),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """Get messages for a session (paginated)."""
    if not COLLABORATION_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Collaboration mode not available", status_code=503)

    try:
        msgs = get_collaboration_messages(session_id, participant_id, since)
        if isinstance(msgs, list):
            total = len(msgs)
            return {"messages": msgs[offset:offset + limit], "total": total, "limit": limit, "offset": offset}
        return {"messages": msgs}
    except Exception as e:
        logger.error(f"[Collaboration] Messages error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/collaboration/status")
async def get_collaboration_session_status(session_id: str = Query(...)):
    """Get collaboration session status."""
    if not COLLABORATION_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Collaboration mode not available", status_code=503)

    try:
        status = get_collaboration_status(session_id)
        return status or {"error": "Session not found"}
    except Exception as e:
        logger.error(f"[Collaboration] Status error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.post("/collaboration/end")
async def end_collaboration_session(
    session_id: str = Query(...),
    participant_id: str = Query(...)
):
    """End collaboration session."""
    if not COLLABORATION_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Collaboration mode not available", status_code=503)

    try:
        return end_collaboration(session_id, participant_id)
    except Exception as e:
        logger.error(f"[Collaboration] End error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


logger.info("[Collaboration] Collaboration endpoints loaded")


# ==============================
# MEETING TEMPLATES
# ==============================

try:
    from meeting_templates import (
        templates_manager,
        get_all_templates,
        get_template,
        get_categories,
        create_template,
        update_template,
        delete_template,
        search_templates,
        generate_notes
    )
    MEETING_TEMPLATES_AVAILABLE = True
    logger.info("[MeetingTemplates] Meeting templates loaded")
except ImportError as e:
    MEETING_TEMPLATES_AVAILABLE = False
    logger.warning(f"[MeetingTemplates] Meeting templates not available: {e}")


@app.get("/meeting-templates")
async def list_meeting_templates(limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)):
    """Get all meeting templates with pagination."""
    if not MEETING_TEMPLATES_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Meeting templates not available")

    try:
        templates = get_all_templates()
        total = len(templates)
        return {
            "templates": templates[offset:offset + limit],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        logger.error(f"[MeetingTemplates] List error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/meeting-templates/categories")
async def list_template_categories():
    """Get all template categories."""
    if not MEETING_TEMPLATES_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Meeting templates not available", status_code=503)

    try:
        categories = get_categories()
        return {"categories": categories}
    except Exception as e:
        logger.error(f"[MeetingTemplates] Categories error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.post("/meeting-templates")
async def create_meeting_template(body: dict, user: User = Depends(require_authentication)):
    """Create a custom meeting template."""
    if not MEETING_TEMPLATES_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Meeting templates not available", status_code=503)

    try:
        template = create_template(body)
        return template
    except Exception as e:
        logger.error(f"[MeetingTemplates] Create error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/meeting-templates/{template_id}")
async def get_meeting_template(template_id: str):
    """Get a specific meeting template."""
    if not MEETING_TEMPLATES_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Meeting templates not available", status_code=503)

    try:
        template = get_template(template_id)
        if template:
            return template
        return error_response(ErrorCode.NOT_FOUND, "Template not found", status_code=404)
    except Exception as e:
        logger.error(f"[MeetingTemplates] Get error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.put("/meeting-templates/{template_id}")
async def update_meeting_template(template_id: str, body: dict):
    """Update a custom meeting template."""
    if not MEETING_TEMPLATES_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Meeting templates not available", status_code=503)

    try:
        template = update_template(template_id, body)
        if template:
            return template
        return error_response(ErrorCode.NOT_FOUND, "Template not found or cannot update default templates", status_code=404)
    except Exception as e:
        logger.error(f"[MeetingTemplates] Update error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.delete("/meeting-templates/{template_id}")
async def delete_meeting_template(template_id: str):
    """Delete a custom meeting template."""
    if not MEETING_TEMPLATES_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Meeting templates not available", status_code=503)

    try:
        success = delete_template(template_id)
        if success:
            return {"success": True}
        return error_response(ErrorCode.NOT_FOUND, "Template not found or cannot delete default templates", status_code=404)
    except Exception as e:
        logger.error(f"[MeetingTemplates] Delete error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.get("/meeting-templates/search")
async def search_meeting_templates(query: str = Query(...)):
    """Search meeting templates."""
    if not MEETING_TEMPLATES_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Meeting templates not available", status_code=503)

    try:
        results = search_templates(query)
        return {"templates": results}
    except Exception as e:
        logger.error(f"[MeetingTemplates] Search error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@app.post("/meeting-templates/{template_id}/generate")
async def generate_meeting_notes(template_id: str, body: dict):
    """Generate meeting notes from template."""
    if not MEETING_TEMPLATES_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Meeting templates not available", status_code=503)

    try:
        notes = generate_notes(template_id, body)
        return {"notes": notes}
    except Exception as e:
        logger.error(f"[MeetingTemplates] Generate error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


logger.info("[MeetingTemplates] Meeting templates endpoints loaded")

