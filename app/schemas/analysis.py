from pydantic import BaseModel, Field


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
