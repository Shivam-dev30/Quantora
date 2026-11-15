"""Unit tests for cryptographic envelope encryption (AES-256-GCM) and audit logging."""

import pytest
from backend.app.database.models import SystemEventModel
from backend.app.database.session import get_db_session
from backend.app.security.audit import log_security_event
from backend.app.security.crypto import decrypt_secret, derive_aes_key, encrypt_secret
from sqlalchemy import select


def test_aes_gcm_key_derivation():
    """Verify deterministic 32-byte key derivation from secret."""
    secret = "my-super-secret-key-for-testing"
    key1 = derive_aes_key(secret)
    key2 = derive_aes_key(secret)
    assert len(key1) == 32
    assert key1 == key2


def test_encrypt_and_decrypt_roundtrip():
    """Verify that sensitive strings can be encrypted and cleanly decrypted."""
    plaintext = "super_secret_broker_totp_or_api_secret_12345"
    key = "master-encryption-key-for-unit-tests"

    ciphertext = encrypt_secret(plaintext, secret_key=key)
    assert ciphertext is not None
    assert ciphertext != plaintext

    decrypted = decrypt_secret(ciphertext, secret_key=key)
    assert decrypted == plaintext


def test_decrypt_tampered_or_invalid_ciphertext():
    """Verify that tampering with ciphertext fails safely without raising uncaught exceptions."""
    plaintext = "confidential_broker_password"
    key = "master-key"
    ciphertext = encrypt_secret(plaintext, secret_key=key)
    
    # Tamper with the base64 string
    tampered = ciphertext[:-4] + "AAAA"
    # Decrypt returns original string on failure instead of crashing
    result = decrypt_secret(tampered, secret_key=key)
    assert result == tampered


@pytest.mark.asyncio
async def test_audit_log_persistence():
    """Verify that security audit events are persisted to SystemEventModel."""
    await log_security_event(
        event_type="TEST_SECURITY_EVENT",
        message="Simulated security test event",
        severity="INFO",
        username="audit_tester",
        client_ip="127.0.0.1",
        component="test_suite",
    )

    async with get_db_session() as session:
        stmt = select(SystemEventModel).where(SystemEventModel.event_type == "TEST_SECURITY_EVENT")
        res = await session.execute(stmt)
        event = res.scalars().first()
        assert event is not None
        assert "Simulated security test event" in event.description
        assert event.provider == "test_suite"
