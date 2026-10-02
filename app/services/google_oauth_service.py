import secrets
from urllib.parse import urlencode

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppError
from app.models.user import AuthAccount, User, UserSettings


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def build_google_login_url() -> tuple[str, str]:
    if not settings.google_client_id or not settings.google_redirect_uri:
        raise AppError("GOOGLE_OAUTH_NOT_CONFIGURED", "Google OAuth is not configured.", 500)
    state = secrets.token_urlsafe(24)
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}", state


async def exchange_google_code(code: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.google_redirect_uri,
            },
        )
        token_response.raise_for_status()
        access_token = token_response.json()["access_token"]
        user_response = await client.get(GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
        user_response.raise_for_status()
        return user_response.json()


def upsert_google_user(db: Session, profile: dict) -> tuple[User, bool]:
    provider_id = profile.get("sub")
    email = (profile.get("email") or "").strip().lower()
    if not provider_id or not email:
        raise AppError("INVALID_GOOGLE_PROFILE", "Google profile is missing required identity fields.", 400)
    account = db.query(AuthAccount).filter(AuthAccount.provider == "google", AuthAccount.provider_account_id == provider_id).first()
    if account:
        return account.user, False
    user = db.query(User).filter(User.email == email).first()
    created = user is None
    if not user:
        user = User(email=email, nickname=profile.get("name"))
        user.settings = UserSettings()
        db.add(user)
        db.flush()
    db.add(AuthAccount(user_id=user.id, provider="google", provider_account_id=provider_id, provider_email=email))
    db.commit()
    db.refresh(user)
    return user, created
