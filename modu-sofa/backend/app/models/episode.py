import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import Timestamps, UuidPk, utcnow


class EpisodeStatus:
    CREATED = "created"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    TRANSCRIBING = "transcribing"
    TRANSCRIBED = "transcribed"
    FAILED = "failed"


class AiStatus:
    NONE = "none"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ErrorStage:
    UPLOAD = "upload"
    PROCESSING = "processing"
    TRANSCRIPTION = "transcription"
    AI = "ai"


class Episode(UuidPk, Timestamps, Base):
    __tablename__ = "episodes"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    playback_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    peaks_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=EpisodeStatus.CREATED)
    ai_status: Mapped[str] = mapped_column(String(32), default=AiStatus.NONE)
    error_stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    stt_model: Mapped[str | None] = mapped_column(String(64), nullable=True)  # "mock" 또는 실제 STT 모델명
    progress_current: Mapped[int] = mapped_column(Integer, default=0)
    progress_total: Mapped[int] = mapped_column(Integer, default=0)
    status_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
