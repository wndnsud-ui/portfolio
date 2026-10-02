from fastapi import APIRouter, Cookie, Depends, Query, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.exceptions import AppError
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserRead
from app.services.auth_service import authenticate, create_access_token, create_user
from app.services.encryption_service import encrypt_secret
from app.services.google_oauth_service import build_google_login_url, exchange_google_code, upsert_google_user

router = APIRouter(prefix="/auth", tags=["Auth"])


def auth_response(user: User) -> AuthResponse:
    return AuthResponse(access_token=create_access_token(user), user=UserRead.model_validate(user, from_attributes=True))


@router.post("/register", response_model=AuthResponse)
async def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    if len(payload.password) < 8:
        raise AppError("WEAK_PASSWORD", "Password must be at least 8 characters.", 400)
    user = create_user(db, payload.email, payload.password, payload.nickname)
    if user.settings:
        user.settings.openai_api_key_encrypted = encrypt_secret(payload.openai_api_key)
        user.settings.notion_api_key_encrypted = encrypt_secret(payload.notion_api_key)
        user.settings.notion_database_id = payload.notion_database_id
        db.commit()
        db.refresh(user)
    return auth_response(user)


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    return auth_response(authenticate(db, payload.email, payload.password))


@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/logout")
async def logout() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/google/status")
async def google_status() -> dict[str, bool]:
    return {
        "configured": bool(
            settings.google_client_id
            and settings.google_client_secret
            and settings.google_redirect_uri
        )
    }


@router.get("/google/login")
async def google_login(response: Response) -> RedirectResponse:
    url, state = build_google_login_url()
    redirect = RedirectResponse(url)
    redirect.set_cookie("google_oauth_state", state, httponly=True, samesite="lax", max_age=600)
    return redirect


@router.get("/google/callback")
async def google_callback(
    code: str = Query(...),
    state: str = Query(...),
    google_oauth_state: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    if not google_oauth_state or google_oauth_state != state:
        raise AppError("INVALID_OAUTH_STATE", "Google OAuth state validation failed.", 400)
    profile = await exchange_google_code(code)
    user, created = upsert_google_user(db, profile)
    onboarding = "1" if created else "0"
    redirect = RedirectResponse(f"{settings.frontend_url}/?token={create_access_token(user)}&onboarding={onboarding}")
    redirect.delete_cookie("google_oauth_state")
    return redirect
