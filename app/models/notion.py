from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import NotionSyncStatus


class NotionConnection(Base):
    __tablename__ = "notion_connections"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_name: Mapped[str | None] = mapped_column(String(200))
    meeting_database_id: Mapped[str | None] = mapped_column(String(120))
    action_item_database_id: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class NotionSyncLog(Base):
    __tablename__ = "notion_sync_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"), index=True)
    status: Mapped[NotionSyncStatus] = mapped_column(String(20), default=NotionSyncStatus.not_synced)
    notion_page_id: Mapped[str | None] = mapped_column(String(120))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

