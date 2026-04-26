"""
start_server.py - Production-ready startup with auto SSL

Usage:
    python start_server.py              # HTTP mode (dev)
    python start_server.py --ssl        # Auto-generate self-signed cert (dev HTTPS)
    python start_server.py --prod       # Production mode (requires SSL_CERT_FILE + SSL_KEY_FILE)

Environment:
    SSL_CERT_FILE   - Path to SSL certificate (PEM)
    SSL_KEY_FILE    - Path to SSL private key (PEM)
    HTTPS_REQUIRED  - Set "true" to enable HTTPS redirect middleware (default: true)
    HSTS_MAX_AGE    - HSTS max-age in seconds (default: 31536000)
"""

import os
import sys
from pathlib import Path

# Add paths
_project_root = Path(__file__).parent.parent
_core_dir = Path(__file__).parent
for _p in [str(_project_root), str(_core_dir)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

_modules_root = _project_root / "modules"
if str(_modules_root) not in sys.path:
    sys.path.insert(0, str(_modules_root))

from generate_ssl import generate_self_signed_cert, get_ssl_context


def main():
    import uvicorn
    import argparse

    parser = argparse.ArgumentParser(description="Start AI Note Taker backend")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=8000, help="Bind port")
    parser.add_argument("--ssl", action="store_true", help="Enable HTTPS with auto-generated self-signed cert")
    parser.add_argument("--prod", action="store_true", help="Production mode: requires SSL_CERT_FILE and SSL_KEY_FILE")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    args = parser.parse_args()

    ssl_cert = os.getenv("SSL_CERT_FILE", "")
    ssl_key = os.getenv("SSL_KEY_FILE", "")
    use_ssl = False

    if args.prod:
        os.environ["HTTPS_REQUIRED"] = "true"
        if not ssl_cert or not ssl_key:
            print("[ERROR] Production mode requires SSL_CERT_FILE and SSL_KEY_FILE environment variables.")
            print("        Set them to your Let's Encrypt or managed certificate paths.")
            sys.exit(1)
        use_ssl, _ = get_ssl_context(ssl_cert, ssl_key)
        if not use_ssl:
            print(f"[ERROR] Certificate files not found:\n  {ssl_cert}\n  {ssl_key}")
            sys.exit(1)
        print(f"[SSL] Production HTTPS enabled with provided certificate")

    elif args.ssl:
        os.environ["HTTPS_REQUIRED"] = "true"
        cert_file, key_file = generate_self_signed_cert()
        use_ssl, _ = get_ssl_context(cert_file, key_file)
        if use_ssl:
            ssl_cert = cert_file
            ssl_key = key_file
            print(f"[SSL] Self-signed HTTPS enabled for development")
        else:
            print("[WARNING] Failed to generate self-signed certificate. Falling back to HTTP.")

    else:
        # Dev mode: HTTP is fine, but still set HTTPS_REQUIRED if user wants middleware active
        if os.getenv("HTTPS_REQUIRED", "").lower() == "true":
            print("[WARNING] HTTPS_REQUIRED=true but no SSL certs configured. Middleware will redirect to HTTPS.")
            print("          Use --ssl to auto-generate dev certs, or --prod with real certs.")

    uvicorn_kwargs = {
        "host": args.host,
        "port": args.port,
        "log_level": "info",
        "workers": args.workers if args.workers > 1 else 1,
    }

    if use_ssl:
        uvicorn_kwargs["ssl_keyfile"] = ssl_key
        uvicorn_kwargs["ssl_certfile"] = ssl_cert
        print(f"[Server] Starting HTTPS server on https://{args.host}:{args.port}")
    else:
        print(f"[Server] Starting HTTP server on http://{args.host}:{args.port}")

    # Import app here so paths are set up
    from core.main import app
    uvicorn.run(app, **uvicorn_kwargs)


if __name__ == "__main__":
    main()
