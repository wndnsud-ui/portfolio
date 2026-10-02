from datetime import date

from pydantic import BaseModel, Field

from app.models.enums import Priority


class DecisionCandidate(BaseModel):
    topic: str
    value: str
    evidence: str
    confidence: float = Field(ge=0, le=1)


class DecisionCandidateResult(BaseModel):
    meeting_id: int
    candidates: list[DecisionCandidate]


class DecisionConfirmItem(BaseModel):
    topic: str = Field(min_length=1, max_length=250)
    value: str = Field(min_length=1)


class DecisionConfirmRequest(BaseModel):
    decisions: list[DecisionConfirmItem]


class SpeakerAnalysisRequest(BaseModel):
    speaker_names: dict[str, str] = Field(default_factory=dict)


class SpeakerIssue(BaseModel):
    speaker: str
    points: list[str]
    stance: str


class ActionItemCandidate(BaseModel):
    task: str
    assignee: str | None = None
    due_date: date | None = None
    priority: Priority = Priority.medium
    evidence: str
    confidence: float = Field(ge=0, le=1)


class SpeakerAnalysisResult(BaseModel):
    meeting_id: int
    summary: str
    issues: list[str]
    speakers: list[SpeakerIssue]
    action_items: list[ActionItemCandidate]


class ActionItemConfirmItem(BaseModel):
    task: str = Field(min_length=1)
    assignee: str | None = None
    due_date: date | None = None
    priority: Priority = Priority.medium


class ActionItemConfirmRequest(BaseModel):
    action_items: list[ActionItemConfirmItem]
