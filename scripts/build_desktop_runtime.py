"""Build a checksum-verified, relocatable Python runtime for desktop packages."""
import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def python_executable(directory):
    return directory / ("python.exe" if sys.platform == "win32" else "bin/python3")


def build_runtime(destination, install_dependencies=True):
    manifest = json.loads((ROOT / "scripts/python-runtime.json").read_text())
    arch = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "x64", "amd64": "x64"}[platform.machine().lower()]
    target = manifest["targets"][f"{sys.platform}-{arch}"]
    filename = f"cpython-{manifest['version']}%2B{manifest['build']}-{target['triple']}-install_only_stripped.tar.gz"
    url = f"https://github.com/astral-sh/python-build-standalone/releases/download/{manifest['build']}/{filename}"
    if destination.exists():
        raise FileExistsError(f"Refusing to replace existing runtime: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ant-python-", dir=destination.parent) as temporary:
        staging = Path(temporary)
        archive = staging / "python.tar.gz"
        with urllib.request.urlopen(url, timeout=120) as response, archive.open("wb") as output:
            shutil.copyfileobj(response, output)
        with archive.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        if digest != target["sha256"]:
            raise ValueError("Python runtime checksum does not match the pinned manifest")
        with tarfile.open(archive) as package:
            package.extractall(staging, filter="data")
        shutil.move(str(staging / "python"), destination)
    python = python_executable(destination)
    # Prove that the interpreter has its own standard library after relocation.
    subprocess.run([str(python), "-I", "-c", "import ssl, sqlite3, ctypes; print('Standalone Python ready')"], check=True)
    if install_dependencies:
        subprocess.run([str(python), "-I", "-m", "pip", "install", "--no-cache-dir", "-r", str(ROOT / "backend/requirements.txt")], check=True)
        subprocess.run([str(python), "-I", "-m", "pip", "check"], check=True)
    (destination / "ANT-RUNTIME.json").write_text(json.dumps({
        "version": manifest["version"], "build": manifest["build"],
        "target": target["triple"], "sha256": target["sha256"],
    }, indent=2) + "\n")
    print(f"Runtime prepared: {python}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=ROOT / "AINT_Python")
    parser.add_argument("--skip-dependencies", action="store_true", help="Verify the interpreter download only")
    args = parser.parse_args()
    build_runtime(args.destination.resolve(), not args.skip_dependencies)
