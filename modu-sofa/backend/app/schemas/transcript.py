import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.speaker import SpeakerOut


class SegmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    speaker_id: uuid.UUID
    seq: int
    start_time: float
    end_time: float
    original_text: str
    edited_text: str | None
    is_deleted: bool


class SegmentUpdate(BaseModel):
    edited_text: str | None = Field(default=None, max_length=5000)
    speaker_id: uuid.UUID | None = None


class TranscriptOut(BaseModel):
    segments: list[SegmentOut]
    speakers: list[SpeakerOut]
    edited_count: int
    deleted_count: int
    named_speaker_count: int
    merge_count: int
