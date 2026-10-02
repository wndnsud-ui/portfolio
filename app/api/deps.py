from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import decode_access_token


async def get_current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError("AUTH_REQUIRED", "Authentication is required.", 401)
    payload = decode_access_token(authorization.split(" ", 1)[1])
    user = db.get(User, int(payload["sub"]))
    if not user:
        raise AppError("USER_NOT_FOUND", "User not found.", 401)
    return user
