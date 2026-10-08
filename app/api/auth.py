from fastapi import APIRouter, Cookie, Depends, Query, Response
from fastapi.responses import RedirectResponse
import hmac
import httpx
import logging
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.services.password_reset_service import request_reset, reset_password

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

class ForgotPassword(BaseModel):
    email: str = Field(min_length=3, max_length=320)

class ResetPassword(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    password: str = Field(min_length=8, max_length=128)

@router.post("/forgot-password")
def forgot_password(payload: ForgotPassword, db: Session = Depends(get_db)):
    request_reset(db, payload.email)
    return {"message": "가입된 이메일이라면 재설정 링크를 보냈습니다. Google 계정은 Google로 로그인해 주세요."}

@router.post("/reset-password")
def password_reset(payload: ResetPassword, db: Session = Depends(get_db)):
    reset_password(db, payload.token, payload.password)
    return {"message": "비밀번호가 변경되었습니다. 다시 로그인해 주세요."}


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


@router.delete("/example-data", status_code=204)
def delete_example_data(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from app.models.project import Project
    from app.models.workflow import FinalResult, TaskProgress
    from app.models.action_item import ActionItem
    from app.models.workflow import TaskComment, TaskReview, ActivityLog, Notification, TaskAttachment, CommentMention, MeetingReview
    # SQLite development connections may not enforce FK cascades.
    for project in db.query(Project).filter_by(user_id=user.id, workspace_id=None, is_example=True).all():
        ids = [t.id for t in project.action_items]
        if ids:
            comment_ids = [c.id for c in db.query(TaskComment).filter(TaskComment.task_id.in_(ids))]
            if comment_ids:
                db.query(CommentMention).filter(CommentMention.comment_id.in_(comment_ids)).delete(synchronize_session=False)
            for model in [FinalResult, TaskProgress, TaskComment, TaskReview, TaskAttachment]:
                db.query(model).filter(model.task_id.in_(ids)).delete(synchronize_session=False)
            db.query(Notification).filter(Notification.target_type=="task", Notification.target_id.in_(ids)).delete(synchronize_session=False)
        meeting_ids = [m.id for m in project.meetings]
        if meeting_ids:
            db.query(MeetingReview).filter(MeetingReview.meeting_id.in_(meeting_ids)).delete(synchronize_session=False)
            db.query(Notification).filter(Notification.target_type=="meeting", Notification.target_id.in_(meeting_ids)).delete(synchronize_session=False)
        db.query(ActivityLog).filter_by(project_id=project.id).delete(synchronize_session=False)
        db.delete(project)
    db.commit()


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
    redirect.set_cookie("google_oauth_state", state, httponly=True, secure=settings.app_env=="production", samesite="lax", max_age=600)
    return redirect


@router.get("/google/callback")
async def google_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    google_oauth_state: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    if not google_oauth_state or not state or not hmac.compare_digest(google_oauth_state, state):
        raise AppError("INVALID_OAUTH_STATE", "Google OAuth state validation failed.", 400)
    if error or not code:
        redirect = RedirectResponse(f"{settings.frontend_url}/?auth_error=google_cancelled")
        redirect.delete_cookie("google_oauth_state")
        return redirect
    try:
        profile = await exchange_google_code(code)
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        reason = "google_failed"
        if isinstance(exc, httpx.RequestError):
            reason = "google_network"
        elif isinstance(exc, httpx.HTTPStatusError):
            try:
                provider_error = exc.response.json().get("error")
            except ValueError:
                provider_error = None
            if provider_error == "invalid_client":
                reason = "google_credentials"
            elif provider_error == "invalid_grant":
                reason = "google_code_expired"
        # Log only a fixed reason, never callback URLs, codes, secrets or tokens.
        logging.getLogger(__name__).warning("Google OAuth failed: %s", reason)
        redirect = RedirectResponse(f"{settings.frontend_url}/?auth_error={reason}")
        redirect.delete_cookie("google_oauth_state")
        return redirect
    user, created = upsert_google_user(db, profile)
    onboarding = "1" if created else "0"
    redirect = RedirectResponse(f"{settings.frontend_url}/#token={create_access_token(user)}&onboarding={onboarding}", headers={"Cache-Control":"no-store", "Referrer-Policy":"no-referrer"})
    redirect.delete_cookie("google_oauth_state")
    return redirect
