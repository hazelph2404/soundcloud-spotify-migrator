"""Encrypt OAuth tokens at rest with Fernet (AES-128-CBC + HMAC)."""

from cryptography.fernet import Fernet

from app.config import get_settings

settings = get_settings()

_key = settings.token_encryption_key or Fernet.generate_key().decode()
if not settings.token_encryption_key:
    # Dev convenience: without a stable key, tokens don't survive a restart.
    print(f"[crypto] TOKEN_ENCRYPTION_KEY unset — using an ephemeral key: {_key}")

_fernet = Fernet(_key.encode() if isinstance(_key, str) else _key)


def encrypt(plaintext: str) -> bytes:
    return _fernet.encrypt(plaintext.encode())


def decrypt(ciphertext: bytes) -> str:
    return _fernet.decrypt(ciphertext).decode()
