import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import Timestamps, UuidPk


class TranscriptSegment(UuidPk, Timestamps, Base):
    __tablename__ = "transcript_segments"
    __table_args__ = (
        Index("ix_segments_episode_seq", "episode_id", "seq"),
        Index("ix_segments_episode_start", "episode_id", "start_time"),
    )

    episode_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("episodes.id", ondelete="CASCADE"))
    speaker_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("episode_speakers.id"))
    seq: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[float] = mapped_column(Float)
    end_time: Mapped[float] = mapped_column(Float)
    original_text: Mapped[str] = mapped_column(Text)  # STT 결과. 절대 수정하지 않는다.
    edited_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    @property
    def text(self) -> str:
        return self.edited_text if self.edited_text is not None else self.original_text
