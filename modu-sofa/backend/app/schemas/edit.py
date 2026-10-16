import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CutIn(BaseModel):
    start_time: float = Field(ge=0)
    end_time: float = Field(ge=0)


class CutsIn(BaseModel):
    cuts: list[CutIn]


class CutOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    start_time: float
    end_time: float


class ExportCreate(BaseModel):
    apply_cuts: bool = True
    enhance: bool = True  # 음량 맞추기 · 잡음 제거
    ai_denoise: bool = False  # AI 잡음 제거 (RNNoise)
    intro_id: uuid.UUID | None = None


class ExportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    options: dict
    duration: float | None
    file_size: int | None
    error_message: str | None
    created_at: datetime


class DownloadOut(BaseModel):
    url: str


class IntroCreate(BaseModel):
    prompt: str = Field(min_length=3, max_length=1000)
    seconds: int = Field(default=8, ge=3, le=30)


class IntroOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    prompt: str
    provider: str
    duration: float | None
    error_message: str | None
    created_at: datetime
    preview_url: str | None = None


class IntroPrompt(BaseModel):
    prompt: str
    provider: str
