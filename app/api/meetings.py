from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.projects import get_project_or_404
from app.core.exceptions import AppError
from app.db.session import get_db
from app.models.decision import Decision
from app.models.enums import DecisionStatus
from app.models.meeting import Meeting
from app.models.transcript import Transcript
from app.schemas.analysis import DecisionCandidateResult, DecisionConfirmRequest
from app.schemas.decision import DecisionRead
from app.schemas.meeting import MeetingCreate, MeetingDetail, MeetingRead, MeetingUpdate
from app.services.ai_service import ai_service

router = APIRouter(prefix="/meetings", tags=["Meetings"])


def get_meeting_or_404(db: Session, meeting_id: int) -> Meeting:
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise AppError("INVALID_MEETING", "Meeting not found.", 404)
    return meeting


def to_detail(meeting: Meeting) -> MeetingDetail:
    return MeetingDetail(
        **MeetingRead.model_validate(meeting).model_dump(),
        transcript=meeting.transcript.content if meeting.transcript else None,
    )


@router.post("", response_model=MeetingDetail)
async def create_meeting(payload: MeetingCreate, db: Session = Depends(get_db)) -> MeetingDetail:
    get_project_or_404(db, payload.project_id)
    meeting = Meeting(**payload.model_dump(exclude={"transcript"}))
    meeting.transcript = Transcript(content=payload.transcript)
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return to_detail(meeting)


@router.get("", response_model=list[MeetingRead])
async def list_meetings(
    project_id: int | None = None,
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[Meeting]:
    query = db.query(Meeting)
    if project_id:
        query = query.filter(Meeting.project_id == project_id)
    if q:
        query = query.outerjoin(Transcript).filter(
            or_(Meeting.title.ilike(f"%{q}%"), Meeting.summary.ilike(f"%{q}%"), Transcript.content.ilike(f"%{q}%"))
        )
    return query.order_by(Meeting.meeting_date.desc(), Meeting.created_at.desc()).all()


@router.get("/{meeting_id}", response_model=MeetingDetail)
async def read_meeting(meeting_id: int, db: Session = Depends(get_db)) -> MeetingDetail:
    return to_detail(get_meeting_or_404(db, meeting_id))


@router.patch("/{meeting_id}", response_model=MeetingDetail)
async def update_meeting(meeting_id: int, payload: MeetingUpdate, db: Session = Depends(get_db)) -> MeetingDetail:
    meeting = get_meeting_or_404(db, meeting_id)
    data = payload.model_dump(exclude_unset=True)
    transcript = data.pop("transcript", None)
    for key, value in data.items():
        setattr(meeting, key, value)
    if transcript is not None:
        if meeting.transcript:
            meeting.transcript.content = transcript
        else:
            meeting.transcript = Transcript(content=transcript)
    db.commit()
    db.refresh(meeting)
    return to_detail(meeting)


@router.delete("/{meeting_id}", status_code=204)
async def delete_meeting(meeting_id: int, db: Session = Depends(get_db)) -> None:
    meeting = get_meeting_or_404(db, meeting_id)
    db.delete(meeting)
    db.commit()


@router.post("/{meeting_id}/analyze")
async def analyze_meeting(meeting_id: int, db: Session = Depends(get_db)) -> dict:
    meeting = to_detail(get_meeting_or_404(db, meeting_id))
    return await ai_service.analyze_meeting(meeting)


@router.post("/{meeting_id}/summarize", response_model=MeetingDetail)
async def summarize_meeting(meeting_id: int, db: Session = Depends(get_db)) -> MeetingDetail:
    meeting = get_meeting_or_404(db, meeting_id)
    transcript = meeting.transcript.content.strip() if meeting.transcript else ""
    result = await ai_service.summarize_meeting(transcript)
    meeting.summary = result["summary"]
    sections = []
    for title, key in (("핵심 쟁점", "issues"), ("결정사항", "decisions"), ("후속 액션", "action_items")):
        values = result[key]
        if values:
            sections.append(f"## {title}\n" + "\n".join(f"- {value}" for value in values))
    meeting.discussion = "\n\n".join(sections)
    meeting.undecided_topics = result["open_questions"]
    meeting.analysis_status = "confirmed"
    db.commit()
    db.refresh(meeting)
    return to_detail(meeting)


@router.post("/{meeting_id}/decision-candidates", response_model=DecisionCandidateResult)
async def extract_decision_candidates(
    meeting_id: int, db: Session = Depends(get_db)
) -> DecisionCandidateResult:
    meeting = get_meeting_or_404(db, meeting_id)
    transcript = meeting.transcript.content.strip() if meeting.transcript else ""
    if not transcript:
        raise AppError("TRANSCRIPT_REQUIRED", "A transcript is required for decision analysis.", 400)
    candidates = await ai_service.extract_decision_candidates(transcript)
    return DecisionCandidateResult(meeting_id=meeting.id, candidates=candidates)


@router.post("/{meeting_id}/decisions/confirm", response_model=list[DecisionRead])
async def confirm_decisions(
    meeting_id: int, payload: DecisionConfirmRequest, db: Session = Depends(get_db)
) -> list[Decision]:
    meeting = get_meeting_or_404(db, meeting_id)
    saved: list[Decision] = []
    for item in payload.decisions:
        topic = item.topic.strip()
        value = item.value.strip()
        if not topic or not value:
            raise AppError("INVALID_DECISION", "Decision topic and value are required.", 400)
        existing = (
            db.query(Decision)
            .filter(
                Decision.meeting_id == meeting.id,
                Decision.topic == topic,
                Decision.value == value,
            )
            .first()
        )
        if existing:
            saved.append(existing)
            continue
        decision = Decision(
            project_id=meeting.project_id,
            meeting_id=meeting.id,
            topic=topic,
            value=value,
            status=DecisionStatus.confirmed,
        )
        db.add(decision)
        saved.append(decision)
    db.commit()
    for decision in saved:
        db.refresh(decision)
    return saved
