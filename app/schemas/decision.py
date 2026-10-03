from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator

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

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        for name in self.model_fields_set & {"topic", "value", "status"}:
            if getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


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


class DecisionHistoryRead(BaseModel):
    id: int
    decision_id: int
    meeting_id: int | None
    previous_value: str | None
    new_value: str
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)
