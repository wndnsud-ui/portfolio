import base64
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppError
from app.models.user import User, UserSettings


TOKEN_TTL_SECONDS = 60 * 60 * 24 * 7


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 390000)
    return "pbkdf2_sha256$390000$" + base64.urlsafe_b64encode(salt).decode() + "$" + base64.urlsafe_b64encode(digest).decode()


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        algorithm, rounds, salt, expected = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.urlsafe_b64decode(salt), int(rounds))
        return hmac.compare_digest(base64.urlsafe_b64encode(digest).decode(), expected)
    except (ValueError, TypeError):
        return False


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def create_access_token(user: User) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": str(user.id), "email": user.email, "ver": user.auth_version or 0, "iat": now, "exp": now + TOKEN_TTL_SECONDS}
    signing_input = f"{_b64(json.dumps(header, separators=(',', ':')).encode())}.{_b64(json.dumps(payload, separators=(',', ':')).encode())}"
    signature = hmac.new(settings.secret_key.encode(), signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{_b64(signature)}"


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        signing_input, signature = token.rsplit(".", 1)
        expected = _b64(hmac.new(settings.secret_key.encode(), signing_input.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError
        payload = json.loads(_unb64(signing_input.split(".")[1]))
    except (ValueError, IndexError, json.JSONDecodeError):
        raise AppError("INVALID_TOKEN", "Invalid authentication token.", 401)
    if int(payload.get("exp", 0)) < int(time.time()):
        raise AppError("TOKEN_EXPIRED", "Authentication token expired.", 401)
    return payload


def create_user(db: Session, email: str, password: str | None = None, nickname: str | None = None) -> User:
    normalized = email.strip().lower()
    if db.query(User).filter(User.email == normalized).first():
        raise AppError("EMAIL_EXISTS", "Email is already registered.", 409)
    user = User(email=normalized, nickname=nickname, password_hash=hash_password(password) if password else None)
    user.settings = UserSettings()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email.strip().lower()).first()
    if not user or not verify_password(password, user.password_hash):
        raise AppError("INVALID_CREDENTIALS", "Email or password is incorrect.", 401)
    return user
