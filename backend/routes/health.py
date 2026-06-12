"""Route module for health checks and rate-limit status."""
import logging
import os

from fastapi import APIRouter, Query, Request

from security import rate_limiter

# Database availability
try:
    from database import db_manager, HAS_SQLALCHEMY
    DATABASE_AVAILABLE = HAS_SQLALCHEMY
except ImportError:
    DATABASE_AVAILABLE = False

# Cognitive graph for health/modules
try:
    from cognitive_graph import get_driver
    COGNITIVE_GRAPH_AVAILABLE = True
except ImportError:
    COGNITIVE_GRAPH_AVAILABLE = False

# Voice clone for health/modules
try:
    from voice_clone_agent import voice_manager
    VOICE_CLONE_AVAILABLE = True
except ImportError:
    VOICE_CLONE_AVAILABLE = False

# RVC gallery for health/modules
try:
    from rvc_gallery import list_gallery
    RVC_GALLERY_AVAILABLE = True
except ImportError:
    RVC_GALLERY_AVAILABLE = False

# Collaboration for health/modules
try:
    from collaboration_mode import collaboration_manager
    COLLABORATION_AVAILABLE = True
except ImportError:
    COLLABORATION_AVAILABLE = False

# Mock interview library for health/modules
try:
    from mock_interview_library import mock_library
    MOCK_LIBRARY_AVAILABLE = True
except ImportError:
    MOCK_LIBRARY_AVAILABLE = False

# Study plan for health/modules
try:
    from study_plan_generator import study_planner
    STUDY_PLAN_AVAILABLE = True
except ImportError:
    STUDY_PLAN_AVAILABLE = False

# Interview simulator for health/modules
try:
    from interview_simulator import interview_simulator
    INTERVIEW_SIMULATOR_AVAILABLE = True
except ImportError:
    INTERVIEW_SIMULATOR_AVAILABLE = False

# Job tracker for health/modules
try:
    from job_tracker import job_tracker
    JOB_TRACKER_AVAILABLE = True
except ImportError:
    JOB_TRACKER_AVAILABLE = False

logger = logging.getLogger("routes.health")

# Shared state — set by main.py at include time or via module-level defaults
CURRENT_MODE = "auto"

router = APIRouter()


@router.get("/")
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


@router.get("/health")
def health():
    return health_check()


@router.get("/health/database")
async def health_database():
    """Check PostgreSQL database connectivity"""
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
            "message": "An internal error occurred"
        }


@router.get("/health/modules")
async def health_modules():
    """Feature health dashboard - show which modules are available"""
    # Check Neo4j connection
    neo4j_connected = False
    if COGNITIVE_GRAPH_AVAILABLE:
        try:
            driver = get_driver()
            neo4j_connected = driver is not None
        except Exception:
            neo4j_connected = False

    # Check encryption key
    encryption_available = bool(os.getenv("ENCRYPTION_KEY"))

    # Check AI providers
    def has_provider_key(provider, env_var):
        try:
            from lib.http_client import sync_client
            headers = {}
            key_secret = os.getenv("KEY_SERVER_SECRET", "")
            if key_secret:
                headers["X-Key-Server-Secret"] = key_secret
            resp = sync_client.post(
                "http://127.0.0.1:18000/get-key",
                json={"provider": provider},
                headers=headers,
                timeout=1,
                skip_ssrf_check=True  # nosec B106 — internal key server
            )
            if resp.status_code == 200:
                return bool(resp.json().get("apiKey"))
        except Exception:
            pass  # nosec B110
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
            pass  # nosec B110

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


@router.get("/rate-limit/status")
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