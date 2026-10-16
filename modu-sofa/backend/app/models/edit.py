"""2차 기능: 음성 자르기 · 내보내기 · AI 시작음.

자르기는 비파괴 편집이다. 원본/재생용 파일과 Segment 시간은 그대로 두고 잘라낼 구간만 저장한다.
내보낼 때만 실제로 잘라 새 파일을 만든다 → 대본 ↔ 오디오 동기화(8장)가 깨지지 않는다.
"""

import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import JsonType, Timestamps, UuidPk


class AudioCut(UuidPk, Timestamps, Base):
    __tablename__ = "audio_cuts"

    episode_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("episodes.id", ondelete="CASCADE"), index=True)
    start_time: Mapped[float] = mapped_column(Float)  # 재생용 파일 기준 초
    end_time: Mapped[float] = mapped_column(Float)


class ExportStatus:
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ExportJob(UuidPk, Timestamps, Base):
    __tablename__ = "exports"

    episode_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("episodes.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(16), default=ExportStatus.RUNNING)
    options: Mapped[dict] = mapped_column(JsonType)  # {apply_cuts, enhance, ai_denoise, intro_id}
    output_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class IntroStatus:
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class IntroClip(UuidPk, Timestamps, Base):
    """AI가 만든 시작음. 사용자 단위로 보관해 다른 에피소드에서도 다시 쓸 수 있다."""

    __tablename__ = "intro_clips"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    status: Mapped[str] = mapped_column(String(16), default=IntroStatus.RUNNING)
    prompt: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(32))
    path: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
