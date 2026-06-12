"""
Regression test for Fix #33 — `backend/data/recordings/` should not
contain stub debug files.

Background: the recordings directory is the production data store for
`backend/modules/video/recording_manager.py`. It is recreated on every
import via `os.makedirs(RECORDINGS_DIR, exist_ok=True)` and all `*.json`
files in it are loaded into the in-memory `_sessions` dict on startup
(see `RecordingManager._load_existing`). So any debug file in this
directory silently becomes a "real" recording for the running app.

The audit found two such stubs (385 bytes each, both titled "Verify Test",
both with `size_bytes: 0` and `file_path: null`, both with a hardcoded
`user_id` that doesn't match any real user). They got picked up on every
app start, surfacing as a "completed" recording in any list call.

This test:
- Loads every `*.json` in the recordings directory
- Asserts none has the known stub signature: `title == "Verify Test"`
  (the two deleted files matched that exactly)
- Also asserts no recording has the contradictory
  `status=completed, size_bytes=0, file_path=null` signature
- Also asserts the directory exists (it's created on import but a
  delete-all scenario is still useful to detect)

We compute RECORDINGS_DIR directly (same as `recording_manager.py:16`)
to avoid the modules/ path dance — the module is self-contained stdlib
imports so a load via importlib would also work, but the constant
duplication is simpler and the test is more readable.
"""

import json
import os
import sys
from pathlib import Path

import pytest

_BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _BACKEND)

# Same value as backend/modules/video/recording_manager.py:16
RECORDINGS_DIR = os.path.join(_BACKEND, "data", "recordings")


class TestFix33NoStubRecordings:
    """Catches debug leftover files in the recordings directory."""

    def test_recordings_dir_exists(self):
        # The directory is created by `os.makedirs(..., exist_ok=True)` at
        # import time in `modules/video/recording_manager.py:17`. If this
        # fails, that call has been removed and the dir is at risk of
        # disappearing on a clean checkout.
        assert os.path.isdir(RECORDINGS_DIR), (
            f"recordings dir missing: {RECORDINGS_DIR}. "
            f"recording_manager.py should create it via os.makedirs(..., exist_ok=True)."
        )

    def test_no_verify_test_stubs(self):
        """No recording file should be titled 'Verify Test' (Fix #33 signature)."""
        if not os.path.isdir(RECORDINGS_DIR):
            pytest.skip("recordings dir does not exist")

        for fname in os.listdir(RECORDINGS_DIR):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(RECORDINGS_DIR, fname)
            try:
                with open(fpath) as f:
                    data = json.load(f)
            except (OSError, json.JSONDecodeError):
                # Don't fail the test on a broken file — that's a different
                # concern. We only care about the stub signature.
                continue

            title = data.get("title")
            assert title != "Verify Test", (
                f"Found debug stub recording in {fpath!r} with title 'Verify Test'. "
                f"Fix #33 deleted two such files; this is a regression. "
                f"Stub signature: id={data.get('id')!r}, user_id={data.get('user_id')!r}, "
                f"size_bytes={data.get('size_bytes')!r}, file_path={data.get('file_path')!r}."
            )

    def test_no_zero_size_completed_stubs(self):
        """A 'completed' recording with size_bytes=0 and file_path=null is a stub.

        Real completed recordings have a non-null file_path (the saved
        webm on disk) and size_bytes > 0. The two audit stubs had
        size_bytes=0, file_path=null, status=completed — a contradiction
        that proves nothing was actually recorded.
        """
        if not os.path.isdir(RECORDINGS_DIR):
            pytest.skip("recordings dir does not exist")

        for fname in os.listdir(RECORDINGS_DIR):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(RECORDINGS_DIR, fname)
            try:
                with open(fpath) as f:
                    data = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue

            if (data.get("status") == "completed"
                    and data.get("size_bytes") == 0
                    and data.get("file_path") is None):
                pytest.fail(
                    f"Stub-like recording in {fpath!r}: status=completed, "
                    f"size_bytes=0, file_path=null. Fix #33 deleted two such files; "
                    f"this is a regression. id={data.get('id')!r}, "
                    f"user_id={data.get('user_id')!r}, title={data.get('title')!r}."
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
