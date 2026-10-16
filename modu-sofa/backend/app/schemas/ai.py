import uuid

from pydantic import BaseModel, ConfigDict, Field


class ChapterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    start_segment_id: uuid.UUID
    start_time: float
    title: str
    description: str | None
    seq: int


class HighlightOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    start_segment_id: uuid.UUID
    end_segment_id: uuid.UUID
    start_time: float
    end_time: float
    title: str
    text: str
    seq: int


class AiOut(BaseModel):
    ai_status: str
    error_message: str | None
    summary: str | None = None
    keywords: list[str] = []
    title_candidates: list[str] = []
    model: str | None = None
    chapters: list[ChapterOut] = []
    highlights: list[HighlightOut] = []


class TitleSelect(BaseModel):
    title: str = Field(min_length=1, max_length=200)
