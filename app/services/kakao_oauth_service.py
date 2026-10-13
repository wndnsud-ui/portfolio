import secrets
import httpx
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from urllib.parse import urlencode

from app.core.config import settings
from app.core.exceptions import AppError
from app.models.user import PLACEHOLDER_EMAIL_DOMAIN, AuthAccount, User, UserSettings


def build_kakao_login_url() -> tuple[str, str]:
    if not settings.kakao_client_id or not settings.kakao_redirect_uri:
        raise AppError("KAKAO_OAUTH_NOT_CONFIGURED", "Kakao REST API key and redirect URI are required.", 503)
    state = secrets.token_urlsafe(24)
    params = {
        "client_id": settings.kakao_client_id,
        "redirect_uri": settings.kakao_redirect_uri,
        "response_type": "code",
        "state": state,
    }
    return f"https://kauth.kakao.com/oauth/authorize?{urlencode(params)}", state


async def exchange_kakao_code(code: str) -> dict:
    data = {
        "grant_type": "authorization_code",
        "client_id": settings.kakao_client_id,
        "redirect_uri": settings.kakao_redirect_uri,
        "code": code,
    }
    if settings.kakao_client_secret:
        data["client_secret"] = settings.kakao_client_secret
    async with httpx.AsyncClient(timeout=15) as client:
        token = await client.post("https://kauth.kakao.com/oauth/token", data=data)
        token.raise_for_status()
        profile = await client.get(
            "https://kapi.kakao.com/v2/user/me",
            headers={"Authorization": f"Bearer {token.json()['access_token']}"},
            params={"property_keys": '["kakao_account.profile.nickname"]'},
        )
        profile.raise_for_status()
        return profile.json()


def upsert_kakao_user(db: Session, profile: dict) -> tuple[User, bool]:
    provider_id = profile.get("id")
    if type(provider_id) is not int or provider_id <= 0:
        raise AppError("INVALID_KAKAO_PROFILE", "Kakao user ID is missing or invalid.", 400)
    provider_id = str(provider_id)
    account = db.query(AuthAccount).filter_by(provider="kakao", provider_account_id=provider_id).first()
    if account:
        return account.user, False
    nickname = ((profile.get("kakao_account") or {}).get("profile") or {}).get("nickname")
    # Existing users schema requires an email. This reserved address is only
    # an internal identifier; never merge accounts using it or send mail to it.
    user = User(email=f"kakao-{provider_id}{PLACEHOLDER_EMAIL_DOMAIN}", nickname=(nickname or "Kakao")[:120])
    user.settings = UserSettings()
    db.add(user)
    try:
        db.flush()
        db.add(AuthAccount(user_id=user.id, provider="kakao", provider_account_id=provider_id))
        db.commit()
    except IntegrityError:
        db.rollback()
        account = db.query(AuthAccount).filter_by(provider="kakao", provider_account_id=provider_id).first()
        if account:
            return account.user, False
        raise AppError("KAKAO_ACCOUNT_CONFLICT", "Kakao account could not be created.", 409)
    db.refresh(user)
    return user, True
