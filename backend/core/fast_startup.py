"""
fast_startup.py - Optimized startup for FastAPI backend
Uses lazy imports to reduce startup time
"""

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

# Configure logging immediately
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("fast_startup")

# Add paths
_project_root = Path(__file__).parent.parent
_core_dir = Path(__file__).parent
for _p in [str(_project_root), str(_core_dir)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

_modules_root = _project_root / "modules"
if str(_modules_root) not in sys.path:
    sys.path.insert(0, str(_modules_root))

# ═══════════════════════════════════════════════════════════════════════════════
# LAZY IMPORTS - Load heavy modules only when needed
# ═══════════════════════════════════════════════════════════════════════════════

class LazyModule:
    """Lazy module loader - imports only on first access"""
    def __init__(self, name):
        self.name = name
        self._module = None

    def __getattr__(self, item):
        if self._module is None:
            logger.info(f"[LazyImport] Loading module: {self.name}")
            self._module = __import__(self.name, fromlist=[''])
        return getattr(self._module, item)


# Core modules (always load)
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Lazy heavy modules
class ModuleLoader:
    """Container for lazy-loaded modules"""

    @property
    def np(self):
        if not hasattr(self, '_np'):
            import numpy as np
            self._np = np
        return self._np

    @property
    def ai_router(self):
        if not hasattr(self, '_ai_router'):
            from ai_router import build_prompt, clean_ai_output, route_ai, route_ai_stream
            self._ai_router = {
                'build_prompt': build_prompt,
                'clean_ai_output': clean_ai_output,
                'route_ai': route_ai,
                'route_ai_stream': route_ai_stream
            }
        return self._ai_router

    @property
    def whisper(self):
        if not hasattr(self, '_whisper'):
            try:
                from whisper_handler import (
                    BrowserTranscriber, transcribe, transcribe_audio, warmup
                )
                self._whisper = {
                    'available': True,
                    'BrowserTranscriber': BrowserTranscriber,
                    'transcribe': transcribe,
                    'transcribe_audio': transcribe_audio,
                    'warmup': warmup
                }
            except ImportError:
                self._whisper = {'available': False}
        return self._whisper

    @property
    def database(self):
        if not hasattr(self, '_database'):
            try:
                from database import (
                    db_manager, init_database, close_database,
                    UserRepository, ConversationRepository
                )
                self._database = {
                    'available': True,
                    'db_manager': db_manager,
                    'init_database': init_database,
                    'close_database': close_database,
                    'UserRepository': UserRepository,
                    'ConversationRepository': ConversationRepository
                }
            except ImportError:
                self._database = {'available': False}
        return self._database

    @property
    def unified_db(self):
        if not hasattr(self, '_unified_db'):
            try:
                from platform import get_db
                self._unified_db = {'available': True, 'db': get_db()}
            except ImportError:
                self._unified_db = {'available': False}
        return self._unified_db

# Global module loader
modules = ModuleLoader()


# ═══════════════════════════════════════════════════════════════════════════════
# FAST ENDPOINTS - Minimal endpoints that load quickly
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi import APIRouter

fast_router = APIRouter()


@fast_router.get("/health")
async def health_check():
    """Ultra-fast health check - no heavy imports"""
    return {
        "status": "ok",
        "version": "1.0.0",
        "optimized": True
    }


@fast_router.get("/ready")
async def readiness_check():
    """Check if heavy modules are loaded"""
    status = {
        "ready": True,
        "whisper": modules.whisper.get('available', False),
        "database": modules.database.get('available', False),
        "unified_db": modules.unified_db.get('available', False)
    }
    return status


# ═══════════════════════════════════════════════════════════════════════════════
# BACKGROUND INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio

async def background_init():
    """Initialize heavy modules in background"""
    logger.info("[BackgroundInit] Starting...")

    # Initialize in order of priority
    tasks = []

    # 1. Initialize unified database (fast)
    if modules.unified_db.get('available'):
        tasks.append(_init_unified_db())

    # 2. Initialize whisper (slow)
    if modules.whisper.get('available'):
        tasks.append(_init_whisper())

    # 3. Initialize postgres database (if available)
    if modules.database.get('available'):
        tasks.append(_init_database())

    # Run in parallel
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

    logger.info("[BackgroundInit] Complete")


async def _init_unified_db():
    """Initialize unified SQLite database"""
    try:
        db = modules.unified_db['db']
        stats = db.get_stats()
        logger.info(f"[UnifiedDB] Initialized: {stats}")
    except Exception as e:
        logger.error(f"[UnifiedDB] Init failed: {e}")


async def _init_whisper():
    """Initialize whisper models"""
    try:
        warmup_fn = modules.whisper.get('warmup')
        if warmup_fn:
            warmup_fn()
            logger.info("[Whisper] Model warmed up")
    except Exception as e:
        logger.error(f"[Whisper] Init failed: {e}")


async def _init_database():
    """Initialize PostgreSQL database"""
    try:
        init_fn = modules.database.get('init_database')
        if init_fn:
            init_fn()
            logger.info("[Database] PostgreSQL initialized")
    except Exception as e:
        logger.error(f"[Database] Init failed: {e}")


def start_background_init():
    """Start background initialization in thread"""
    import threading

    def run_async_init():
        try:
            asyncio.run(background_init())
        except Exception as e:
            logger.error(f"[BackgroundInit] Error: {e}")

    thread = threading.Thread(target=run_async_init, daemon=True)
    thread.start()
    return thread


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY - Optimized FastAPI app
# ═══════════════════════════════════════════════════════════════════════════════

def create_optimized_app():
    """Create FastAPI app with lazy loading"""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI(
        title="ANT API (Optimized)",
        version="2.0.0",
        docs_url="/docs" if __debug__ else None,
        redoc_url="/redoc" if __debug__ else None
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include fast routes
    app.include_router(fast_router, tags=["fast"])

    # Start background init
    @app.on_event("startup")
    async def startup_event():
        logger.info("[Startup] FastAPI initializing...")
        start_background_init()
        logger.info("[Startup] Background init started")

    return app


if __name__ == "__main__":
    import uvicorn

    app = create_optimized_app()

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info",
        access_log=False  # Reduce noise
    )
