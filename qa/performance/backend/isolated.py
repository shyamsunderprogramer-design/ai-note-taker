"""Run backend tests/server in a disposable source copy, without personal data.

Usage: AINT_Venv/bin/python qa/performance/backend/isolated.py test [pytest args]
       AINT_Venv/bin/python qa/performance/backend/isolated.py serve --port 8046
Artifacts remain under the printed temporary directory for inspection.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]


def prepare():
    work = Path(tempfile.mkdtemp(prefix="ant-isolated-"))
    backend = work / "backend"
    shutil.copytree(ROOT / "backend", backend, ignore=shutil.ignore_patterns(
        ".env", ".env.*", "*.db", "*.db-*", "*.sqlite*", "data", "logs",
        "uploads", "recordings", "__pycache__", ".pytest_cache", "*.pyc"))
    # Only carry process essentials; never inherit provider credentials or DB URLs.
    env = {k: os.environ[k] for k in ("PATH", "TMPDIR", "SYSTEMROOT", "LANG") if k in os.environ}
    paths = [backend, backend / "core"]
    paths.extend(p for p in (backend / "modules").iterdir() if p.is_dir())
    env.update(PYTHONPATH=os.pathsep.join(map(str, paths)), TESTING="true",
               ANT_DATA_DIR=str(work / "data"), USE_SQLITE="true", FORCE_SQLITE="true",
               DATABASE_URL=f"sqlite+aiosqlite:///{work / 'data' / 'test.db'}",
               AUTH_REQUIRED="false", ANT_SKIP_ALEMBIC="1", HF_HUB_OFFLINE="1",
               JWT_SECRET_KEY=secrets.token_hex(32), HTTPS_REQUIRED="false",
               TEST_API_URL="http://127.0.0.1:8046", ANT_DISABLE_KEY_SERVER="1",
               CORS_ORIGINS="http://127.0.0.1:8048")
    return work, backend, env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["test", "serve"])
    parser.add_argument("--port", type=int, default=8046)
    args, rest = parser.parse_known_args()
    work, backend, env = prepare()
    env["TEST_API_URL"] = f"http://127.0.0.1:{args.port}"
    if args.mode == "serve":
        command = [sys.executable, "-m", "uvicorn", "core.main:app", "--host", "127.0.0.1", "--port", str(args.port)]
    else:
        command = [sys.executable, "-m", "pytest", *(rest or ["tests", "core/test_startup.py"]), f"--junitxml={work / 'pytest.xml'}"]
    print(f"Isolated run: {work}", flush=True)
    (work / "run.json").write_text(json.dumps({"mode": args.mode, "command": command, "data": env["ANT_DATA_DIR"], "api": env["TEST_API_URL"]}, indent=2))
    child = subprocess.Popen(command, cwd=backend, env=env)
    try:
        result = child.wait()
    except KeyboardInterrupt:
        child.terminate()
        try:
            result = child.wait(timeout=15)
        except subprocess.TimeoutExpired:
            child.kill()
            result = child.wait()
    raise SystemExit(result)


if __name__ == "__main__":
    main()
