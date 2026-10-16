import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import JsonType, Timestamps, UuidPk


class EpisodeSpeaker(UuidPk, Timestamps, Base):
    __tablename__ = "episode_speakers"
    __table_args__ = (UniqueConstraint("episode_id", "speaker_code", name="uq_episode_speaker_code"),)

    episode_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("episodes.id", ondelete="CASCADE"), index=True)
    speaker_code: Mapped[str] = mapped_column(String(32))
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[str] = mapped_column(String(16))


class SpeakerMerge(UuidPk, Timestamps, Base):
    """병합 되돌리기를 위해 옮긴 Segment ID 목록과 삭제된 화자 정보를 보관한다."""

    __tablename__ = "speaker_merges"

    episode_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("episodes.id", ondelete="CASCADE"), index=True)
    from_speaker_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    from_speaker_code: Mapped[str] = mapped_column(String(32))
    from_display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    from_color: Mapped[str] = mapped_column(String(16))
    into_speaker_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    segment_ids: Mapped[list] = mapped_column(JsonType)
