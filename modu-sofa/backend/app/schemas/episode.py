import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EpisodeCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    description: str | None = None


class EpisodeUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    description: str | None = None


class EpisodeCounts(BaseModel):
    speakers: int = 0
    chapters: int = 0
    highlights: int = 0


class EpisodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None
    description: str | None
    original_filename: str | None
    duration: float | None
    file_size: int | None
    status: str
    ai_status: str
    error_stage: str | None
    error_message: str | None
    progress_current: int
    progress_total: int
    stt_model: str | None = None
    status_updated_at: datetime
    created_at: datetime
    updated_at: datetime
    counts: EpisodeCounts | None = None


class EpisodeDetail(EpisodeOut):
    playback_url: str | None = None
    peaks_url: str | None = None
    stt_chunk_sec: int = 1200
    stt_overlap_sec: int = 15


class JobAccepted(BaseModel):
    episode_id: uuid.UUID
    status: str
    ai_status: str | None = None


class UploadUrlRequest(BaseModel):
    filename: str
    size: int
    content_type: str | None = None


class UploadUrlResponse(BaseModel):
    upload_url: str
    method: str
    headers: dict[str, str]
    path: str
