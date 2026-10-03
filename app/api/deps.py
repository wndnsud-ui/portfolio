from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import decode_access_token
from app.services.encryption_service import decrypt_secret
from app.services.integration_context import credentials


async def get_current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError("AUTH_REQUIRED", "Authentication is required.", 401)
    payload = decode_access_token(authorization.split(" ", 1)[1])
    user = db.get(User, int(payload["sub"]))
    if not user:
        raise AppError("USER_NOT_FOUND", "User not found.", 401)
    personal = user.settings
    context_token = credentials.set({
        "openai_api_key": decrypt_secret(personal.openai_api_key_encrypted) if personal else None,
        "notion_api_key": decrypt_secret(personal.notion_api_key_encrypted) if personal else None,
        "notion_database_id": personal.notion_database_id if personal else None,
    })
    try:
        yield user
    finally:
        credentials.reset(context_token)
