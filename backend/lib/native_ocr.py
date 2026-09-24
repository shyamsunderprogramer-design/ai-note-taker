"""Local macOS OCR. Build the small Vision helper once into a private cache."""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading

_build_lock = threading.Lock()
_binary = None


def extract_native_text(image_b64):
    """Return text (including empty text), or None if native OCR is unavailable."""
    if sys.platform != 'darwin':
        return None
    global _binary
    try:
        raw = base64.b64decode(image_b64.split(',', 1)[-1], validate=True)
        if not raw or len(raw) > 20 * 1024 * 1024:
            return None
        with _build_lock:
            if _binary is None or not _binary.exists():
                source = Path(__file__).with_suffix('.swift')
                digest = hashlib.sha256(source.read_bytes()).hexdigest()[:16]
                # Private per-user directory; never execute a shared /tmp binary.
                directory = Path(tempfile.gettempdir()) / f'ant-native-ocr-{os.getuid()}'
                directory.mkdir(mode=0o700, exist_ok=True)
                if directory.is_symlink() or directory.stat().st_uid != os.getuid():
                    return None
                os.chmod(directory, 0o700)
                target = directory / f'ocr-{digest}'
                if not target.exists():
                    temporary = directory / f'build-{os.getpid()}'
                    subprocess.run(['/usr/bin/xcrun','swiftc',str(source),'-O','-module-cache-path',str(directory / 'modules'),'-o',str(temporary)],
                                   check=True, capture_output=True, timeout=60)
                    temporary.replace(target)
                _binary = target
        result = subprocess.run([str(_binary)], input=raw, capture_output=True, check=True, timeout=15)
        return json.loads(result.stdout)['text']
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        return None
