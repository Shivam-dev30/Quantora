"""Cryptographic envelope encryption and decryption utilities for sensitive credentials.

Uses AES-256-GCM authenticated symmetric encryption.
Keys are derived using PBKDF2-HMAC-SHA256 from the master secret key with a deterministic salt.
"""

import base64
import os
from typing import Optional
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from backend.app.config.settings import get_config
from backend.app.core.logging import get_logger

logger = get_logger("crypto")

# Static salt used for key derivation across the application
_DERIVATION_SALT = b"quantora_credential_salt_v1"


def derive_aes_key(master_secret: str) -> bytes:
    """Derive a 256-bit (32 bytes) encryption key from the master secret using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_DERIVATION_SALT,
        iterations=100_000,
    )
    return kdf.derive(master_secret.encode("utf-8"))


def encrypt_secret(plaintext: Optional[str], secret_key: Optional[str] = None) -> Optional[str]:
    """Encrypt plaintext string using AES-256-GCM.
    
    Output format: base64(12-byte-nonce + ciphertext-and-16-byte-tag)
    Returns None if plaintext is empty or None.
    """
    if not plaintext:
        return plaintext

    if secret_key is None:
        cfg = get_config()
        secret_key = cfg.settings.secret_key

    key = derive_aes_key(secret_key)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit standard GCM nonce
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    
    # Prepend nonce to ciphertext and base64 encode
    payload = nonce + ciphertext
    return base64.b64encode(payload).decode("utf-8")


def decrypt_secret(encrypted_text: Optional[str], secret_key: Optional[str] = None) -> Optional[str]:
    """Decrypt AES-256-GCM ciphertext payload produced by encrypt_secret.
    
    Returns original plaintext if valid, or original string if not encrypted/malformed.
    """
    if not encrypted_text:
        return encrypted_text

    if secret_key is None:
        cfg = get_config()
        secret_key = cfg.settings.secret_key

    try:
        data = base64.b64decode(encrypted_text.encode("utf-8"))
        if len(data) < 28:  # 12-byte nonce + at least 16-byte GCM tag
            return encrypted_text

        nonce = data[:12]
        ciphertext = data[12:]
        key = derive_aes_key(secret_key)
        aesgcm = AESGCM(key)
        decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, None)
        return decrypted_bytes.decode("utf-8")
    except Exception:
        # If decryption fails (e.g. plaintext stored during development), return as is
        return encrypted_text
