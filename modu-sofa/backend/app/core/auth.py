"""Supabase JWT 검증.

- 레거시 HS256 프로젝트: SUPABASE_JWT_SECRET 으로 검증
- 비대칭 키(ES256/RS256) 프로젝트: {SUPABASE_URL}/auth/v1/.well-known/jwks.json 으로 검증
- DEV_AUTH_ENABLED=true 일 때만 "dev:<URL 인코딩된 닉네임>" 토큰 허용 (로컬 개발 전용)
"""

import uuid
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import unquote

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

_bearer = HTTPBearer(auto_error=False)
DEV_NAMESPACE = uuid.UUID("6c0b9f7e-3b2a-4a8e-9c61-5d0f3e2a1b44")


@dataclass(frozen=True)
class CurrentUser:
    id: uuid.UUID
    nickname: str | None = None


@lru_cache
def _jwks_client() -> jwt.PyJWKClient:
    return jwt.PyJWKClient(f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json")


def _unauthorized(detail: str = "로그인이 필요해요.") -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail=detail, headers={"WWW-Authenticate": "Bearer"})


def decode_token(token: str) -> CurrentUser:
    if settings.DEV_AUTH_ENABLED and token.startswith("dev:"):
        name = unquote(token[4:]) or "개발자"
        return CurrentUser(id=uuid.uuid5(DEV_NAMESPACE, name), nickname=name)

    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")
        if alg == "HS256":
            if not settings.SUPABASE_JWT_SECRET:
                raise _unauthorized()
            key = settings.SUPABASE_JWT_SECRET
        else:
            if not settings.SUPABASE_URL:
                raise _unauthorized()
            key = _jwks_client().get_signing_key_from_jwt(token).key
        payload = jwt.decode(token, key, algorithms=[alg], audience="authenticated")
    except HTTPException:
        raise
    except jwt.PyJWTError as e:
        raise _unauthorized("로그인이 만료되었어요. 다시 로그인해 주세요.") from e

    meta = payload.get("user_metadata") or {}
    nickname = meta.get("name") or meta.get("full_name") or meta.get("nickname") or meta.get("preferred_username")
    try:
        return CurrentUser(id=uuid.UUID(payload["sub"]), nickname=nickname)
    except (KeyError, ValueError) as e:
        raise _unauthorized() from e


def get_current_user(cred: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> CurrentUser:
    if cred is None or not cred.credentials:
        raise _unauthorized()
    return decode_token(cred.credentials)
