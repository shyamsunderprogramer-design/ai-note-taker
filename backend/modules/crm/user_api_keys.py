"""
User API Key Management System - BYOK (Bring Your Own Key)
Allows users to provide their own API keys for premium providers.
Keys are encrypted at rest using AES-256 via the EncryptionManager.
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("user_api_keys")

# Encryption at rest
try:
    from security.encryption import EncryptionManager, HAS_CRYPTOGRAPHY
    _encryption = EncryptionManager()
    ENCRYPTION_AVAILABLE = _encryption.is_available()
except ImportError:
    ENCRYPTION_AVAILABLE = False
    _encryption = None

# Fields that contain API keys and must be encrypted
ENCRYPTED_FIELDS = [
    "openai_key", "anthropic_key", "google_key", "xai_key",
    "deepseek_key", "groq_key", "perplexity_key", "ollama_cloud_key"
]

# Directory for storing user API keys (encrypted at rest)
USER_KEYS_DIR = Path("data/user_keys")
USER_KEYS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class UserAPIKeys:
    """User's personal API keys for premium providers"""

    user_id: str

    # Premium provider API keys (BYOK) — stored encrypted on disk
    openai_key: Optional[str] = None
    anthropic_key: Optional[str] = None
    google_key: Optional[str] = None
    xai_key: Optional[str] = None
    deepseek_key: Optional[str] = None
    groq_key: Optional[str] = None
    perplexity_key: Optional[str] = None
    ollama_cloud_key: Optional[str] = None

    # Metadata
    updated_at: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding sensitive keys)"""
        return {
            "user_id": self.user_id,
            "has_openai": bool(self.openai_key),
            "has_anthropic": bool(self.anthropic_key),
            "has_google": bool(self.google_key),
            "has_xai": bool(self.xai_key),
            "has_deepseek": bool(self.deepseek_key),
            "has_groq": bool(self.groq_key),
            "has_perplexity": bool(self.perplexity_key),
            "has_ollama_cloud": bool(self.ollama_cloud_key),
            "updated_at": self.updated_at,
            "created_at": self.created_at,
        }

    def get_active_providers(self) -> Dict[str, bool]:
        """Get dictionary of which providers have keys"""
        return {
            "openai": bool(self.openai_key),
            "anthropic": bool(self.anthropic_key),
            "google": bool(self.google_key),
            "xai": bool(self.xai_key),
            "deepseek": bool(self.deepseek_key),
            "groq": bool(self.groq_key),
            "perplexity": bool(self.perplexity_key),
            "ollama_cloud": bool(self.ollama_cloud_key),
        }

    def has_any_premium_key(self) -> bool:
        """Check if user has any premium API key"""
        return any([
            self.openai_key,
            self.anthropic_key,
            self.google_key,
            self.xai_key,
            self.deepseek_key,
            self.groq_key,
            self.perplexity_key,
            self.ollama_cloud_key,
        ])


class UserKeyManager:
    """Manages user API keys storage and retrieval"""

    def __init__(self):
        self._cache: Dict[str, UserAPIKeys] = {}

    def _get_key_file(self, user_id: str) -> Path:
        """Get path to user's key file"""
        # Sanitize user_id for filesystem
        safe_id = "".join(c for c in user_id if c.isalnum() or c in "-_")
        return USER_KEYS_DIR / f"{safe_id}_keys.json"

    def _save_keys(self, keys: UserAPIKeys):
        """Save user keys to disk (encrypted at rest)"""
        try:
            key_file = self._get_key_file(keys.user_id)

            data = {
                "user_id": keys.user_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "created_at": keys.created_at,
            }

            # Encrypt API keys before writing to disk
            for field in ENCRYPTED_FIELDS:
                value = getattr(keys, field, None) or ""
                if value and ENCRYPTION_AVAILABLE:
                    encrypted = _encryption.encrypt_str(value)
                    if encrypted:
                        data[field] = f"enc:{encrypted}"
                    else:
                        # Encryption failed — store as plaintext (should log warning)
                        logger.warning(f"[UserKeyManager] Encryption failed for {field}, storing plaintext")
                        data[field] = value
                else:
                    # No value or no encryption available — store empty
                    data[field] = value

            key_file.write_text(json.dumps(data, indent=2))

            # Set file permissions to owner-only (Unix-like systems)
            try:
                os.chmod(key_file, 0o600)
            except (OSError, AttributeError):
                pass  # Windows doesn't fully support chmod

            logger.info(f"[UserKeyManager] Saved keys for user: {keys.user_id}")
        except Exception as e:
            logger.error("[UserKeyManager] Failed to save keys: %s", str(e))
            raise

    def _load_keys(self, user_id: str) -> Optional[UserAPIKeys]:
        """Load user keys from disk (decrypt encrypted keys)"""
        try:
            key_file = self._get_key_file(user_id)
            if not key_file.exists():
                return None

            data = json.loads(key_file.read_text())

            # Decrypt API keys that are encrypted (prefixed with "enc:")
            decrypted_keys = {}
            for field in ENCRYPTED_FIELDS:
                value = data.get(field, "") or ""
                if value.startswith("enc:") and ENCRYPTION_AVAILABLE:
                    # Decrypt the key
                    decrypted = _encryption.decrypt_str(value[4:])
                    decrypted_keys[field] = decrypted if decrypted else None
                elif value.startswith("enc:"):
                    # Encrypted but encryption not available — can't decrypt
                    logger.warning(f"[UserKeyManager] Cannot decrypt {field} — encryption unavailable")
                    decrypted_keys[field] = None
                else:
                    # Plaintext (legacy or encryption unavailable)
                    decrypted_keys[field] = value or None

            return UserAPIKeys(
                user_id=data.get("user_id", user_id),
                openai_key=decrypted_keys.get("openai_key"),
                anthropic_key=decrypted_keys.get("anthropic_key"),
                google_key=decrypted_keys.get("google_key"),
                xai_key=decrypted_keys.get("xai_key"),
                deepseek_key=decrypted_keys.get("deepseek_key"),
                groq_key=decrypted_keys.get("groq_key"),
                perplexity_key=decrypted_keys.get("perplexity_key"),
                ollama_cloud_key=decrypted_keys.get("ollama_cloud_key"),
                updated_at=data.get("updated_at", ""),
                created_at=data.get("created_at", ""),
            )
        except Exception as e:
            logger.error("[UserKeyManager] Failed to load keys: %s", str(e))
            return None

    def get_user_keys(self, user_id: str) -> UserAPIKeys:
        """Get user's API keys (creates empty if not exists)"""
        if user_id not in self._cache:
            keys = self._load_keys(user_id)
            if keys is None:
                keys = UserAPIKeys(user_id=user_id)
            self._cache[user_id] = keys
        return self._cache[user_id]

    def update_keys(self, user_id: str, **kwargs) -> UserAPIKeys:
        """Update user's API keys"""
        keys = self.get_user_keys(user_id)

        # Update only provided keys
        for key_name, value in kwargs.items():
            if hasattr(keys, key_name) and key_name != "user_id":
                # Strip whitespace and validate
                if value:
                    value = value.strip()
                    if len(value) < 20:  # Basic validation
                        logger.warning(f"[UserKeyManager] Key too short for {key_name}")
                        continue
                setattr(keys, key_name, value)

        keys.updated_at = datetime.now(timezone.utc).isoformat()
        self._save_keys(keys)
        self._cache[user_id] = keys

        return keys

    def delete_keys(self, user_id: str, provider: Optional[str] = None):
        """Delete user's API keys (all or specific provider)"""
        if provider:
            # Delete specific provider key
            keys = self.get_user_keys(user_id)
            if hasattr(keys, f"{provider}_key"):
                setattr(keys, f"{provider}_key", None)
                self._save_keys(keys)
                self._cache[user_id] = keys
        else:
            # Delete all keys
            key_file = self._get_key_file(user_id)
            if key_file.exists():
                key_file.unlink()
            if user_id in self._cache:
                del self._cache[user_id]

    def get_provider_key(self, user_id: str, provider: str) -> Optional[str]:
        """Get a specific provider key for a user"""
        keys = self.get_user_keys(user_id)
        key_attr = f"{provider}_key"
        if hasattr(keys, key_attr):
            return getattr(keys, key_attr)
        return None

    def validate_key(self, provider: str, key: str) -> tuple[bool, str]:
        """Validate an API key format (basic validation)"""
        if not key:
            return False, "Key is empty"

        if len(key) < 20:
            return False, "Key too short"

        # Provider-specific validation
        patterns = {
            "openai": ("sk-", "Should start with 'sk-'"),
            "anthropic": ("", "No specific prefix required"),
            "google": ("", "No specific prefix required"),
            "xai": ("", "No specific prefix required"),
            "deepseek": ("", "No specific prefix required"),
            "groq": ("gsk_", "Should start with 'gsk_'"),
            "perplexity": ("pplx-", "Should start with 'pplx-'"),
            "ollama_cloud": ("", "No specific prefix required"),
        }

        if provider in patterns:
            prefix, message = patterns[provider]
            if prefix and not key.startswith(prefix):
                return False, f"Invalid format: {message}"

        return True, "Valid"


# Global key manager instance
user_key_manager = UserKeyManager()


def get_user_api_key(user_id: str, provider: str) -> Optional[str]:
    """Get a user's API key for a specific provider"""
    return user_key_manager.get_provider_key(user_id, provider)


def get_available_providers(user_id: str) -> Dict[str, bool]:
    """Get dict of available providers for a user"""
    keys = user_key_manager.get_user_keys(user_id)
    return keys.get_active_providers()


def has_premium_access(user_id: str) -> bool:
    """Check if user has any premium provider configured"""
    keys = user_key_manager.get_user_keys(user_id)
    return keys.has_any_premium_key()


def get_provider_for_mode(mode: str, user_id: Optional[str] = None) -> tuple[str, Optional[str]]:
    """
    Get the best available provider for a given mode
    Returns: (provider_name, api_key or None)

    Priority:
    1. User's configured premium keys (if user_id provided)
    2. Ollama (always free, always available)
    """
    if user_id:
        keys = user_key_manager.get_user_keys(user_id)

        # Mode-specific provider preferences
        mode_preferences = {
            "fast": ["groq", "openai", "anthropic", "ollama"],
            "reasoning": ["anthropic", "openai", "deepseek", "ollama"],
            "code": ["openai", "anthropic", "groq", "ollama"],
            "interview": ["anthropic", "openai", "google", "ollama"],
            "cloud": ["groq", "openai", "anthropic", "ollama"],
            "adaptive": ["openai", "anthropic", "groq", "ollama"],
        }

        preferences = mode_preferences.get(mode, ["openai", "anthropic", "ollama"])

        for provider in preferences:
            if provider == "ollama":
                # Ollama is always available
                return ("ollama", None)

            key = getattr(keys, f"{provider}_key", None)
            if key:
                return (provider, key)

    # Default to Ollama (free)
    return ("ollama", None)


# Provider costs per 1K tokens (approximate, for display purposes)
PROVIDER_COSTS = {
    "openai": {"input": 0.0015, "output": 0.002, "name": "OpenAI GPT-4o"},
    "anthropic": {"input": 0.003, "output": 0.015, "name": "Anthropic Claude 3"},
    "google": {"input": 0.0005, "output": 0.0015, "name": "Google Gemini"},
    "xai": {"input": 0.005, "output": 0.015, "name": "xAI Grok"},
    "deepseek": {"input": 0.00014, "output": 0.00028, "name": "DeepSeek V3"},
    "groq": {"input": 0.00059, "output": 0.00079, "name": "Groq (Llama/Mixtral)"},
    "perplexity": {"input": 0.0002, "output": 0.0002, "name": "Perplexity"},
    "ollama_cloud": {"input": 0, "output": 0, "name": "Ollama Cloud"},
    "ollama": {"input": 0, "output": 0, "name": "Ollama (Local - FREE)"},
}


def get_provider_cost_info(provider: str) -> Dict[str, Any]:
    """Get cost information for a provider"""
    return PROVIDER_COSTS.get(provider, {
        "input": 0,
        "output": 0,
        "name": provider.title()
    })
