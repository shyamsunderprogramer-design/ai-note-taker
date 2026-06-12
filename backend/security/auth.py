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
from typing import Optional, Dict, Any, Tuple
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
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))  # 7 days

# Password hashing
if HAS_JWT:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
else:
    pwd_context = None

# In-memory user storage (replace with database in production)
# Path: backend/data/users.json — same directory as the SQLAlchemy SQLite DB
# so all user data lives in one place. (Phase 16 migration: SQLAlchemy users
# table will become the source of truth; this file is the JSON fallback.)
USERS_FILE = Path(__file__).resolve().parent.parent / "data" / "users.json"
USERS_FILE.parent.mkdir(parents=True, exist_ok=True)

# Legacy location — older installs wrote to backend/core/data/users.json
# (because the path was relative to the security/ directory). On first load
# we silently migrate any file from the old path to the new one so users
# don't lose accounts after upgrading.
_LEGACY_USERS_FILE = Path(__file__).resolve().parent / "data" / "users.json"
if _LEGACY_USERS_FILE.exists() and not USERS_FILE.exists():
    import shutil
    shutil.copy2(_LEGACY_USERS_FILE, USERS_FILE)
    # Don't delete the legacy file — let the next write to USERS_FILE take
    # over. Operators can clean it up after verifying the migration.


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
    # Single-session enforcement (Fix #34). active_session_id is the jti of the
    # currently-valid access + refresh token. A 2nd-device login overwrites it,
    # invalidating the 1st device's tokens. None = no active session (legacy
    # user, or after /auth/logout). on_new_login_pref is the user-controlled
    # "ask first" toggle stored for v2.
    active_session_id: Optional[str] = None
    active_session_ip: Optional[str] = None
    active_session_user_agent: Optional[str] = None
    active_session_started_at: Optional[str] = None
    on_new_login_pref: str = "auto_kick"


@dataclass
class TokenData:
    """JWT token payload"""
    user_id: str
    username: str
    exp: Optional[datetime] = None
    iat: Optional[datetime] = None
    # JWT ID. For single-session enforcement (Fix #34), every issued token
    # carries a unique jti; verify_token compares the token's jti to the
    # user's active_session_id. Optional for back-compat with tokens issued
    # before the feature shipped.
    jti: Optional[str] = None


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
                    # Migration: add single-session fields (Fix #34) if missing.
                    # All default to None / "auto_kick" so legacy tokens issued
                    # before the feature shipped still work (verify_token
                    # allows jti-less tokens when user.active_session_id is
                    # None).
                    if "active_session_id" not in user_data:
                        user_data["active_session_id"] = None
                    if "active_session_ip" not in user_data:
                        user_data["active_session_ip"] = None
                    if "active_session_user_agent" not in user_data:
                        user_data["active_session_user_agent"] = None
                    if "active_session_started_at" not in user_data:
                        user_data["active_session_started_at"] = None
                    if "on_new_login_pref" not in user_data:
                        user_data["on_new_login_pref"] = "auto_kick"
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
                        "hashed_security_answer": u.hashed_security_answer,
                        # Single-session enforcement (Fix #34)
                        "active_session_id": u.active_session_id,
                        "active_session_ip": u.active_session_ip,
                        "active_session_user_agent": u.active_session_user_agent,
                        "active_session_started_at": u.active_session_started_at,
                        "on_new_login_pref": u.on_new_login_pref,
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

    def authenticate_user(self, username: str, password: str,
                          ip: str = "", user_agent: str = "") -> Optional[User]:
        """Authenticate a user. On success, rotates the active session
        (single-session enforcement, Fix #34): generates a new jti, stores
        it on the user along with the IP and user agent, and saves.

        The route layer is responsible for the actual JWT minting with
        this jti (call create_access_token / create_refresh_token with the
        same jti). The session_bus publish also happens at the route layer,
        not here, so this function stays synchronous + unit-testable.
        """
        user = self.users.get(username)
        if not user:
            return None
        if not user.is_active:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None

        # Rotate the active session (single-session enforcement).
        new_jti = str(uuid.uuid4())
        user.active_session_id = new_jti
        user.active_session_ip = ip or user.active_session_ip
        user.active_session_user_agent = user_agent or user.active_session_user_agent
        user.active_session_started_at = datetime.now(timezone.utc).isoformat()
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

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by id. Linear scan — the dict is keyed by username
        (Fix #34). Centralises the lookup duplicated in
        ``_enforce_single_session``, ``get_current_user`` and
        ``get_current_user_with_reason``. Fine while n is small
        (single-operator install); see TODO in ``_enforce_single_session``.
        """
        for u in self.users.values():
            if u.id == user_id:
                return u
        return None


# Global user manager instance
user_manager = UserManager()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None,
                        jti: Optional[str] = None) -> str:
    """Create a JWT access token.

    The ``jti`` argument is the JWT ID (Fix #34, single-session
    enforcement). If supplied, it is embedded in the payload as the
    standard ``jti`` claim. If not supplied, a fresh UUID4 is generated
    and embedded. The caller should reuse the same ``jti`` for the
    matching refresh token so access + refresh share a session.
    """
    if not HAS_JWT:
        # Fallback: create simple token without JWT library
        import base64
        import json

        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
        to_encode.update({
            "exp": expire.isoformat(),
            "iat": datetime.now(timezone.utc).isoformat(),
            "jti": jti or str(uuid.uuid4()),
        })

        payload = json.dumps(to_encode).encode()
        # Simple encoding - NOT SECURE, just for dev without JWT lib
        token = base64.urlsafe_b64encode(payload).decode()
        return f"dev_{token}"

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": jti or str(uuid.uuid4()),
    })

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict, jti: Optional[str] = None) -> str:
    """Create a long-lived JWT refresh token. Shares the same jti as
    the matching access token (Fix #34, single-session enforcement)."""
    if not HAS_JWT:
        # Fallback: create simple token
        import base64
        import json

        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({
            "exp": expire.isoformat(),
            "iat": datetime.now(timezone.utc).isoformat(),
            "type": "refresh",
            "jti": jti or str(uuid.uuid4()),
        })
        payload = json.dumps(to_encode).encode()
        token = base64.urlsafe_b64encode(payload).decode()
        return f"dev_refresh_{token}"

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
        "jti": jti or str(uuid.uuid4()),
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_refresh_token(token: str) -> Optional[TokenData]:
    """Verify a refresh token and return the payload"""
    if not HAS_JWT:
        import base64
        import json
        try:
            if token.startswith("dev_refresh_"):
                payload = base64.urlsafe_b64decode(token[12:])
                data = json.loads(payload)
                return TokenData(
                    user_id=data.get("sub", "unknown"),
                    username=data.get("username", "unknown"),
                    exp=datetime.fromisoformat(data.get("exp")) if data.get("exp") else None,
                    iat=datetime.fromisoformat(data.get("iat")) if data.get("iat") else None,
                    jti=data.get("jti"),
                )
        except Exception:
            pass  # nosec B110
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        return TokenData(
            user_id=payload.get("sub", ""),
            username=payload.get("username", ""),
            exp=datetime.fromtimestamp(payload.get("exp")) if payload.get("exp") else None,
            iat=datetime.fromtimestamp(payload.get("iat")) if payload.get("iat") else None,
            jti=payload.get("jti"),
        )
    except JWTError:
        return None


def verify_token(token: str) -> Optional[TokenData]:
    """Verify and decode a JWT token. Single-session enforcement
    (Fix #34): if the token carries a jti, the same function compares
    it to the user's active_session_id. A mismatch means the user has
    logged in on another device since this token was issued, and the
    token is rejected (the caller gets None and returns 401 with
    error_code="session_invalidated").

    Back-compat: a token with no jti claim, or a user with no
    active_session_id set, falls through the check (the token is
    accepted). This keeps tokens issued before Fix #34 working until
    the user next logs in, which populates active_session_id.
    """
    if not HAS_JWT:
        # Fallback: decode simple token
        import base64
        import json

        try:
            if token.startswith("dev_"):
                payload = base64.urlsafe_b64decode(token[4:])
                data = json.loads(payload)
                token_data = TokenData(
                    user_id=data.get("sub", "unknown"),
                    username=data.get("username", "unknown"),
                    exp=datetime.fromisoformat(data.get("exp")) if data.get("exp") else None,
                    iat=datetime.fromisoformat(data.get("iat")) if data.get("iat") else None,
                    jti=data.get("jti"),
                )
                return _enforce_single_session(token_data)
        except Exception:
            pass  # nosec B110
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_data = TokenData(
            user_id=payload.get("sub"),
            username=payload.get("username"),
            exp=datetime.fromtimestamp(payload.get("exp")) if payload.get("exp") else None,
            iat=datetime.fromtimestamp(payload.get("iat")) if payload.get("iat") else None,
            jti=payload.get("jti"),
        )
        return _enforce_single_session(token_data)
    except JWTError:
        return None


def _enforce_single_session(token_data: TokenData) -> Optional[TokenData]:
    """If the token has a jti AND the matching user has an
    active_session_id set AND they differ, return None (rejected).
    Otherwise return token_data unchanged. Pure helper, no I/O.

    Back-compat rule (Fix #34): a token with no jti claim is always
    accepted (pre-Fix-34 issuance). A token with a jti whose matching
    user has active_session_id=None is rejected (the user logged out
    after the token was issued, so the token must be invalid). A
    token with a jti whose matching user has active_session_id set
    is rejected on mismatch (a 2nd-device login rotated the session).
    """
    if not token_data.jti:
        return token_data
    # TODO(solo): O(n) over user_manager.users on every request. Fine
    # for a single-operator install; add a username->User + id->User
    # index in UserManager.__init__ if user count exceeds ~1000.
    # The user may not exist (deleted), or the active_session_id may be
    # None (user logged out, or legacy user who never logged in after
    # the fix shipped — but a jti-bearing token implies a post-fix
    # issuance, so a None active_session_id here means logout, not
    # legacy).
    user = None
    for u in user_manager.users.values():
        if u.username == token_data.username or u.id == token_data.user_id:
            user = u
            break
    if user is None:
        return token_data  # user not found — let get_current_user handle the "user_not_found" reason
    if user.active_session_id is None:
        # jti-bearing token, no active session: user logged out since
        # the token was issued. Reject.
        try:
            from security.audit import log_audit_event as _log_audit
            _log_audit(
                "auth_session_invalidated",
                user.username,
                "token_rejected_after_logout",
                resource=f"user:{user.id}",
                details={"token_jti": token_data.jti},
                success=False,
            )
        except Exception:
            pass  # nosec B110
        return None
    if user.active_session_id != token_data.jti:
        # Log the rejection so the kicked device's silent failures aren't
        # actually silent. Imported lazily to avoid a circular dependency
        # between security.auth and security.audit at module load time.
        try:
            from security.audit import log_audit_event as _log_audit
            _log_audit(
                "auth_session_invalidated",
                user.username,
                "token_rejected_session_rotated",
                resource=f"user:{user.id}",
                details={"token_jti": token_data.jti, "active_jti": user.active_session_id},
                success=False,
            )
        except Exception:
            pass  # nosec B110
        return None
    return token_data


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


def get_current_user_with_reason(token: str) -> Tuple[Optional[User], Optional[str]]:
    """Get current user from token, plus a string reason if the token
    was rejected. Returns (user, None) on success. On failure, returns
    (None, reason) where reason is one of:

      - "no_token"  — token is None or empty
      - "invalid_token"  — token is malformed, expired, or wrong signature
      - "session_invalidated"  — single-session enforcement (Fix #34):
        the token's jti no longer matches the user's active_session_id
        (i.e., a 2nd-device login has kicked this one)
      - "user_inactive"  — token is valid but the user is is_active=False
      - "user_not_found"  — token is valid but the user was deleted

    The new auth routes use this to return 401 bodies with an
    ``error_code`` field, so clients can distinguish "your session was
    kicked" from "your token is bad" and react accordingly.
    """
    if not token:
        return None, "no_token"
    token_data = verify_token(token)
    if not token_data:
        # Disambiguate the reason by trying to decode without the
        # jti-check. If raw_decode succeeds and has a jti but verify_token
        # still returned None, it was the single-session check that
        # rejected — that's the kicked case. Otherwise it's a malformed
        # / expired token.
        try:
            if HAS_JWT:
                raw = jwt.get_unverified_claims(token)
            else:
                import base64 as _b64
                if token.startswith("dev_"):
                    raw = json.loads(_b64.urlsafe_b64decode(token[4:]))
                else:
                    raw = None
        except Exception:
            raw = None
        if raw and raw.get("jti"):
            return None, "session_invalidated"
        return None, "invalid_token"

    user = None
    for u in user_manager.users.values():
        if u.username == token_data.username or u.id == token_data.user_id:
            user = u
            break
    if user is None:
        return None, "user_not_found"
    if not user.is_active:
        return None, "user_inactive"
    return user, None


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
