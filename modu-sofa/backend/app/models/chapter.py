import uuid

from sqlalchemy import Float, ForeignKey, Integer, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import UuidPk


class Chapter(UuidPk, Base):
    __tablename__ = "chapters"

    episode_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("episodes.id", ondelete="CASCADE"), index=True)
    start_segment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("transcript_segments.id", ondelete="CASCADE")
    )
    start_time: Mapped[float] = mapped_column(Float)  # Backend가 Segment에서 복사
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    seq: Mapped[int] = mapped_column(Integer)
