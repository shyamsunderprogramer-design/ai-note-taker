"""Shared database URL classification, safe display and verified PostgreSQL TLS."""
import os
import ssl
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def database_dialect(url):
    scheme = (url or "").partition(":")[0].lower().split("+", 1)[0]
    if scheme == "sqlite":
        return "sqlite"
    if scheme in {"postgresql", "postgres"}:
        return "postgresql"
    return "unknown"


def database_display_url(url):
    # Credentials can occur in userinfo, query parameters and filesystem paths.
    # Return only a known dialect rather than attempting partial redaction.
    return f"{database_dialect(url)}://[redacted]" if url else "(none)"


def postgres_connection_options(url):
    """Keep non-TLS query options and fail closed for invalid CA configuration."""
    parsed = urlsplit(url)
    query = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True)
             if key != "sslmode"]
    effective_url = urlunsplit(parsed._replace(query=urlencode(query)))
    context = ssl.create_default_context(cafile=os.getenv("DATABASE_SSL_CA_FILE") or None)
    return effective_url, {"ssl": context}
