from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import AnalysisStatus, NotionSyncStatus


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(250), nullable=False, index=True)
    meeting_date: Mapped[date] = mapped_column(Date, nullable=False)
    participants: Mapped[list[str]] = mapped_column(JSON, default=list)
    summary: Mapped[str | None] = mapped_column(Text)
    discussion: Mapped[str | None] = mapped_column(Text)
    undecided_topics: Mapped[list[str]] = mapped_column(JSON, default=list)
    analysis_status: Mapped[AnalysisStatus] = mapped_column(String(20), default=AnalysisStatus.draft)
    notion_sync_status: Mapped[NotionSyncStatus] = mapped_column(String(20), default=NotionSyncStatus.not_synced)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="meetings")
    transcript = relationship("Transcript", back_populates="meeting", uselist=False, cascade="all, delete-orphan")
    decisions = relationship("Decision", back_populates="meeting", cascade="all, delete-orphan")
    action_items = relationship("ActionItem", back_populates="meeting", cascade="all, delete-orphan")

