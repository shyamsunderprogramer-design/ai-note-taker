"""
JWT Authentication module
Handles token generation, validation, and user authentication
"""

import hmac
import json
import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path

try:
    from jose import JWTError, jwt
    from passlib.context import CryptContext
    HAS_JWT = True
except ImportError:
    HAS_JWT = False
    logging.getLogger("auth").warning("[WARNING] PyJWT or passlib not installed. Authentication will be limited.")
    logging.getLogger("auth").warning("  Install: pip install python-jose[cryptography] passlib[bcrypt]")

# Configuration
_is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"
_jwt_secret = os.getenv("JWT_SECRET_KEY", "")

if _is_production and not _jwt_secret:
    raise RuntimeError(
        "FATAL: JWT_SECRET_KEY must be set in production. "
        "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
    )

SECRET_KEY = _jwt_secret if _jwt_secret else os.urandom(32).hex()
if not _jwt_secret:
    import logging
    logging.getLogger("auth").warning(
        "JWT_SECRET_KEY not set — tokens will invalidate on restart. "
        "Set JWT_SECRET_KEY for stable authentication."
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))  # 8 hours

# Password hashing
if HAS_JWT:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
else:
    pwd_context = None

# In-memory user storage (replace with database in production)
USERS_FILE = Path("data/users.json")
USERS_FILE.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class User:
    """User model"""
    id: str
    username: str
    email: str
    hashed_password: Optional[str] = None
    is_active: bool = True
    is_admin: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_login: Optional[str] = None
    api_quota: Dict[str, Any] = field(default_factory=lambda: {
        "requests_today": 0,
        "daily_limit": 1000,
        "reset_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
    })
    security_question: Optional[str] = None
    hashed_security_answer: Optional[str] = None


@dataclass
class TokenData:
    """JWT token payload"""
    user_id: str
    username: str
    exp: Optional[datetime] = None
    iat: Optional[datetime] = None


class UserManager:
    """Manages user authentication and storage"""

    def __init__(self):
        self.users: Dict[str, User] = {}
        self._load_users()
        self._create_default_user()

    def _load_users(self):
        """Load users from disk"""
        if USERS_FILE.exists():
            try:
                data = json.loads(USERS_FILE.read_text())
                for user_data in data.get("users", []):
                    # Migration: add security question fields if missing
                    if "security_question" not in user_data:
                        user_data["security_question"] = None
                    if "hashed_security_answer" not in user_data:
                        user_data["hashed_security_answer"] = None
                    user = User(**user_data)
                    self.users[user.username] = user
            except Exception as e:
                logging.getLogger("auth").warning(f"[WARNING] Failed to load users: {e}")

    def _save_users(self):
        """Save users to disk"""
        try:
            data = {
                "users": [
                    {
                        "id": u.id,
                        "username": u.username,
                        "email": u.email,
                        "hashed_password": u.hashed_password,
                        "is_active": u.is_active,
                        "is_admin": u.is_admin,
                        "created_at": u.created_at,
                        "last_login": u.last_login,
                        "api_quota": u.api_quota,
                        "security_question": u.security_question,
                        "hashed_security_answer": u.hashed_security_answer
                    }
                    for u in self.users.values()
                ]
            }
            USERS_FILE.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logging.getLogger("auth").warning(f"[WARNING] Failed to save users: {e}")

    def _create_default_user(self):
        """No default user is created. First user must register via /auth/register."""
        pass

    def create_user(self, username: str, email: str, password: str,
                   is_admin: bool = False,
                   security_question: Optional[str] = None,
                   security_answer: Optional[str] = None) -> User:
        """Create a new user. First user automatically becomes admin."""
        if username in self.users:
            raise ValueError(f"User '{username}' already exists")

        # First user is automatically admin
        if not self.users:
            is_admin = True

        user_id = str(uuid.uuid4())
        hashed_password = self._hash_password(password) if HAS_JWT else password

        hashed_answer = None
        if security_question and security_answer:
            normalized_answer = security_answer.strip().lower()
            hashed_answer = self._hash_password(normalized_answer) if HAS_JWT else f"plain:{normalized_answer}"

        user = User(
            id=user_id,
            username=username,
            email=email,
            hashed_password=hashed_password,
            is_admin=is_admin,
            security_question=security_question,
            hashed_security_answer=hashed_answer
        )

        self.users[username] = user
        self._save_users()
        return user

    def _hash_password(self, password: str) -> str:
        """Hash a password"""
        if pwd_context:
            return pwd_context.hash(password)
        # Fallback: store plain text with marker (not for production!)
        return f"plain:{password}"

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash (constant-time comparison for plaintext fallbacks)"""
        if not HAS_JWT:
            # Fallback for development — use constant-time comparison
            expected = hashed_password.replace("plain:", "") if hashed_password else ""
            return hmac.compare_digest(plain_password.encode(), expected.encode())

        if hashed_password and hashed_password.startswith("plain:"):
            expected = hashed_password.replace("plain:", "")
            # Use constant-time comparison to prevent timing attacks
            return hmac.compare_digest(plain_password.encode(), expected.encode())

        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:  # nosec B110
            return False

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user"""
        user = self.users.get(username)
        if not user:
            return None
        if not user.is_active:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None

        # Update last login
        user.last_login = datetime.now(timezone.utc).isoformat()
        self._save_users()
        return user

    def get_user(self, username: str) -> Optional[User]:
        """Get user by username"""
        return self.users.get(username)

    def update_password(self, username: str, new_password: str) -> bool:
        """Update password for an existing user"""
        user = self.users.get(username)
        if not user:
            return False
        user.hashed_password = self._hash_password(new_password) if HAS_JWT else f"plain:{new_password}"
        self._save_users()
        return True

    def set_security_question(self, username: str, question: str, answer: str) -> bool:
        """Set or update a user's security question and answer"""
        user = self.users.get(username)
        if not user:
            return False
        normalized_answer = answer.strip().lower()
        user.security_question = question
        user.hashed_security_answer = self._hash_password(normalized_answer) if HAS_JWT else f"plain:{normalized_answer}"
        self._save_users()
        return True

    def verify_security_answer(self, username: str, answer: str) -> bool:
        """Verify a user's security answer. Returns False if user not found or no question set."""
        user = self.users.get(username)
        if not user or not user.hashed_security_answer:
            return False
        normalized_answer = answer.strip().lower()
        return self.verify_password(normalized_answer, user.hashed_security_answer)

    def has_security_question(self, username: str) -> Optional[str]:
        """Return the security question text if set, or None. Does not leak user existence."""
        user = self.users.get(username)
        if not user or not user.security_question:
            return None
        return user.security_question


# Global user manager instance
user_manager = UserManager()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    if not HAS_JWT:
        # Fallback: create simple token without JWT library
        import base64
        import json

        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
        to_encode.update({"exp": expire.isoformat(), "iat": datetime.now(timezone.utc).isoformat()})

        payload = json.dumps(to_encode).encode()
        # Simple encoding - NOT SECURE, just for dev without JWT lib
        token = base64.urlsafe_b64encode(payload).decode()
        return f"dev_{token}"

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[TokenData]:
    """Verify and decode a JWT token"""
    if not HAS_JWT:
        # Fallback: decode simple token
        import base64
        import json

        try:
            if token.startswith("dev_"):
                payload = base64.urlsafe_b64decode(token[4:])
                data = json.loads(payload)
                return TokenData(
                    user_id=data.get("sub", "unknown"),
                    username=data.get("username", "unknown"),
                    exp=datetime.fromisoformat(data.get("exp")) if data.get("exp") else None,
                    iat=datetime.fromisoformat(data.get("iat")) if data.get("iat") else None
                )
        except Exception:
            pass  # nosec B110
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return TokenData(
            user_id=payload.get("sub"),
            username=payload.get("username"),
            exp=datetime.fromtimestamp(payload.get("exp")) if payload.get("exp") else None,
            iat=datetime.fromtimestamp(payload.get("iat")) if payload.get("iat") else None
        )
    except JWTError:
        return None


def get_current_user(token: str) -> Optional[User]:
    """Get current user from token"""
    token_data = verify_token(token)
    if not token_data:
        return None

    # Try to find by username first, then by user_id
    for user in user_manager.users.values():
        if user.username == token_data.username or user.id == token_data.user_id:
            if user.is_active:
                return user
    return None


def require_auth(token: Optional[str]) -> User:
    """Require authentication - raises exception if not authenticated"""
    from fastapi import HTTPException, status

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_current_user(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def check_admin(user: User) -> bool:
    """Check if user is admin"""
    return user.is_admin
