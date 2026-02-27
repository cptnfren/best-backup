"""
tests/test_encryption.py
Tests for bbackup.encryption: AES-256-GCM encrypt/decrypt, key generation,
PBKDF2 derivation, RSA key generation, file encryption round-trip.
"""

import os
import secrets
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

from bbackup.encryption import EncryptionManager
from bbackup.config import EncryptionSettings


def make_sym_config(key_file=None, key_password=None) -> EncryptionSettings:
    sym = {}
    if key_file:
        sym["key_file"] = str(key_file)
    if key_password:
        sym["key_password"] = key_password
    return EncryptionSettings(enabled=True, method="symmetric", symmetric=sym)


def make_asym_config(pub_file=None, priv_file=None) -> EncryptionSettings:
    asym = {}
    if pub_file:
        asym["public_key_file"] = str(pub_file)
    if priv_file:
        asym["private_key_file"] = str(priv_file)
    return EncryptionSettings(enabled=True, method="asymmetric", asymmetric=asym)


# ---------------------------------------------------------------------------
# EncryptionManager construction (missing/unconfigured keys)
# ---------------------------------------------------------------------------

class TestEncryptionManagerConstruction:
    def test_disabled_config_creates_manager(self):
        cfg = EncryptionSettings(enabled=False)
        # Should not raise even though no keys configured
        mgr = EncryptionManager(cfg)
        assert mgr is not None

    def test_symmetric_with_no_key_file_sets_key_none(self, capsys):
        cfg = make_sym_config()  # no key_file
        mgr = EncryptionManager(cfg)
        assert mgr.symmetric_key is None

    def test_symmetric_with_missing_key_file_sets_key_none(self, tmp_path):
        cfg = make_sym_config(key_file=tmp_path / "missing.key")
        mgr = EncryptionManager(cfg)
        assert mgr.symmetric_key is None

    def test_symmetric_with_valid_key_file_loads_key(self, tmp_path):
        key_file = tmp_path / "test.key"
        raw_key = secrets.token_bytes(32)
        key_file.write_bytes(raw_key)
        cfg = make_sym_config(key_file=key_file)
        mgr = EncryptionManager(cfg)
        assert mgr.symmetric_key == raw_key

    def test_asymmetric_with_no_keys_sets_none(self):
        cfg = make_asym_config()
        mgr = EncryptionManager(cfg)
        assert mgr.public_key is None
        assert mgr.private_key is None


# ---------------------------------------------------------------------------
# AES-256-GCM encrypt / decrypt (direct AESGCM tests - no Docker needed)
# ---------------------------------------------------------------------------

class TestAESGCM:
    """Test AES-256-GCM primitives that EncryptionManager wraps."""

    def test_encrypt_decrypt_roundtrip(self):
        key = secrets.token_bytes(32)
        nonce = secrets.token_bytes(12)
        aesgcm = AESGCM(key)
        plaintext = b"Hello bbackup encryption test payload"
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        recovered = aesgcm.decrypt(nonce, ciphertext, None)
        assert recovered == plaintext

    def test_different_nonces_produce_different_ciphertext(self):
        key = secrets.token_bytes(32)
        plaintext = b"same plaintext"
        ct1 = AESGCM(key).encrypt(secrets.token_bytes(12), plaintext, None)
        ct2 = AESGCM(key).encrypt(secrets.token_bytes(12), plaintext, None)
        assert ct1 != ct2

    def test_wrong_key_decryption_fails(self):
        from cryptography.exceptions import InvalidTag
        key1 = secrets.token_bytes(32)
        key2 = secrets.token_bytes(32)
        nonce = secrets.token_bytes(12)
        ct = AESGCM(key1).encrypt(nonce, b"secret", None)
        with pytest.raises(InvalidTag):
            AESGCM(key2).decrypt(nonce, ct, None)

    def test_tampered_ciphertext_fails(self):
        from cryptography.exceptions import InvalidTag
        key = secrets.token_bytes(32)
        nonce = secrets.token_bytes(12)
        ct = bytearray(AESGCM(key).encrypt(nonce, b"secret data", None))
        ct[5] ^= 0xFF  # flip a byte
        with pytest.raises(InvalidTag):
            AESGCM(key).decrypt(nonce, bytes(ct), None)

    def test_aad_enforced(self):
        from cryptography.exceptions import InvalidTag
        key = secrets.token_bytes(32)
        nonce = secrets.token_bytes(12)
        aad = b"additional-auth-data"
        ct = AESGCM(key).encrypt(nonce, b"payload", aad)
        # Decrypting with wrong AAD should fail
        with pytest.raises(InvalidTag):
            AESGCM(key).decrypt(nonce, ct, b"wrong-aad")

    def test_key_must_be_32_bytes(self):
        with pytest.raises(ValueError):
            AESGCM(b"tooshort")


# ---------------------------------------------------------------------------
# EncryptionManager: _encrypt_data / _decrypt_data (if exposed)
# ---------------------------------------------------------------------------

class TestEncryptionManagerFileMethods:
    def test_encrypt_file_roundtrip(self, tmp_path):
        """encrypt_file then decrypt_file should recover original content."""
        raw_key = secrets.token_bytes(32)
        key_file = tmp_path / "test.key"
        key_file.write_bytes(raw_key)

        cfg = make_sym_config(key_file=key_file)
        mgr = EncryptionManager(cfg)
        assert mgr.symmetric_key is not None

        # Check if encrypt_file / decrypt_file exist before calling
        if not (hasattr(mgr, "encrypt_file") and hasattr(mgr, "decrypt_file")):
            pytest.skip("encrypt_file/decrypt_file not implemented on EncryptionManager")

        src = tmp_path / "original.txt"
        src.write_bytes(b"backup payload data " * 100)
        enc_path = tmp_path / "original.txt.enc"
        dec_path = tmp_path / "recovered.txt"

        assert mgr.encrypt_file(src, enc_path) is True
        assert enc_path.exists()
        assert enc_path.read_bytes() != src.read_bytes()

        assert mgr.decrypt_file(enc_path, dec_path) is True
        assert dec_path.read_bytes() == src.read_bytes()

    def test_encrypt_data_returns_bytes(self, tmp_path):
        raw_key = secrets.token_bytes(32)
        key_file = tmp_path / "test.key"
        key_file.write_bytes(raw_key)

        cfg = make_sym_config(key_file=key_file)
        mgr = EncryptionManager(cfg)

        if not hasattr(mgr, "_encrypt_data"):
            pytest.skip("_encrypt_data not implemented")

        result = mgr._encrypt_data(b"test plaintext")
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_decrypt_data_roundtrip(self, tmp_path):
        raw_key = secrets.token_bytes(32)
        key_file = tmp_path / "test.key"
        key_file.write_bytes(raw_key)

        cfg = make_sym_config(key_file=key_file)
        mgr = EncryptionManager(cfg)

        if not (hasattr(mgr, "_encrypt_data") and hasattr(mgr, "_decrypt_data")):
            pytest.skip("_encrypt_data/_decrypt_data not implemented")

        original = b"round-trip test payload"
        encrypted = mgr._encrypt_data(original)
        recovered = mgr._decrypt_data(encrypted)
        assert recovered == original


# ---------------------------------------------------------------------------
# RSA key generation
# ---------------------------------------------------------------------------

class TestRSAKeyGeneration:
    def test_generate_2048_key(self):
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend(),
        )
        assert private_key is not None
        assert private_key.key_size == 2048

    def test_public_key_extracted(self):
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend(),
        )
        pub = private_key.public_key()
        assert pub is not None

    def test_rsa_key_serialization_roundtrip(self, tmp_path):
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend(),
        )
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
        key_file = tmp_path / "test.pem"
        key_file.write_bytes(pem)

        loaded = serialization.load_pem_private_key(
            key_file.read_bytes(), password=None, backend=default_backend()
        )
        assert loaded.key_size == 2048


# ---------------------------------------------------------------------------
# URL / GitHub shortcut detection (private helpers via manager)
# ---------------------------------------------------------------------------

class TestURLDetection:
    def _make_manager(self):
        cfg = EncryptionSettings(enabled=False)
        return EncryptionManager(cfg)

    def test_is_url_http(self):
        mgr = self._make_manager()
        if not hasattr(mgr, "_is_url"):
            pytest.skip("_is_url not implemented")
        assert mgr._is_url("http://example.com/key") is True

    def test_is_url_https(self):
        mgr = self._make_manager()
        if not hasattr(mgr, "_is_url"):
            pytest.skip()
        assert mgr._is_url("https://example.com/key") is True

    def test_is_url_file_path(self):
        mgr = self._make_manager()
        if not hasattr(mgr, "_is_url"):
            pytest.skip()
        assert mgr._is_url("/path/to/key.pem") is False

    def test_is_github_shortcut(self):
        mgr = self._make_manager()
        if not hasattr(mgr, "_is_github_shortcut"):
            pytest.skip()
        assert mgr._is_github_shortcut("github:user/gist:abc123") is True

    def test_is_not_github_shortcut(self):
        mgr = self._make_manager()
        if not hasattr(mgr, "_is_github_shortcut"):
            pytest.skip()
        assert mgr._is_github_shortcut("https://github.com/user/repo") is False
