"""Writable desktop storage, with legacy source-install locations preserved."""
import os
from pathlib import Path


def storage_path(legacy_path, *parts):
    root = os.getenv("ANT_DATA_DIR")
    return Path(root).expanduser().resolve().joinpath(*parts) if root else Path(legacy_path)
