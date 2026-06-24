"""
JWT Authentication module
Handles token generation, validation, and user authentication
"""

import hmac
import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, field

try:
    from jose import JWTError, jwt
    from passlib.context import CryptContext
    HAS_JWT = True
except ImportError:
    HAS_JWT = False
    logging.getLogger("auth").warning("[WARNING] PyJWT or passlib not installed. Authentication will be limited.")
    logging.getLogger("auth").warning("  Install: pip install python-jose[cryptography] passlib[bcrypt]")

# UserRepository is the SQLAlchemy persistence layer (Fix #35). NOT
# imported at module level to avoid a circular import: `core.database`
# imports `security.encryption` (line 24) which transitively loads
# `security.auth`, and a top-level `from core.database import
# UserRepository` here would fire while `core.database` is still being
# constructed. The repository's `UserRepository` class doesn't exist
# yet at that point, so the import fails. We resolve it lazily, inside
# the methods that actually need it via the ``UserManager._repo()``
# helper, which caches the import here at module level so the lookup
# is one-shot per process.
_USER_REPO_CACHED = None

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

# In-memory user storage is GONE as of Fix #35 — the SQLAlchemy users
# table is the single source of truth. The legacy USERS_FILE was the
# JSON-file fallback. The DataMigrator (Fix #35 Commit 5) backfills
# any existing data/users.json into the users table on first boot.
# See `core.database.UserRepository` for the persistence layer and
# `core.database.DataMigrator` for the one-time backfill.


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

    @classmethod
    def from_orm(cls, orm_user) -> "User":
        """Bridge an ORM ``User`` row to the public ``User`` DTO.

        Centralises the ORM → DTO conversion at the boundary so all read
        paths produce the same shape. The ``id`` becomes a ``str``
        (UUID-stringified); datetime fields become ISO 8601 strings.
        This is the only public conversion API; ``UserManager._orm_to_dto``
        delegates here.

        Usage::

            orm = await UserRepository.get_by_username("alice")
            user = User.from_orm(orm)
        """
        def _to_iso(value):
            if value is None:
                return None
            if isinstance(value, str):
                return value
            try:
                return value.isoformat()
            except AttributeError:
                return None

        return cls(
            id=str(orm_user.id),
            username=orm_user.username,
            email=orm_user.email,
            hashed_password=orm_user.hashed_password,
            is_active=bool(orm_user.is_active) if orm_user.is_active is not None else True,
            is_admin=bool(orm_user.is_admin) if orm_user.is_admin is not None else False,
            created_at=_to_iso(getattr(orm_user, "created_at", None)),
            last_login=_to_iso(getattr(orm_user, "last_login", None)),
            api_quota=getattr(orm_user, "api_quota", None) or {
                "requests_today": 0,
                "daily_limit": 1000,
                "reset_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            },
            security_question=getattr(orm_user, "security_question", None),
            hashed_security_answer=getattr(orm_user, "hashed_security_answer", None),
            active_session_id=getattr(orm_user, "active_session_id", None),
            active_session_ip=getattr(orm_user, "active_session_ip", None),
            active_session_user_agent=getattr(orm_user, "active_session_user_agent", None),
            active_session_started_at=_to_iso(
                getattr(orm_user, "active_session_started_at", None)
            ),
            on_new_login_pref=getattr(orm_user, "on_new_login_pref", None) or "auto_kick",
        )


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
    """Async shim over the SQLAlchemy ``UserRepository``.

    As of Fix #35, the JSON file (``data/users.json``) is no longer
    the runtime auth store. Every method on this class delegates to
    ``core.database.UserRepository``, which uses the SQLAlchemy
    ``users`` table. The ``User`` dataclass remains the public DTO
    (12+ files import it as a type annotation), and ``User.from_orm``
    bridges the ORM row → DTO conversion.

    The instance is **stateless** — there is no in-memory cache. Each
    method opens its own DB session via ``UserRepository``. This is a
    deliberate trade: no cache means no cache-invalidation bugs. The
    per-request cost (one extra DB hit) is negligible on a single-
    operator install with SQLite.

    All public methods are ``async def``. The 12+ call sites that
    previously did ``user_manager.create_user(...)`` (sync) now do
    ``await user_manager.create_user(...)`` (async).
    """

    def __init__(self):
        # No state. The class is a singleton facade.
        pass

    @staticmethod
    def _repo():
        """Lazy import of ``core.database.UserRepository``.

        Avoids the circular import that fires when ``security.auth``
        is loaded while ``core.database`` is still being constructed
        (the ``UserRepository`` class doesn't exist yet at that point).
        The repo is imported on the first call into UserManager and
        cached at module level so the lookup is one-shot.
        """
        # Cache the import at module level to avoid a sys.modules
        # lookup on every call.
        global _USER_REPO_CACHED
        if _USER_REPO_CACHED is None:
            from core.database import UserRepository as _UR
            _USER_REPO_CACHED = _UR
        return _USER_REPO_CACHED

    @staticmethod
    def _to_iso(value):
        """Convert a datetime (or None) to ISO 8601 string. The User
        dataclass stores ``created_at`` / ``last_login`` / ``active_session_started_at``
        as ISO strings, but the ORM returns them as ``datetime`` objects.
        This helper normalises at the DTO boundary."""
        if value is None:
            return None
        if isinstance(value, str):
            return value
        try:
            return value.isoformat()
        except AttributeError:
            return None

    @classmethod
    def _orm_to_dto(cls, orm_user) -> "User":
        """Bridge an ORM ``User`` row to the public ``User`` DTO.

        Thin delegate to ``User.from_orm``. Kept as a separate method
        on ``UserManager`` so call sites that have a manager instance
        don't need to import the classmethod separately. Single source
        of truth for the conversion lives on ``User``.
        """
        return User.from_orm(orm_user)

    async def create_user(self, username: str, email: str, password: str,
                          is_admin: bool = False,
                          security_question: Optional[str] = None,
                          security_answer: Optional[str] = None) -> "User":
        """Create a new user. First user automatically becomes admin.

        Persists via ``UserRepository.create``. Hashing happens in the
        repository for the password; we hash the security answer here
        (the repository takes already-hashed values).
        """
        # Pre-check uniqueness by username (TOCTOU window, but the
        # users.username unique constraint catches the race).
        existing = await self._repo().get_by_username(username)
        if existing is not None:
            raise ValueError(f"User '{username}' already exists")
        # Also check by email to give a friendlier error (the
        # constraint is the safety net for concurrent inserts).
        existing_email = await self._repo().get_by_email(email)
        if existing_email is not None:
            raise ValueError(f"Email '{email}' is already registered")

        # First user is automatically admin
        if await self._repo().count() == 0:
            is_admin = True

        hashed_password = self._hash_password(password) if HAS_JWT else password
        hashed_answer = None
        if security_question and security_answer:
            normalized_answer = security_answer.strip().lower()
            hashed_answer = (
                self._hash_password(normalized_answer) if HAS_JWT
                else f"plain:{normalized_answer}"
            )

        orm_user = await self._repo().create(
            username=username,
            email=email,
            hashed_password=hashed_password,
            is_admin=is_admin,
            security_question=security_question,
            hashed_security_answer=hashed_answer,
        )
        if orm_user is None:
            raise ValueError(f"Failed to create user '{username}' (DB error)")
        return self._orm_to_dto(orm_user)

    def _hash_password(self, password: str) -> str:
        """Hash a password. Stays sync — bcrypt is CPU-bound and the
        route layer is already inside an ``async def``, so a sync call
        is fine here. The bcrypt<4.1 pin lives in
        ``requirements-security.txt``."""
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

    async def authenticate_user(self, username: str, password: str,
                                 ip: str = "", user_agent: str = "") -> Optional["User"]:
        """Authenticate a user. On success, rotates the active session
        (single-session enforcement, Fix #34) and returns the DTO.

        The route layer is responsible for the actual JWT minting with
        this jti (call create_access_token / create_refresh_token with the
        same jti). The session_bus publish also happens at the route layer,
        not here, so this function stays async + unit-testable.
        """
        orm_user = await self._repo().authenticate_and_rotate_session(
            username, password, ip=ip, user_agent=user_agent,
        )
        if orm_user is None:
            return None
        return self._orm_to_dto(orm_user)

    async def get_user(self, username: str) -> Optional["User"]:
        """Get user by username."""
        orm_user = await self._repo().get_by_username(username)
        if orm_user is None:
            return None
        return self._orm_to_dto(orm_user)

    async def update_password(self, username: str, new_password: str) -> bool:
        """Update password for an existing user."""
        orm_user = await self._repo().get_by_username(username)
        if orm_user is None:
            return False
        hashed = self._hash_password(new_password) if HAS_JWT else f"plain:{new_password}"
        return await self._repo().update_password(str(orm_user.id), hashed)

    async def set_security_question(self, username: str, question: str, answer: str) -> bool:
        """Set or update a user's security question and answer."""
        orm_user = await self._repo().get_by_username(username)
        if orm_user is None:
            return False
        normalized = answer.strip().lower()
        hashed = (
            self._hash_password(normalized) if HAS_JWT
            else f"plain:{normalized}"
        )
        return await self._repo().set_security_question(
            str(orm_user.id), question, hashed
        )

    async def verify_security_answer(self, username: str, answer: str) -> bool:
        """Verify a user's security answer. Returns False if user not
        found or no question set."""
        orm_user = await self._repo().get_by_username(username)
        if orm_user is None or not orm_user.hashed_security_answer:
            return False
        normalized = answer.strip().lower()
        return await self._repo().verify_security_answer(
            str(orm_user.id), normalized, orm_user.hashed_security_answer
        )

    async def has_security_question(self, username: str) -> Optional[str]:
        """Return the security question text if set, or None. Does not leak user existence."""
        orm_user = await self._repo().get_by_username(username)
        if orm_user is None or not orm_user.security_question:
            return None
        return orm_user.security_question

    async def get_user_by_id(self, user_id: str) -> Optional["User"]:
        """Get user by id. Hits the indexed PK on the users table —
        no linear scan. Replaces the pre-Fix-35 O(n) scan in
        ``_enforce_single_session`` / ``get_current_user`` etc."""
        orm_user = await self._repo().get_by_id(user_id)
        if orm_user is None:
            return None
        return self._orm_to_dto(orm_user)

    async def clear_session(self, user_id: str) -> bool:
        """Zero out the 4 active_session_* columns on the user. Used
        by ``routes.auth.logout_user`` (Fix #34)."""
        return await self._repo().clear_session(user_id)


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


async def verify_token(token: str) -> Optional[TokenData]:
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

    Async (Fix #35): the underlying user lookup now hits the
    SQLAlchemy ``users`` table via ``user_manager.get_user_by_id``.
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
                return await _enforce_single_session(token_data)
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
        return await _enforce_single_session(token_data)
    except JWTError:
        return None


async def _enforce_single_session(token_data: TokenData) -> Optional[TokenData]:
    """If the token has a jti AND the matching user has an
    active_session_id set AND they differ, return None (rejected).
    Otherwise return token_data unchanged.

    Back-compat rule (Fix #34): a token with no jti claim is always
    accepted (pre-Fix-34 issuance). A token with a jti whose matching
    user has active_session_id=None is rejected (the user logged out
    after the token was issued, so the token must be invalid). A
    token with a jti whose matching user has active_session_id set
    is rejected on mismatch (a 2nd-device login rotated the session).

    Async (Fix #35): the user lookup is now an indexed DB hit via
    ``user_manager.get_user_by_id(token_data.user_id)``. The pre-Fix-35
    O(n) linear scan over ``user_manager.users.values()`` is gone —
    that was the hidden cost of the JSON-file store.
    """
    if not token_data.jti:
        return token_data
    # Indexed DB hit on users.id. Replaces the O(n) scan.
    user = await user_manager.get_user_by_id(token_data.user_id)
    # If the user_id route misses (e.g. dev-mode tokens carry a
    # username but no id), fall back to a username lookup. One extra
    # DB hit, but dev-mode only.
    if user is None and token_data.username:
        user = await user_manager.get_user(token_data.username)
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


async def get_current_user(token: str) -> Optional[User]:
    """Get current user from token. Async (Fix #35) — delegates to
    ``user_manager.get_user_by_id`` for the user lookup."""
    token_data = await verify_token(token)
    if not token_data:
        return None

    # Indexed DB hit by user_id, fallback to username.
    user = await user_manager.get_user_by_id(token_data.user_id)
    if user is None and token_data.username:
        user = await user_manager.get_user(token_data.username)
    if user is not None and user.is_active:
        return user
    return None


async def get_current_user_with_reason(token: str) -> Tuple[Optional[User], Optional[str]]:
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

    Async (Fix #35) — the user lookup is now an indexed DB hit.
    """
    if not token:
        return None, "no_token"
    token_data = await verify_token(token)
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

    # Indexed DB hit on users.id, fallback to username.
    user = await user_manager.get_user_by_id(token_data.user_id)
    if user is None and token_data.username:
        user = await user_manager.get_user(token_data.username)
    if user is None:
        return None, "user_not_found"
    if not user.is_active:
        return None, "user_inactive"
    return user, None


async def require_auth(token: Optional[str]) -> User:
    """Require authentication - raises exception if not authenticated.
    Async (Fix #35) — calls ``get_current_user`` which is async."""
    from fastapi import HTTPException, status

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await get_current_user(token)
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
