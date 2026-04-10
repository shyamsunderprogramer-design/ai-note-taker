#!/usr/bin/env python3
"""
AI Note Taker - Secure Startup Script
Starts the backend with HTTPS, SSL, and security features enabled
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from generate_ssl import generate_self_signed_cert, get_ssl_context


def check_dependencies():
    """Check if required security packages are installed"""
    required = [
        ("python-jose", "python-jose[cryptography]"),
        ("passlib", "passlib[bcrypt]"),
    ]

    missing = []
    for module, package in required:
        try:
            __import__(module.replace("-", "_"))
        except ImportError:
            missing.append(package)

    if missing:
        print("[WARNING] Missing security dependencies:")
        for pkg in missing:
            print(f"  - {pkg}")
        print("\nInstall with:")
        print(f"  pip install {' '.join(missing)}")
        print("\nContinuing without full security features...")
        return False
    return True


def generate_ssl_if_needed(cert_file: str = "", key_file: str = ""):
    """Generate SSL certificates if not provided"""
    if not cert_file or not key_file:
        print("[INFO] Generating self-signed SSL certificate...")
        cert_file, key_file = generate_self_signed_cert()

    if cert_file and key_file and Path(cert_file).exists() and Path(key_file).exists():
        print(f"[SUCCESS] SSL certificates ready:")
        print(f"  Certificate: {cert_file}")
        print(f"  Private Key: {key_file}")
        return cert_file, key_file
    else:
        print("[ERROR] Failed to generate/load SSL certificates")
        return None, None


def start_server(host: str = "127.0.0.1", port: int = 8000,
                 ssl_cert: str = "", ssl_key: str = "",
                 reload: bool = False, workers: int = 1):
    """Start the FastAPI server with security features"""

    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║  AI Note Taker - Secure Server Startup                          ║")
    print("╠══════════════════════════════════════════════════════════════════╣")
    print(f"║  Host:    {host:54} ║")
    print(f"║  Port:    {port:54} ║")
    print(f"║  HTTPS:   {'ENABLED' if ssl_cert else 'DISABLED (add --ssl)':54} ║")
    print(f"║  Workers: {workers:54} ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print()

    # Change to backend directory
    os.chdir(Path(__file__).parent / "backend")

    # Build uvicorn command
    cmd = [
        sys.executable, "-m", "uvicorn",
        "main:app",
        "--host", host,
        "--port", str(port),
    ]

    if ssl_cert and ssl_key:
        cmd.extend(["--ssl-keyfile", ssl_key, "--ssl-certfile", ssl_cert])

    if reload:
        cmd.append("--reload")

    if workers > 1:
        cmd.extend(["--workers", str(workers)])

    # Environment variables
    env = os.environ.copy()
    env["SECURE_MODE"] = "1"
    if ssl_cert:
        env["SSL_CERT_FILE"] = ssl_cert
        env["SSL_KEY_FILE"] = ssl_key

    print(f"[INFO] Starting server...")
    print(f"[CMD] {' '.join(cmd)}")
    print()

    try:
        subprocess.run(cmd, env=env)
    except KeyboardInterrupt:
        print("\n[INFO] Server stopped")


def main():
    parser = argparse.ArgumentParser(description="AI Note Taker - Secure Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--ssl", action="store_true", help="Enable HTTPS with auto-generated certificates")
    parser.add_argument("--ssl-cert", default="", help="Path to SSL certificate")
    parser.add_argument("--ssl-key", default="", help="Path to SSL private key")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    parser.add_argument("--skip-deps", action="store_true", help="Skip dependency check")

    args = parser.parse_args()

    # Check dependencies
    if not args.skip_deps:
        check_dependencies()

    # Generate SSL if requested
    ssl_cert = args.ssl_cert
    ssl_key = args.ssl_key

    if args.ssl and not (ssl_cert and ssl_key):
        ssl_cert, ssl_key = generate_ssl_if_needed()

    if args.ssl and not (ssl_cert and ssl_key):
        print("[ERROR] Cannot start with SSL - certificate generation failed")
        print("Run without --ssl flag for HTTP mode")
        sys.exit(1)

    # Start server
    start_server(
        host=args.host,
        port=args.port,
        ssl_cert=ssl_cert or "",
        ssl_key=ssl_key or "",
        reload=args.reload,
        workers=args.workers
    )


if __name__ == "__main__":
    main()
