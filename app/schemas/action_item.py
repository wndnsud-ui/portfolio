from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import ActionStatus, Priority, RiskLevel


class ActionItemCreate(BaseModel):
    project_id: int
    meeting_id: int | None = None
    task: str
    assignee: str | None = None
    due_date: date | None = None
    status: ActionStatus = ActionStatus.todo
    priority: Priority = Priority.medium


class ActionItemUpdate(BaseModel):
    meeting_id: int | None = None
    task: str | None = None
    assignee: str | None = None
    due_date: date | None = None
    status: ActionStatus | None = None
    priority: Priority | None = None


class ActionItemRead(BaseModel):
    id: int
    project_id: int
    meeting_id: int | None
    task: str
    assignee: str | None
    due_date: date | None
    status: ActionStatus
    priority: Priority
    risk_score: int
    risk_level: RiskLevel
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class RiskRead(BaseModel):
    action_item_id: int
    risk_score: int
    risk_level: RiskLevel


class PredictionRead(BaseModel):
    action_item_id: int
    delay_probability: float
    risk_level: RiskLevel
    model_version: str

