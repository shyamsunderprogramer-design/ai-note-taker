"""
Security module for AI Note Taker
Provides authentication, rate limiting, input validation, audit logging, and structured errors
"""

from .auth import (
    create_access_token,
    verify_token,
    get_current_user,
    require_auth,
    TokenData,
    User,
)
from .rate_limit import (
    RateLimiter,
    rate_limit,
    rate_limit_middleware,
    rate_limiter,
)
from .validation import (
    sanitize_input,
    validate_file_upload,
    SecurityHeaders,
    InputValidator,
)
from .audit import (
    log_audit_event,
    get_audit_log,
    get_audit_stats,
    AuditEvent,
)
from .errors import (
    ErrorCode,
    APIError,
    error_response,
)
from .encryption import (
    EncryptionManager,
    FieldEncryption,
    field_encryption,
    encryption_manager,
    encrypt_data,
    decrypt_data,
    encrypt_string,
    decrypt_string,
    is_encryption_available,
    encrypt_api_key,
    decrypt_api_key,
    HAS_CRYPTOGRAPHY,
)

__all__ = [
    # Auth
    "create_access_token",
    "verify_token",
    "get_current_user",
    "require_auth",
    "TokenData",
    "User",
    # Rate Limit
    "RateLimiter",
    "rate_limit",
    "rate_limit_middleware",
    "rate_limiter",
    # Validation
    "sanitize_input",
    "validate_file_upload",
    "SecurityHeaders",
    "InputValidator",
    # Audit
    "log_audit_event",
    "get_audit_log",
    "get_audit_stats",
    "AuditEvent",
    # Errors
    "ErrorCode",
    "APIError",
    "error_response",
    # Encryption
    "EncryptionManager",
    "FieldEncryption",
    "field_encryption",
    "encryption_manager",
    "encrypt_data",
    "decrypt_data",
    "encrypt_string",
    "decrypt_string",
    "is_encryption_available",
    "encrypt_api_key",
    "decrypt_api_key",
    "HAS_CRYPTOGRAPHY",
]