from app.models.project import Project
from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.projects import get_project_or_404
from app.services.permissions import visible_projects, require_project_manager, workspace_role, require_meeting_editor
from app.services.workflow_service import validate_project_user, activity
from app.api.deps import get_current_user
from app.core.exceptions import AppError
from app.db.session import get_db
from app.models.action_item import ActionItem
from app.models.decision import Decision
from app.models.enums import ActionStatus, DecisionStatus, NotionSyncStatus
from app.models.meeting import Meeting
from app.models.transcript import Transcript
from app.models.workflow import TranscriptionJob
from app.models.user import User
from app.schemas.action_item import ActionItemRead
from app.schemas.analysis import ActionItemConfirmRequest, DecisionCandidateResult, DecisionConfirmRequest, SpeakerAnalysisRequest, SpeakerAnalysisResult
from app.schemas.decision import DecisionRead
from app.schemas.meeting import MeetingCreate, MeetingDetail, MeetingRead, MeetingUpdate
from app.services.ai_service import ai_service
from app.services.risk_service import risk_service
from app.services.permissions import is_project_manager
from app.models.decision import DecisionHistory

router = APIRouter(prefix="/meetings", tags=["Meetings"])


def get_meeting_or_404(db: Session, meeting_id: int, user: User | None = None, lock: bool = False) -> Meeting:
    query = db.query(Meeting).filter(Meeting.id == meeting_id)
    if user:
        query = query.filter(Meeting.project_id.in_(visible_projects(db, user.id)))
    if lock:
        query = query.with_for_update()
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
    require_project_manager(db, get_project_or_404(db, payload.project_id, current_user), current_user.id)
    validate_project_user(db, payload.project_id, payload.recorder_id)
    meeting = Meeting(**payload.model_dump(exclude={"transcript"}), user_id=current_user.id)
    meeting.transcript = Transcript(content=payload.transcript)
    db.add(meeting)
    db.flush()
    activity(db, meeting.project_id, current_user.id, "meeting_created", "meeting", meeting.id)
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
    query = db.query(Meeting).filter(Meeting.project_id.in_(visible_projects(db, current_user.id)))
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
    meeting = get_meeting_or_404(db, meeting_id, current_user, lock=True)
    require_meeting_editor(db, meeting, current_user.id)
    if meeting.report_status in {"TRANSCRIBING", "APPROVED", "PUBLISHED"} or (meeting.report_status == "MANAGER_REVIEW" and not is_project_manager(db, meeting.project, current_user.id)):
        raise AppError("REVIEW_LOCKED", "Return meeting for changes before editing.", 409)
    data = payload.model_dump(exclude_unset=True)
    if data.get("analysis_status") == "confirmed":
        raise AppError("WORKFLOW_REQUIRED", "Use meeting approval to confirm the report.", 409)
    if db.query(TranscriptionJob).filter_by(meeting_id=meeting_id, status="ANALYZING").first():
        raise AppError("ANALYSIS_BUSY", "AI analysis is already running.", 409)
    if "recorder_id" in data:
        require_project_manager(db, db.get(Project, meeting.project_id), current_user.id)
        validate_project_user(db, meeting.project_id, data["recorder_id"])
    if meeting.report_status in {"AI_ANALYZED", "CHANGES_REQUESTED"} or (meeting.report_status == "DRAFT" and any(k in data for k in {"summary", "discussion", "candidates"})):
        meeting.report_status = "RECORDER_REVIEW"
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
    require_project_manager(db, db.get(Project, meeting.project_id), current_user.id)
    db.delete(meeting)
    db.commit()


@router.post("/{meeting_id}/analyze")
async def analyze_meeting(meeting_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> MeetingDetail:
    meeting = get_meeting_or_404(db, meeting_id, current_user, lock=True)
    require_meeting_editor(db, meeting, current_user.id)
    if meeting.report_status in {"TRANSCRIBING", "MANAGER_REVIEW", "APPROVED", "PUBLISHED"}:
        raise AppError("REVIEW_LOCKED", "Return meeting for changes before analysis.", 409)
    job = db.query(TranscriptionJob).filter_by(meeting_id=meeting_id).order_by(TranscriptionJob.id.desc()).first()
    if job and job.status == "ANALYZING":
        raise AppError("ANALYSIS_BUSY", "AI analysis is already running.", 409)
    if not job:
        job = TranscriptionJob(meeting_id=meeting_id, user_id=current_user.id)
        db.add(job)
    job.status, job.progress, job.error = "ANALYZING", 0, None
    db.commit()
    text = meeting.transcript.content if meeting.transcript else ""
    try:
        summary = await ai_service.summarize_meeting(text)
        speakers = await ai_service.analyze_speakers(text, meeting.speaker_names)
        decisions = await ai_service.extract_decision_candidates(text)
    except Exception:
        job.status, job.error = "FAILED", "AI 분석에 실패했습니다. 설정과 원문을 확인해 주세요."
        db.commit()
        raise
    meeting.summary = summary["summary"]
    meeting.discussion = "\n".join(summary["issues"])
    meeting.undecided_topics = summary["open_questions"]
    meeting.candidates = {"decisions": [d.model_dump(mode="json") for d in decisions],
        "action_items": [a.model_dump(mode="json") for a in speakers.action_items],
        "speaker_segments": [s.model_dump(mode="json") for s in speakers.speakers],
        "follow_up_topics": summary["open_questions"]}
    meeting.report_status = "AI_ANALYZED"
    job.status, job.progress = "REVIEW_READY", 100
    db.commit()
    return to_detail(meeting)


@router.post("/{meeting_id}/summarize", response_model=MeetingDetail)
async def summarize_meeting(meeting_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> MeetingDetail:
    meeting = get_meeting_or_404(db, meeting_id, current_user)
    require_meeting_editor(db, meeting, current_user.id)
    if meeting.report_status in {"MANAGER_REVIEW", "APPROVED", "PUBLISHED"}:
        raise AppError("REVIEW_LOCKED", "Return meeting for changes before editing.", 409)
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
    meeting.analysis_status = "draft"
    meeting.report_status = "AI_ANALYZED"
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
    require_meeting_editor(db, meeting, current_user.id)
    if meeting.report_status in {"MANAGER_REVIEW", "APPROVED", "PUBLISHED"}:
        raise AppError("REVIEW_LOCKED", "Return meeting for changes before editing.", 409)
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
    require_project_manager(db, db.get(Project, meeting.project_id), current_user.id)
    if meeting.report_status not in {"APPROVED", "PUBLISHED"}:
        raise AppError("APPROVAL_REQUIRED", "Approve the meeting before confirming tasks.", 409)
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
    require_meeting_editor(db, meeting, current_user.id)
    if meeting.report_status in {"MANAGER_REVIEW", "APPROVED", "PUBLISHED"}:
        raise AppError("REVIEW_LOCKED", "Return meeting for changes before editing.", 409)
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
    require_project_manager(db, db.get(Project, meeting.project_id), current_user.id)
    if meeting.report_status not in {"APPROVED", "PUBLISHED"}:
        raise AppError("APPROVAL_REQUIRED", "Approve the meeting before confirming decisions.", 409)
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
        db.flush()
        db.add(DecisionHistory(decision_id=decision.id, meeting_id=meeting.id, new_value=value))
        saved.append(decision)
    db.commit()
    for decision in saved:
        db.refresh(decision)
    return saved
