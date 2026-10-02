from datetime import datetime

from pydantic import BaseModel


class UserRead(BaseModel):
    id: int
    email: str
    nickname: str | None = None
    created_at: datetime


class RegisterRequest(BaseModel):
    email: str
    password: str
    nickname: str | None = None
    openai_api_key: str | None = None
    notion_api_key: str | None = None
    notion_database_id: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
