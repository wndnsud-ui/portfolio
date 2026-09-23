from __future__ import annotations

from pydantic import BaseModel, Field


class Segment(BaseModel):
    start: float
    end: float
    text: str


class Transcript(BaseModel):
    source_name: str
    duration: float | None = None
    segments: list[Segment] = Field(default_factory=list)


class Candidate(BaseModel):
    id: str = ""
    title: str
    summary: str = ""
    listener_question: str
    reason: str
    start: float
    end: float
    transcript: str
    usage_type: str
    review_notes: str = ""
    status: str = "hold"


class RecordingState(BaseModel):
    recording_id: str
    source_name: str
    audio_path: str | None = None
    duration: float | None = None
    transcript_path: str | None = None
    candidates_path: str | None = None
