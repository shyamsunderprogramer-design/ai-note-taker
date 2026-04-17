"""
Structured error codes for consistent API responses
T6: Standardized error format across all endpoints
"""

from fastapi import HTTPException
from typing import Optional, Dict, Any


class ErrorCode:
    """Standard error codes for the API"""
    # Auth errors (401)
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"  # nosec B105
    FORBIDDEN = "FORBIDDEN"  # nosec B105

    # Validation errors (400, 422)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_PARAMETER = "MISSING_PARAMETER"
    INVALID_FORMAT = "INVALID_FORMAT"

    # Rate limiting (429)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # Not found (404)
    NOT_FOUND = "NOT_FOUND"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    CONVERSATION_NOT_FOUND = "CONVERSATION_NOT_FOUND"
    USER_NOT_FOUND = "USER_NOT_FOUND"

    # Conflict (409)
    ALREADY_EXISTS = "ALREADY_EXISTS"
    CONFLICT = "CONFLICT"

    # Server errors (500)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    MODULE_NOT_AVAILABLE = "MODULE_NOT_AVAILABLE"

    # HTTPS (301)
    HTTPS_REQUIRED = "HTTPS_REQUIRED"

    # Request too large (413)
    REQUEST_TOO_LARGE = "REQUEST_TOO_LARGE"


class APIError(HTTPException):
    """Structured API error with code, message, and details"""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(
            status_code=status_code,
            detail={
                "error": {
                    "code": code,
                    "message": message,
                    **({"details": details} if details else {}),
                }
            }
        )


def error_response(
    code: str,
    message: str,
    status_code: int = 400,
    details: Optional[Dict[str, Any]] = None,
) -> dict:
    """Create a structured error response dict (for return, not raise)"""
    error_obj: Dict[str, Any] = {"code": code, "message": message}
    if details:
        error_obj["details"] = details
    return {"error": error_obj}