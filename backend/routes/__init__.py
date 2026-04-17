"""Route modules for the AI backend API.

Each module defines an ``APIRouter`` instance that can be mounted by
``app.include_router(routes.<module>.router)`` in main.py.

Modules are imported lazily to avoid import errors when optional
dependencies are missing. Import only what you need:
    from routes.deps import state
    from routes.health import router as health_router
"""

# deps is always safe to import (no optional dependencies)
from . import deps

__all__ = ["deps"]