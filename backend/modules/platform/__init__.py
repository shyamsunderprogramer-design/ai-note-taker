"""
Platform Modules - Cloud, Document Store, MCP, Unified Database
"""

__all__ = ["cloud_providers", "document_store", "mcp_server", "unified_database", "get_db", "db"]

from . import cloud_providers
from . import document_store
from . import mcp_server
from .unified_database import UnifiedDatabase, get_db, db

# Convenience exports
def migrate_from_json(data_dir: str = None) -> dict:
    """
    Migrate existing JSON files to unified database.
    Call this on first run to migrate user data.

    `data_dir` defaults to backend/data/ (resolved from this file's location)
    so the path is stable regardless of server CWD. Pass an explicit path to
    override (e.g. when migrating from a legacy install).
    """
    import json
    import os
    from pathlib import Path

    if data_dir is None:
        # backend/modules/platform/__init__.py -> backend/data/
        data_dir = str(Path(__file__).resolve().parent.parent.parent / "data")

    results = {"migrated": [], "errors": []}
    db = get_db()

    # Migrate conversations
    conversations_dir = Path(data_dir) / "conversations"
    if conversations_dir.exists():
        for json_file in conversations_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    conv = json.load(f)
                if db.save_conversation(conv):
                    results["migrated"].append(f"conversation/{conv.get('id')}")
            except Exception as e:
                results["errors"].append(f"{json_file.name}: {str(e)}")

    # Migrate settings (config.json)
    config_file = Path(data_dir) / "config.json"
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            for key, value in config.items():
                db.set_setting(key, value, category="config")
            results["migrated"].append("config")
        except Exception as e:
            results["errors"].append(f"config: {str(e)}")

    return results
