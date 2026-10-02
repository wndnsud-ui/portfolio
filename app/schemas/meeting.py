from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AnalysisStatus, NotionSyncStatus


class MeetingCreate(BaseModel):
    project_id: int
    title: str
    meeting_date: date
    participants: list[str] = Field(default_factory=list)
    speaker_names: dict[str, str] = Field(default_factory=dict)
    transcript: str


class MeetingUpdate(BaseModel):
    title: str | None = None
    meeting_date: date | None = None
    participants: list[str] | None = None
    speaker_names: dict[str, str] | None = None
    transcript: str | None = None
    summary: str | None = None
    discussion: str | None = None
    undecided_topics: list[str] | None = None
    analysis_status: AnalysisStatus | None = None


class MeetingRead(BaseModel):
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
