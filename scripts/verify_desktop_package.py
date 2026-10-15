"""Exercise the packaged interpreter and authentication using disposable user data."""
import argparse
import json
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def verify(resources):
    runtime = resources / "python"
    executable = runtime / ("python.exe" if sys.platform == "win32" else "bin/python3")
    import_check = (
        "import ssl, sqlite3, ctypes, uvicorn, fastapi, jwt, bcrypt, faster_whisper; "
        "from pathlib import Path; import sys; "
        "assert Path(sys.prefix).resolve() == Path(sys.argv[1]).resolve(); "
        "print('Packaged runtime imports passed')"
    )
    subprocess.run([str(executable), "-I", "-c", import_check, str(runtime)], check=True)
    with tempfile.TemporaryDirectory(prefix="ant-package-smoke-") as temporary:
        user_dir = Path(temporary)
        data = user_dir / "data"
        data.mkdir()
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        environment = {
            **os.environ, "PYTHONPATH": str(resources / "backend"),
            "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
            "ANT_DATA_DIR": str(data), "ANT_ENCRYPTION_KEY_FILE": str(data / "master.key"),
            "ANT_VOICE_STORAGE_DIR": str(data / "voice_models"),
            "ANT_MEETING_TEMPLATES_DIR": str(data / "meeting_templates"),
            "AUTH_REQUIRED": "true", "CLOUD_MODE": "true", "HTTPS_REQUIRED": "false",
            "JWT_SECRET_KEY": secrets.token_hex(32), "KEY_SERVER_SECRET": secrets.token_hex(32),
            "DATABASE_URL": "", "FORCE_SQLITE": "true", "EMBEDDING_ENABLED": "false",
            "CLASSIFIER_ENABLED": "false", "HF_HUB_OFFLINE": "1",
        }
        base = f"http://127.0.0.1:{port}"

        def request(endpoint, fields=None, token=None):
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            body = urllib.parse.urlencode(fields).encode() if fields is not None else None
            req = urllib.request.Request(base + endpoint, data=body, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as response:
                return json.load(response)

        log_path = user_dir / "backend.log"
        with log_path.open("w+") as log:
            server = subprocess.Popen([str(executable), "-m", "uvicorn", "core.main:app",
                                       "--host", "127.0.0.1", "--port", str(port), "--no-access-log"],
                                      cwd=user_dir, env=environment, stdout=log, stderr=log)
            try:
                for _ in range(120):
                    if server.poll() is not None:
                        raise RuntimeError("Packaged backend exited before becoming healthy")
                    try:
                        request("/health")
                        break
                    except (urllib.error.URLError, TimeoutError):
                        time.sleep(1)
                else:
                    raise TimeoutError("Packaged backend did not become healthy")
                password = "Rc!" + secrets.token_urlsafe(18)
                request("/auth/register", {"username": "release_smoke", "email": "release-smoke@example.com", "password": password})
                login = request("/auth/login", {"username": "release_smoke", "password": password})
                token = login["access_token"]
                account = request("/auth/me", token=token)
                if account.get("username") != "release_smoke":
                    raise RuntimeError("Packaged authentication returned the wrong account")
                if not (data / "ainotetaker.db").is_file():
                    raise RuntimeError("Packaged account database was not stored in the user data directory")
                print("Packaged backend health, registration, login and user-data storage passed")
            except Exception:
                log.flush()
                print(log_path.read_text(errors="replace")[-20000:])
                raise
            finally:
                server.terminate()
                try:
                    server.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=10)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resources", type=Path)
    args = parser.parse_args()
    if args.resources:
        resources = args.resources.resolve()
    else:
        output = Path(__file__).resolve().parent.parent / "electron/dist"
        candidates = list(output.glob("mac*/*.app/Contents/Resources")) + list(output.glob("*-unpacked/resources"))
        if len(candidates) != 1:
            raise RuntimeError(f"Expected exactly one packaged app, found {len(candidates)}")
        resources = candidates[0]
    verify(resources)
