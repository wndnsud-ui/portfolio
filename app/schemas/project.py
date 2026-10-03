from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator


class ProjectCreate(BaseModel):
    workspace_id: int | None = None
    name: str
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None

    @model_validator(mode="after")
    def reject_null_name(self):
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name cannot be null")
        return self


class ProjectRead(BaseModel):
    workspace_id: int | None = None
    id: int
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

