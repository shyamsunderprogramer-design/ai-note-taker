"""
Input validation and security headers module
Provides sanitization, validation, and security header utilities
"""

import re
import html
import hashlib
from typing import Optional, Dict, Any, List
from pathlib import Path
import json

try:
    from fastapi import Request, HTTPException, status
    from fastapi.responses import Response
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


# Maximum allowed sizes
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
MAX_TEXT_LENGTH = 100_000  # 100KB
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_FILENAME_LENGTH = 255

# Allowed file types
ALLOWED_IMAGE_TYPES = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
ALLOWED_DOCUMENT_TYPES = {'.pdf', '.doc', '.docx', '.txt', '.md', '.json', '.csv'}
ALLOWED_AUDIO_TYPES = {'.mp3', '.wav', '.ogg', '.m4a', '.webm'}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_TYPES | ALLOWED_DOCUMENT_TYPES | ALLOWED_AUDIO_TYPES

# Pattern for SQL injection detection (basic)
SQL_INJECTION_PATTERNS = [
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION|WHERE|AND|OR)\b.*['\";])",
    r"(--|\#|\/\*|\*\/)",
    r"(\bWAITFOR\s+DELAY\b|\bSHUTDOWN\b|\bBENCHMARK\s*\()",
]

# Pattern for XSS detection
XSS_PATTERNS = [
    r"(<script.*?>.*?<\/script.*?>)",
    r"(javascript:|data:text/html|on\w+\s*=)",
    r"(<iframe.*?>)",
    r"(alert\s*\(|confirm\s*\(|prompt\s*\()",
]

# Pattern for path traversal
PATH_TRAVERSAL_PATTERNS = [
    r"\.\.",
    r"~\/",
    r"%2e%2e",
    r"\\x2e\\x2e",
]


class SecurityHeaders:
    """
    Security headers for HTTP responses
    Protects against XSS, clickjacking, MIME sniffing, etc.
    """

    # Content Security Policy
    CSP_DIRECTIVES = {
        "default-src": "'self'",
        "script-src": "'self' 'unsafe-inline'",  # May need adjustment for your frontend
        "style-src": "'self' 'unsafe-inline'",
        "img-src": "'self' data: blob:",
        "font-src": "'self'",
        "connect-src": "'self' http://localhost:* http://127.0.0.1:* ws://localhost:* ws://127.0.0.1:* https://localhost:* https://127.0.0.1:* wss://localhost:* wss://127.0.0.1:*",
        "media-src": "'self' blob: mediastream:",
        "object-src": "'none'",
        "frame-ancestors": "'none'",
        "form-action": "'self'",
        "base-uri": "'self'",
    }

    @classmethod
    def get_csp_header(cls) -> str:
        """Generate Content-Security-Policy header value"""
        return "; ".join(f"{k} {v}".strip() for k, v in cls.CSP_DIRECTIVES.items())

    @classmethod
    def get_security_headers(cls, request_host: str = "") -> Dict[str, str]:
        """Get all security headers.
        HSTS is omitted for localhost/127.0.0.1 to prevent SSL protocol errors
        from Electron/browser clients that connect over plain HTTP in development.
        """
        headers = {
            # CSP
            "Content-Security-Policy": cls.get_csp_header(),

            # Prevent MIME sniffing
            "X-Content-Type-Options": "nosniff",

            # XSS Protection
            "X-XSS-Protection": "1; mode=block",

            # Clickjacking protection
            "X-Frame-Options": "DENY",

            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",

            # Permissions policy
            "Permissions-Policy": "geolocation=(), microphone=(self), camera=(self), fullscreen=(self)",

            # Cache control for sensitive data
            "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }

        # Only send HSTS for non-localhost origins to avoid forcing
        # browsers/Electron to upgrade HTTP connections to HTTPS
        is_localhost = not request_host or "localhost" in request_host or "127.0.0.1" in request_host or "::1" in request_host  # nosec B106 — localhost check
        if not is_localhost:
            headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        return headers

    @classmethod
    def apply_to_response(cls, response: Any) -> Any:
        """Apply security headers to a response object"""
        if not HAS_FASTAPI:
            return response

        headers = cls.get_security_headers()
        for key, value in headers.items():
            response.headers[key] = value
        return response


class InputValidator:
    """Comprehensive input validation"""

    @staticmethod
    def sanitize_string(value: str, max_length: int = MAX_TEXT_LENGTH,
                        allow_html: bool = False) -> str:
        """
        Sanitize a string input
        - Removes/replaces dangerous characters
        - Escapes HTML if not allowed
        - Enforces length limits
        """
        if not isinstance(value, str):
            value = str(value)

        # Trim whitespace
        value = value.strip()

        # Check length
        if len(value) > max_length:
            value = value[:max_length]

        # Escape HTML if not allowed
        if not allow_html:
            value = html.escape(value)

        return value

    @staticmethod
    def validate_email(email: str) -> Optional[str]:
        """
        Validate email format
        Returns sanitized email or None if invalid
        """
        if not email:
            return None

        email = email.strip().lower()

        # Basic email pattern
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return None

        # Length check
        if len(email) > 254:
            return None

        return email

    @staticmethod
    def validate_username(username: str) -> Optional[str]:
        """
        Validate username format
        Returns sanitized username or None if invalid
        """
        if not username:
            return None

        username = username.strip()

        # Alphanumeric + underscore + hyphen, 3-30 chars
        pattern = r'^[a-zA-Z0-9_-]{3,30}$'
        if not re.match(pattern, username):
            return None

        return username

    @staticmethod
    def validate_filename(filename: str) -> Optional[str]:
        """
        Validate and sanitize filename
        Returns safe filename or None if invalid
        """
        if not filename:
            return None

        # Remove path components
        filename = Path(filename).name

        # Check length
        if len(filename) > MAX_FILENAME_LENGTH:
            return None

        # Check for path traversal attempts
        for pattern in PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, filename, re.IGNORECASE):
                return None

        # Remove dangerous characters
        filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename)

        # Ensure extension is allowed (if has extension)
        if '.' in filename:
            ext = Path(filename).suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                return None

        return filename if filename else None

    @staticmethod
    def validate_security_question(question: str) -> Optional[str]:
        """Validate security question format. Returns sanitized question or None."""
        if not question:
            return None
        question = question.strip()
        if len(question) < 5 or len(question) > 200:
            return None
        return InputValidator.sanitize_string(question, max_length=200, allow_html=False)

    @staticmethod
    def validate_security_answer(answer: str) -> Optional[str]:
        """Validate security answer format. Returns stripped answer or None.
        Answer is stored hashed, so no HTML sanitization needed."""
        if not answer:
            return None
        answer = answer.strip()
        if len(answer) < 2 or len(answer) > 100:
            return None
        return answer

    @staticmethod
    def check_sql_injection(text: str) -> bool:
        """
        Check for potential SQL injection patterns
        Returns True if suspicious patterns found
        """
        text_upper = text.upper()
        for pattern in SQL_INJECTION_PATTERNS:
            if re.search(pattern, text_upper, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def check_xss(text: str) -> bool:
        """
        Check for potential XSS patterns
        Returns True if suspicious patterns found
        """
        for pattern in XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def validate_json(data: Any, max_depth: int = 10) -> bool:
        """
        Validate JSON data structure
        Check for deeply nested objects, oversized data, etc.
        """
        def check_depth(obj, current_depth: int) -> bool:
            if current_depth > max_depth:
                return False

            if isinstance(obj, dict):
                return all(check_depth(v, current_depth + 1) for v in obj.values())
            elif isinstance(obj, list):
                return all(check_depth(item, current_depth + 1) for item in obj)
            return True

        return check_depth(data, 0)


class FileValidator:
    """File upload validation"""

    @staticmethod
    def validate_file_size(content: bytes, max_size: int = MAX_FILE_SIZE) -> bool:
        """Validate file size"""
        return len(content) <= max_size

    @staticmethod
    def get_file_hash(content: bytes) -> str:
        """Get file hash for deduplication"""
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def validate_content_type(content: bytes, declared_type: str) -> bool:
        """
        Validate file content matches declared type
        Basic magic number checking
        """
        # Magic numbers for common formats
        magic = {
            'image/png': b'\x89PNG\r\n\x1a\n',
            'image/jpeg': b'\xff\xd8\xff',
            'image/gif': b'GIF89a',
            'image/webp': b'RIFF',
            'application/pdf': b'%PDF',
        }

        expected = magic.get(declared_type.lower())
        if expected:
            return content.startswith(expected)
        return True  # Unknown type, let it through


# Convenience functions
def sanitize_input(text: str, max_length: int = MAX_TEXT_LENGTH) -> str:
    """Quick sanitize function"""
    return InputValidator.sanitize_string(text, max_length)


def validate_file_upload(filename: str, content: Optional[bytes] = None) -> tuple[bool, str]:
    """
    Validate file upload
    Returns (is_valid, error_message)
    """
    # Validate filename
    safe_name = InputValidator.validate_filename(filename)
    if not safe_name:
        return False, "Invalid filename"

    # Validate content if provided
    if content is not None:
        if not FileValidator.validate_file_size(content):
            return False, f"File too large (max {MAX_FILE_SIZE / 1024 / 1024:.0f}MB)"

    return True, ""


def check_security_threats(data: Dict[str, Any]) -> List[str]:
    """
    Check dict data for security threats
    Returns list of found threats
    """
    threats = []

    def check_value(value):
        if isinstance(value, str):
            if InputValidator.check_sql_injection(value):
                threats.append("SQL_INJECTION")
            if InputValidator.check_xss(value):
                threats.append("XSS_ATTEMPT")
        elif isinstance(value, dict):
            for v in value.values():
                check_value(v)
        elif isinstance(value, list):
            for item in value:
                check_value(item)

    check_value(data)
    return list(set(threats))  # Remove duplicates


# Security middleware for FastAPI
if HAS_FASTAPI:
    class SecurityHeadersMiddleware:
        """Add security headers to all responses"""

        async def __call__(self, request: Request, call_next):
            response = await call_next(request)

            # Add security headers
            headers = SecurityHeaders.get_security_headers()
            for key, value in headers.items():
                response.headers[key] = value

            return response


    class RequestSizeLimitMiddleware:
        """Limit request body size"""

        def __init__(self, max_size: int = MAX_REQUEST_SIZE):
            self.max_size = max_size

        async def __call__(self, request: Request, call_next):
            content_length = request.headers.get("content-length")
            if content_length:
                if int(content_length) > self.max_size:
                    return Response(
                        content=json.dumps({
                            "error": "Request too large",
                            "max_size": self.max_size
                        }),
                        status_code=413,
                        media_type="application/json"
                    )
            return await call_next(request)


    class InputValidationMiddleware:
        """Validate request inputs for threats"""

        async def __call__(self, request: Request, call_next):
            # Skip validation for GET/HEAD requests
            if request.method in ("GET", "HEAD"):
                return await call_next(request)

            try:
                # Try to parse and validate JSON body
                body = await request.body()
                if body:
                    try:
                        data = json.loads(body)
                        threats = check_security_threats(data)
                        if threats:
                            return Response(
                                content=json.dumps({
                                    "error": "Security violation detected",
                                    "threats": threats
                                }),
                                status_code=400,
                                media_type="application/json"
                            )
                    except json.JSONDecodeError:
                        pass  # Not JSON, skip validation
            except Exception:  # nosec B110
                pass

            return await call_next(request)
