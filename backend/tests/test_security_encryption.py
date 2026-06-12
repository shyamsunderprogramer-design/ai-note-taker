"""
Test suite for backend/security/encryption.py
Covers EncryptionManager (Fernet-based AES-128-CBC + HMAC), and the
FieldEncryption helper for `ENC:` / `ENC_BYTES:` prefixed dict fields.

EncryptionManager._get_default_key_file() writes a key under
~/.config/ai-note-taker/master.key (or %LOCALAPPDATA% on Windows).
We avoid touching the user's real key directory by passing a custom
key_file to the constructor in every test.

Run with: python -m pytest backend/tests/test_security_encryption.py -v
"""

import os
import sys

import pytest

# Add backend/ to sys.path so `from security.encryption import ...` resolves.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from security.encryption import (  # noqa: E402
    EncryptionManager,
    FieldEncryption,
    HAS_CRYPTOGRAPHY,
)


# Skip the whole module if cryptography isn't available (rare in dev,
# but possible in minimal CI images).
pytestmark = pytest.mark.skipif(
    not HAS_CRYPTOGRAPHY,
    reason="cryptography library not installed",
)


class TestEncryptionManagerRoundTrip:
    """Encrypt + decrypt of the same data returns the original."""

    def test_encrypt_decrypt_bytes(self, tmp_path):
        mgr = EncryptionManager(key_file=str(tmp_path / "master.key"))
        plaintext = b"hello, world"
        ciphertext = mgr.encrypt(plaintext)
        assert ciphertext is not None  # nosec B101
        assert ciphertext != plaintext  # not plaintext in output
        assert mgr.decrypt(ciphertext) == plaintext  # nosec B101

    def test_encrypt_decrypt_str(self, tmp_path):
        mgr = EncryptionManager(key_file=str(tmp_path / "master.key"))
        plaintext = "secret message"
        ciphertext = mgr.encrypt_str(plaintext)
        assert ciphertext is not None  # nosec B101
        assert plaintext not in ciphertext  # no plaintext leak in base64
        assert mgr.decrypt_str(ciphertext) == plaintext  # nosec B101

    def test_encrypt_unicode(self, tmp_path):
        mgr = EncryptionManager(key_file=str(tmp_path / "master.key"))
        plaintext = "héllo wörld 🦀"
        ciphertext = mgr.encrypt_str(plaintext)
        assert mgr.decrypt_str(ciphertext) == plaintext  # nosec B101

    def test_documented_limitation_empty_string_decrypt_returns_none(self, tmp_path):
        # DOCUMENTED BUG: `decrypt_str` returns None for an empty
        # string because `if decrypted else None` treats `b""` as
        # falsy. Empty-string round-trip is therefore broken — the
        # encrypt side succeeds but the decrypt side returns None
        # instead of the original empty string. Callers should not
        # encrypt empty strings. Pinned here so a fix is noticed.
        mgr = EncryptionManager(key_file=str(tmp_path / "master.key"))
        ciphertext = mgr.encrypt_str("")
        assert ciphertext is not None  # nosec B101
        assert mgr.decrypt_str(ciphertext) is None  # nosec B101


class TestEncryptionManagerDeterminism:
    """Each encrypt() call produces a different ciphertext (Fernet
    uses a random IV per encrypt), but decrypt recovers the plaintext."""

    def test_encrypt_produces_different_ciphertexts(self, tmp_path):
        mgr = EncryptionManager(key_file=str(tmp_path / "master.key"))
        a = mgr.encrypt_str("same plaintext")
        b = mgr.encrypt_str("same plaintext")
        # Fernet includes a random IV + timestamp → output should differ
        assert a != b  # nosec B101
        # But both decrypt to the same plaintext
        assert mgr.decrypt_str(a) == mgr.decrypt_str(b) == "same plaintext"  # nosec B101


class TestEncryptionManagerKeyPersistence:
    """EncryptionManager loads an existing key from disk on second run."""

    def test_key_persists_across_instances(self, tmp_path):
        key_file = tmp_path / "master.key"
        mgr1 = EncryptionManager(key_file=str(key_file))
        ciphertext = mgr1.encrypt_str("persistent")
        # New instance reads the same key
        mgr2 = EncryptionManager(key_file=str(key_file))
        assert mgr2.decrypt_str(ciphertext) == "persistent"  # nosec B101

    def test_key_file_has_restrictive_permissions(self, tmp_path):
        key_file = tmp_path / "master.key"
        EncryptionManager(key_file=str(key_file))
        # On Unix, the key should be 0o600. Skip on Windows where
        # chmod is a no-op.
        if os.name == "nt":
            pytest.skip("chmod is unreliable on Windows")
        mode = key_file.stat().st_mode & 0o777
        assert mode == 0o600, f"Expected 0o600, got {oct(mode)}"  # nosec B101


class TestEncryptionManagerTampering:
    """Modifying the ciphertext should cause decrypt to fail."""

    def test_tampered_ciphertext_fails_decrypt(self, tmp_path):
        mgr = EncryptionManager(key_file=str(tmp_path / "master.key"))
        ciphertext = mgr.encrypt_str("important")
        # Flip a byte in the middle of the base64 string
        mid = len(ciphertext) // 2
        tampered = ciphertext[:mid] + ("A" if ciphertext[mid] != "A" else "B") + ciphertext[mid+1:]
        # Either decrypt returns None (Fernet HMAC catches it) or raises
        # InvalidToken. The wrapper catches both → returns None.
        assert mgr.decrypt_str(tampered) is None  # nosec B101


class TestEncryptionManagerIsAvailable:
    """is_available reports the actual state."""

    def test_is_available_with_crypto(self, tmp_path):
        mgr = EncryptionManager(key_file=str(tmp_path / "master.key"))
        assert mgr.is_available() is True  # nosec B101


class TestApiKeyHelpers:
    """encrypt_api_key / decrypt_api_key at the module level."""

    def test_encrypt_then_decrypt(self, tmp_path, monkeypatch):
        # Use a fresh EncryptionManager (the module-level one is OK,
        # but to avoid touching the user's real key file we replace
        # the module's singleton for this test only).
        from security import encryption as enc_module
        original = enc_module.encryption_manager
        enc_module.encryption_manager = EncryptionManager(
            key_file=str(tmp_path / "master.key")
        )
        try:
            encrypted = enc_module.encrypt_api_key("sk-test-12345")
            assert encrypted is not None  # nosec B101
            assert encrypted.startswith("enc:")  # nosec B101
            assert "sk-test-12345" not in encrypted  # plaintext not in output

            decrypted = enc_module.decrypt_api_key(encrypted)
            assert decrypted == "sk-test-12345"  # nosec B101
        finally:
            enc_module.encryption_manager = original

    def test_decrypt_plaintext_passthrough(self, monkeypatch):
        # A key that doesn't have the "enc:" prefix is returned as-is.
        # This is the "backward-compat" path for keys stored before
        # encryption was enabled.
        from security import encryption as enc_module
        assert enc_module.decrypt_api_key("plaintext-key") == "plaintext-key"  # nosec B101

    def test_encrypt_empty_key_returns_none(self):
        from security import encryption as enc_module
        assert enc_module.encrypt_api_key("") is None  # nosec B101

    def test_decrypt_empty_key_returns_none(self):
        from security import encryption as enc_module
        assert enc_module.decrypt_api_key("") is None  # nosec B101


class TestFieldEncryption:
    """FieldEncryption: encrypt_dict / decrypt_dict with ENC: prefix."""

    def test_encrypt_dict_marks_fields(self, tmp_path):
        mgr = EncryptionManager(key_file=str(tmp_path / "master.key"))
        fe = FieldEncryption(mgr)
        data = {"name": "alice", "api_key": "sk-secret-123"}
        result = fe.encrypt_dict(data, fields_to_encrypt=["api_key"])
        assert result["name"] == "alice"  # nosec B101
        assert result["api_key"].startswith("ENC:")  # nosec B101
        assert "sk-secret-123" not in result["api_key"]  # nosec B101

    def test_decrypt_dict_recovers_values(self, tmp_path):
        mgr = EncryptionManager(key_file=str(tmp_path / "master.key"))
        fe = FieldEncryption(mgr)
        original = {"name": "alice", "api_key": "sk-secret-123"}
        encrypted = fe.encrypt_dict(original, fields_to_encrypt=["api_key"])
        decrypted = fe.decrypt_dict(encrypted, fields_to_encrypt=["api_key"])
        assert decrypted == original  # nosec B101

    def test_encrypt_dict_skips_unlisted_fields(self, tmp_path):
        mgr = EncryptionManager(key_file=str(tmp_path / "master.key"))
        fe = FieldEncryption(mgr)
        data = {"name": "alice", "api_key": "sk-secret"}
        result = fe.encrypt_dict(data, fields_to_encrypt=["name"])
        # "name" was supposed to be encrypted, "api_key" was not
        assert result["name"].startswith("ENC:")  # nosec B101
        assert result["api_key"] == "sk-secret"  # nosec B101

    def test_encrypt_dict_skips_empty_values(self, tmp_path):
        mgr = EncryptionManager(key_file=str(tmp_path / "master.key"))
        fe = FieldEncryption(mgr)
        data = {"api_key": ""}
        result = fe.encrypt_dict(data, fields_to_encrypt=["api_key"])
        # Empty string is left as-is (no encryption)
        assert result["api_key"] == ""  # nosec B101

    def test_decrypt_dict_handles_enc_bytes_prefix(self, tmp_path):
        mgr = EncryptionManager(key_file=str(tmp_path / "master.key"))
        fe = FieldEncryption(mgr)
        data = {"blob": b"raw bytes here"}
        encrypted = fe.encrypt_dict(data, fields_to_encrypt=["blob"])
        assert encrypted["blob"].startswith("ENC_BYTES:")  # nosec B101
        decrypted = fe.decrypt_dict(encrypted, fields_to_encrypt=["blob"])
        assert decrypted["blob"] == b"raw bytes here"  # nosec B101

    def test_decrypt_dict_leaves_unencrypted_values_alone(self, tmp_path):
        mgr = EncryptionManager(key_file=str(tmp_path / "master.key"))
        fe = FieldEncryption(mgr)
        data = {"name": "plain alice"}
        result = fe.decrypt_dict(data, fields_to_encrypt=["api_key"])
        # "name" is not in the encrypted list and doesn't start with ENC:
        assert result == data  # nosec B101


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
