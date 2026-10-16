import uuid

from sqlalchemy import Float, ForeignKey, Integer, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import UuidPk


class Highlight(UuidPk, Base):
    __tablename__ = "highlights"

    episode_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("episodes.id", ondelete="CASCADE"), index=True)
    start_segment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("transcript_segments.id", ondelete="CASCADE")
    )
    end_segment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("transcript_segments.id", ondelete="CASCADE")
    )
    start_time: Mapped[float] = mapped_column(Float)  # start_segment.start_time
    end_time: Mapped[float] = mapped_column(Float)  # end_segment.end_time
    title: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)  # Backend가 구간 Segment 텍스트를 이어 붙여 생성
    seq: Mapped[int] = mapped_column(Integer)
