from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.projects import get_project_or_404
from app.api.deps import get_current_user
from app.core.exceptions import AppError
from app.db.session import get_db
from app.models.action_item import ActionItem
from app.models.decision import Decision
from app.models.enums import ActionStatus, DecisionStatus, NotionSyncStatus
from app.models.meeting import Meeting
from app.models.transcript import Transcript
from app.models.user import User
from app.schemas.action_item import ActionItemRead
from app.schemas.analysis import ActionItemConfirmRequest, DecisionCandidateResult, DecisionConfirmRequest, SpeakerAnalysisRequest, SpeakerAnalysisResult
from app.schemas.decision import DecisionRead
from app.schemas.meeting import MeetingCreate, MeetingDetail, MeetingRead, MeetingUpdate
from app.services.ai_service import ai_service
from app.services.risk_service import risk_service

router = APIRouter(prefix="/meetings", tags=["Meetings"])


def get_meeting_or_404(db: Session, meeting_id: int, user: User | None = None) -> Meeting:
    query = db.query(Meeting).filter(Meeting.id == meeting_id)
    if user:
        query = query.filter(Meeting.user_id == user.id)
    meeting = query.first()
    if not meeting:
        raise AppError("INVALID_MEETING", "Meeting not found.", 404)
    return meeting


def to_detail(meeting: Meeting) -> MeetingDetail:
    return MeetingDetail(
        **MeetingRead.model_validate(meeting).model_dump(),
        transcript=meeting.transcript.content if meeting.transcript else None,
    )


@router.post("", response_model=MeetingDetail)
async def create_meeting(payload: MeetingCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> MeetingDetail:
    get_project_or_404(db, payload.project_id, current_user)
    meeting = Meeting(**payload.model_dump(exclude={"transcript"}), user_id=current_user.id)
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
    current_user: User = Depends(get_current_user),
) -> list[Meeting]:
    query = db.query(Meeting).filter(Meeting.user_id == current_user.id)
    if project_id:
        query = query.filter(Meeting.project_id == project_id)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Meeting.title.ilike(pattern),
                Meeting.summary.ilike(pattern),
                Meeting.discussion.ilike(pattern),
                Meeting.transcript.has(Transcript.content.ilike(pattern)),
                Meeting.decisions.any(or_(Decision.topic.ilike(pattern), Decision.value.ilike(pattern))),
                Meeting.action_items.any(or_(ActionItem.task.ilike(pattern), ActionItem.assignee.ilike(pattern))),
            )
        )
    return query.order_by(Meeting.meeting_date.desc(), Meeting.created_at.desc()).all()


@router.get("/{meeting_id}", response_model=MeetingDetail)
async def read_meeting(meeting_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> MeetingDetail:
    return to_detail(get_meeting_or_404(db, meeting_id, current_user))


@router.patch("/{meeting_id}", response_model=MeetingDetail)
async def update_meeting(meeting_id: int, payload: MeetingUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> MeetingDetail:
    meeting = get_meeting_or_404(db, meeting_id, current_user)
    data = payload.model_dump(exclude_unset=True)
    transcript = data.pop("transcript", None)
    for key, value in data.items():
        setattr(meeting, key, value)
    if transcript is not None:
        if meeting.transcript:
            meeting.transcript.content = transcript
        else:
            meeting.transcript = Transcript(content=transcript)
    if data or transcript is not None:
        if meeting.notion_sync_status == NotionSyncStatus.synced:
            meeting.notion_sync_status = NotionSyncStatus.outdated
    db.commit()
    db.refresh(meeting)
    return to_detail(meeting)


@router.delete("/{meeting_id}", status_code=204)
async def delete_meeting(meeting_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> None:
    meeting = get_meeting_or_404(db, meeting_id, current_user)
    db.delete(meeting)
    db.commit()


@router.post("/{meeting_id}/analyze")
async def analyze_meeting(meeting_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    meeting = to_detail(get_meeting_or_404(db, meeting_id, current_user))
    return await ai_service.analyze_meeting(meeting)


@router.post("/{meeting_id}/summarize", response_model=MeetingDetail)
async def summarize_meeting(meeting_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> MeetingDetail:
    meeting = get_meeting_or_404(db, meeting_id, current_user)
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


@router.post("/{meeting_id}/speaker-analysis", response_model=SpeakerAnalysisResult)
async def analyze_meeting_speakers(
    meeting_id: int,
    payload: SpeakerAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SpeakerAnalysisResult:
    meeting = get_meeting_or_404(db, meeting_id, current_user)
    transcript = meeting.transcript.content.strip() if meeting.transcript else ""
    cleaned_names = {key.strip(): value.strip() for key, value in payload.speaker_names.items() if key.strip() and value.strip()}
    meeting.speaker_names = cleaned_names
    result = await ai_service.analyze_speakers(transcript, cleaned_names)
    db.commit()
    return result.model_copy(update={"meeting_id": meeting.id})


@router.post("/{meeting_id}/action-items/confirm", response_model=list[ActionItemRead])
async def confirm_action_items(
    meeting_id: int,
    payload: ActionItemConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ActionItem]:
    meeting = get_meeting_or_404(db, meeting_id, current_user)
    saved: list[ActionItem] = []
    for candidate in payload.action_items:
        item = ActionItem(
            user_id=current_user.id,
            project_id=meeting.project_id,
            meeting_id=meeting.id,
            task=candidate.task.strip(),
            assignee=candidate.assignee.strip() if candidate.assignee else None,
            due_date=candidate.due_date,
            status=ActionStatus.todo,
            priority=candidate.priority,
        )
        item.risk_score, item.risk_level = risk_service.score(item)
        db.add(item)
        saved.append(item)
    db.commit()
    for item in saved:
        db.refresh(item)
    return saved


@router.post("/{meeting_id}/decision-candidates", response_model=DecisionCandidateResult)
async def extract_decision_candidates(
    meeting_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> DecisionCandidateResult:
    meeting = get_meeting_or_404(db, meeting_id, current_user)
    transcript = meeting.transcript.content.strip() if meeting.transcript else ""
    if not transcript:
        raise AppError("TRANSCRIPT_REQUIRED", "A transcript is required for decision analysis.", 400)
    candidates = await ai_service.extract_decision_candidates(transcript)
    return DecisionCandidateResult(meeting_id=meeting.id, candidates=candidates)


@router.post("/{meeting_id}/decisions/confirm", response_model=list[DecisionRead])
async def confirm_decisions(
    meeting_id: int, payload: DecisionConfirmRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[Decision]:
    meeting = get_meeting_or_404(db, meeting_id, current_user)
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
            user_id=current_user.id,
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
