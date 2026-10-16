import uuid

from pydantic import BaseModel, ConfigDict, Field


class SpeakerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    speaker_code: str
    display_name: str | None
    color: str
    segment_count: int = 0
    share: float = 0.0
    sample_start: float | None = None
    sample_end: float | None = None
    first_start: float | None = None
    suspect: bool = False  # 자동 분석에서 둘로 나뉘었을 가능성이 있는 화자


class SpeakerUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=40)
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")


class SpeakerMergeRequest(BaseModel):
    from_id: uuid.UUID
    into_id: uuid.UUID


class LastMergeOut(BaseModel):
    from_speaker_code: str
    from_display_name: str | None
    into_speaker_id: uuid.UUID
    segment_count: int


class SpeakersOut(BaseModel):
    speakers: list[SpeakerOut]
    last_merge: LastMergeOut | None
