from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import DecisionStatus


class DecisionCreate(BaseModel):
    project_id: int
    meeting_id: int | None = None
    topic: str
    value: str
    status: DecisionStatus = DecisionStatus.draft


class DecisionUpdate(BaseModel):
    meeting_id: int | None = None
    topic: str | None = None
    value: str | None = None
    status: DecisionStatus | None = None


class DecisionRead(BaseModel):
    id: int
    project_id: int
    meeting_id: int | None
    topic: str
    value: str
    status: DecisionStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

