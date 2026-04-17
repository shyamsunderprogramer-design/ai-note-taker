"""
SSL Certificate Generator
Generates self-signed certificates for development and provides setup for production
"""

import os
import subprocess  # nosec B404
from pathlib import Path
from datetime import datetime, timedelta


def generate_self_signed_cert(cert_dir: str = "certs", hostname: str = "localhost") -> tuple[str, str]:
    """
    Generate self-signed SSL certificate for development

    Returns:
        Tuple of (cert_path, key_path)
    """
    cert_path = Path(cert_dir)
    cert_path.mkdir(parents=True, exist_ok=True)

    key_file = cert_path / "key.pem"
    cert_file = cert_path / "cert.pem"

    # Check if OpenSSL is available
    try:
        result = subprocess.run(  # nosec B603 B607
            ["openssl", "version"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            print("[WARNING] OpenSSL not found. Cannot generate certificates.")
            return str(cert_file) if cert_file.exists() else "", str(key_file) if key_file.exists() else ""
    except FileNotFoundError:
        print("[WARNING] OpenSSL not found in PATH.")
        return "", ""

    # Generate certificate if not exists
    if not cert_file.exists() or not key_file.exists():
        print(f"[INFO] Generating self-signed certificate for {hostname}...")

        # Create config for SAN (Subject Alternative Name)
        config_content = f"""
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = {hostname}

[v3_req]
subjectAltName = @alt_names
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth

[alt_names]
DNS.1 = {hostname}
DNS.2 = localhost
DNS.3 = 127.0.0.1  # nosec B106 — localhost for development
IP.1 = 127.0.0.1
"""
        config_file = cert_path / "openssl.cnf"
        config_file.write_text(config_content)

        cmd = [
            "openssl", "req", "-x509",
            "-nodes",
            "-days", "365",
            "-newkey", "rsa:2048",
            "-keyout", str(key_file),
            "-out", str(cert_file),
            "-config", str(config_file),
            "-sha256"
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)  # nosec B603
            print(f"[SUCCESS] Certificate generated:")
            print(f"  - Certificate: {cert_file}")
            print(f"  - Private Key: {key_file}")
            print(f"  - Valid for: 365 days")
            print(f"  - Hosts: {hostname}, localhost, 127.0.0.1")

            # Clean up config file
            config_file.unlink(missing_ok=True)

            return str(cert_file), str(key_file)
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to generate certificate: {e}")
            print(f"stderr: {e.stderr}")
            return "", ""
    else:
        print(f"[INFO] Using existing certificate:")
        print(f"  - Certificate: {cert_file}")
        print(f"  - Private Key: {key_file}")
        return str(cert_file), str(key_file)


def get_ssl_context(cert_file: str, key_file: str) -> tuple[bool, str]:
    """
    Get SSL context for production or development

    Returns:
        Tuple of (use_ssl, cert_path)
    """
    if not cert_file or not key_file:
        return False, ""

    if Path(cert_file).exists() and Path(key_file).exists():
        return True, cert_file

    return False, ""


def print_production_ssl_instructions():
    """Print instructions for production SSL setup"""
    instructions = """
╔══════════════════════════════════════════════════════════════════╗
║  PRODUCTION SSL/TLS SETUP INSTRUCTIONS                           ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Option 1: Let's Encrypt (Free, Recommended)                    ║
║  ──────────────────────────────────────────                      ║
║  1. Install certbot:                                             ║
║     sudo apt-get install certbot python3-certbot-nginx          ║
║                                                                  ║
║  2. Obtain certificate:                                         ║
║     sudo certbot --nginx -d yourdomain.com                      ║
║                                                                  ║
║  3. Auto-renewal is configured by default                       ║
║                                                                  ║
║  Option 2: Cloud Provider Managed Certificates                  ║
║  ───────────────────────────────────────────────                  ║
║  AWS: AWS Certificate Manager (ACM)                               ║
║  Google Cloud: Google-managed SSL certificates                  ║
║  Azure: Azure Key Vault certificates                            ║
║                                                                  ║
║  Option 3: Reverse Proxy with SSL                               ║
║  ────────────────────────────────                               ║
║  Use Nginx or Caddy as reverse proxy with SSL termination:      ║
║                                                                  ║
║  Nginx example:                                                  ║
║  ─────────────                                                   ║
║  server {                                                        ║
║      listen 443 ssl;                                             ║
║      server_name yourdomain.com;                                 ║
║                                                                  ║
║      ssl_certificate /path/to/cert.pem;                         ║
║      ssl_certificate_key /path/to/key.pem;                      ║
║                                                                  ║
║      location / {                                                ║
║          proxy_pass http://localhost:8000;                       ║
║          proxy_set_header Host $host;                           ║
║          proxy_set_header X-Real-IP $remote_addr;               ║
║      }                                                           ║
║  }                                                               ║
║                                                                  ║
║  Caddy example:                                                  ║
║  ────────────                                                    ║
║  yourdomain.com {                                                ║
║      reverse_proxy localhost:8000                               ║
║  }                                                               ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
"""
    print(instructions)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--production":
        print_production_ssl_instructions()
    else:
        print("╔══════════════════════════════════════════════════════════════════╗")
        print("║  SSL Certificate Generator for Development                       ║")
        print("╠══════════════════════════════════════════════════════════════════╣")
        print("")

        hostname = sys.argv[1] if len(sys.argv) > 1 else "localhost"
        cert_file, key_file = generate_self_signed_cert(hostname=hostname)

        print("")
        print("╔══════════════════════════════════════════════════════════════════╗")
        print("║  USAGE                                                           ║")
        print("╠══════════════════════════════════════════════════════════════════╣")
        print("║  Set these environment variables:                                ║")
        print(f"║  export SSL_CERT_FILE={cert_file or '/path/to/cert.pem'}")
        print(f"║  export SSL_KEY_FILE={key_file or '/path/to/key.pem'}")
        print("║                                                                  ║")
        print("║  Or run with:                                                    ║")
        print("║  python main.py --ssl                                          ║")
        print("║                                                                  ║")
        print("║  For production instructions:                                    ║")
        print("║  python generate_ssl.py --production                           ║")
        print("╚══════════════════════════════════════════════════════════════════╝")
