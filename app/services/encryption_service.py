import base64
import hashlib
import hmac
import os

from app.core.config import settings


def _key() -> bytes:
    return hashlib.sha256((settings.encryption_key or settings.secret_key).encode()).digest()


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    output = b""
    counter = 0
    while len(output) < length:
        output += hmac.new(key, nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest()
        counter += 1
    return output[:length]


def encrypt_secret(value: str | None) -> str | None:
    if not value:
        return None
    key = _key()
    nonce = os.urandom(16)
    plaintext = value.encode()
    ciphertext = bytes(a ^ b for a, b in zip(plaintext, _keystream(key, nonce, len(plaintext))))
    signature = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(nonce + signature + ciphertext).decode()


def decrypt_secret(value: str | None) -> str | None:
    if not value:
        return None
    try:
        raw = base64.urlsafe_b64decode(value.encode())
        nonce, signature, ciphertext = raw[:16], raw[16:48], raw[48:]
        key = _key()
        expected = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            return None
        plaintext = bytes(a ^ b for a, b in zip(ciphertext, _keystream(key, nonce, len(ciphertext))))
        return plaintext.decode()
    except (ValueError, UnicodeDecodeError):
        return None


def mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return value[0] + "••••" + value[-1]
    return value[:4] + "••••••••" + value[-4:]
