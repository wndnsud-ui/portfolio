from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import AnalysisStatus, NotionSyncStatus


class MeetingCreate(BaseModel):
    recorder_id: int | None = None
    input_type: Literal["audio", "recording", "text_file", "text_paste"] = "text_paste"
    project_id: int
    title: str
    meeting_date: date
    participants: list[str] = Field(default_factory=list)
    speaker_names: dict[str, str] = Field(default_factory=dict)
    transcript: str = ""


class MeetingUpdate(BaseModel):
    recorder_id: int | None = None
    candidates: dict | None = None
    title: str | None = None
    meeting_date: date | None = None
    participants: list[str] | None = None
    speaker_names: dict[str, str] | None = None
    transcript: str | None = None
    summary: str | None = None
    discussion: str | None = None
    undecided_topics: list[str] | None = None
    analysis_status: AnalysisStatus | None = None

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        for name in self.model_fields_set & {"title", "meeting_date", "participants", "speaker_names", "undecided_topics", "analysis_status", "candidates"}:
            if getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class MeetingRead(BaseModel):
    recorder_id: int | None = None
    report_status: str = "DRAFT"
    input_type: str = "text_paste"
    candidates: dict = Field(default_factory=dict)
    id: int
    project_id: int
    title: str
    meeting_date: date
    participants: list[str]
    speaker_names: dict[str, str] = Field(default_factory=dict)
    summary: str | None
    discussion: str | None
    undecided_topics: list[str] = Field(default_factory=list)
    analysis_status: AnalysisStatus
    notion_sync_status: NotionSyncStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MeetingDetail(MeetingRead):
    transcript: str | None = None
