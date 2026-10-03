from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ActionStatus, Priority, RiskLevel


class ActionItem(Base):
    __tablename__ = "action_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    assigned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    description: Mapped[str | None] = mapped_column(Text)
    workflow_status: Mapped[str | None] = mapped_column(String(30), index=True)
    progress_percent: Mapped[int | None] = mapped_column(Integer)
    progress_updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    progress_content: Mapped[str | None] = mapped_column(Text)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    meeting_id: Mapped[int | None] = mapped_column(ForeignKey("meetings.id", ondelete="SET NULL"), index=True)
    task: Mapped[str] = mapped_column(Text, nullable=False)
    assignee: Mapped[str | None] = mapped_column(String(120), index=True)
    due_date: Mapped[date | None] = mapped_column(Date, index=True)
    status: Mapped[ActionStatus] = mapped_column(String(20), default=ActionStatus.todo, index=True)
    priority: Mapped[Priority] = mapped_column(String(20), default=Priority.medium)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    risk_level: Mapped[RiskLevel] = mapped_column(String(20), default=RiskLevel.low, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status_changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)

    project = relationship("Project", back_populates="action_items")
    meeting = relationship("Meeting", back_populates="action_items")
    predictions = relationship("ActionItemPrediction", back_populates="action_item", cascade="all, delete-orphan")


class ActionItemPrediction(Base):
    __tablename__ = "action_item_predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    action_item_id: Mapped[int] = mapped_column(ForeignKey("action_items.id", ondelete="CASCADE"), index=True)
    delay_probability: Mapped[float] = mapped_column(Float, default=0)
    risk_level: Mapped[RiskLevel] = mapped_column(String(20), default=RiskLevel.low)
    model_version: Mapped[str] = mapped_column(String(50), default="rule-v1")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    action_item = relationship("ActionItem", back_populates="predictions")
