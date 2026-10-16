import uuid

from sqlalchemy import ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import JsonType, Timestamps, UuidPk


class AiResult(UuidPk, Timestamps, Base):
    __tablename__ = "ai_results"

    episode_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("episodes.id", ondelete="CASCADE"), unique=True
    )
    summary: Mapped[str] = mapped_column(Text)
    keywords: Mapped[list] = mapped_column(JsonType)
    title_candidates: Mapped[list] = mapped_column(JsonType)
    model: Mapped[str] = mapped_column(Text)
