from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.enums import ActionStatus, Priority, RiskLevel


class ActionItemCreate(BaseModel):
    assignee_id: int | None = None
    description: str | None = None
    project_id: int
    meeting_id: int | None = None
    task: str
    assignee: str | None = None
    due_date: date | None = None
    status: ActionStatus = ActionStatus.todo
    priority: Priority = Priority.medium


class ActionItemUpdate(BaseModel):
    assignee_id: int | None = None
    description: str | None = None
    meeting_id: int | None = None
    task: str | None = None
    assignee: str | None = None
    due_date: date | None = None
    status: ActionStatus | None = None
    priority: Priority | None = None

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        for name in self.model_fields_set & {"task", "status", "priority"}:
            if getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class ActionItemRead(BaseModel):
    progress_percent: int | None = None
    progress_updated_at: datetime | None = None
    progress_content: str | None = None
    assignee_id: int | None = None
    assigned_by: int | None = None
    description: str | None = None
    workflow_status: str | None = None
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

