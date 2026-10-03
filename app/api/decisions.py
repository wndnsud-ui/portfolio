from app.models.project import Project
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.services.permissions import visible_projects, require_project_manager, workspace_role
from app.api.deps import get_current_user
from app.api.meetings import get_meeting_or_404
from app.api.projects import get_project_or_404
from app.core.exceptions import AppError
from app.db.session import get_db
from app.models.decision import Decision, DecisionHistory
from app.models.user import User
from app.schemas.decision import DecisionCreate, DecisionHistoryRead, DecisionRead, DecisionUpdate

router = APIRouter(tags=["Decisions"])


def get_decision_or_404(db: Session, decision_id: int, user: User | None = None) -> Decision:
    query = db.query(Decision).filter(Decision.id == decision_id)
    if user:
        query = query.filter(Decision.project_id.in_(visible_projects(db, user.id)))
    decision = query.first()
    if not decision:
        raise AppError("DECISION_NOT_FOUND", "Decision not found.", 404)
    return decision


@router.post("/decisions", response_model=DecisionRead)
async def create_decision(payload: DecisionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Decision:
    require_project_manager(db, get_project_or_404(db, payload.project_id, current_user), current_user.id)
    if payload.meeting_id:
        meeting = get_meeting_or_404(db, payload.meeting_id, current_user)
        if meeting.project_id != payload.project_id:
            raise AppError("INVALID_MEETING", "Meeting must belong to selected project.", 400)
        if payload.status == "confirmed" and meeting.report_status not in {"APPROVED", "PUBLISHED"}:
            raise AppError("APPROVAL_REQUIRED", "Approve the meeting first.", 409)
    decision = Decision(**payload.model_dump(), user_id=current_user.id)
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return decision


@router.get("/projects/{project_id}/decisions", response_model=list[DecisionRead])
async def list_project_decisions(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[Decision]:
    get_project_or_404(db, project_id, current_user)
    return db.query(Decision).filter(Decision.project_id == project_id).order_by(Decision.updated_at.desc()).all()


@router.get("/decisions/{decision_id}", response_model=DecisionRead)
async def read_decision(decision_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Decision:
    return get_decision_or_404(db, decision_id, current_user)


@router.get("/decisions/{decision_id}/history", response_model=list[DecisionHistoryRead])
async def read_decision_history(
    decision_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DecisionHistory]:
    get_decision_or_404(db, decision_id, current_user)
    return (
        db.query(DecisionHistory)
        .filter(DecisionHistory.decision_id == decision_id)
        .order_by(DecisionHistory.changed_at.desc())
        .all()
    )


@router.patch("/decisions/{decision_id}", response_model=DecisionRead)
async def update_decision(decision_id: int, payload: DecisionUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Decision:
    decision = get_decision_or_404(db, decision_id, current_user)
    require_project_manager(db, db.get(Project, decision.project_id), current_user.id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("meeting_id"):
        meeting = get_meeting_or_404(db, data["meeting_id"], current_user)
        if meeting.project_id != decision.project_id:
            raise AppError("INVALID_MEETING", "Meeting must belong to decision project.", 400)
    if data.get("status") == "confirmed" and (data.get("meeting_id") or decision.meeting_id):
        meeting = get_meeting_or_404(db, data.get("meeting_id") or decision.meeting_id, current_user)
        if meeting.report_status not in {"APPROVED", "PUBLISHED"}:
            raise AppError("APPROVAL_REQUIRED", "Approve the meeting first.", 409)
    if ("value" in data and data["value"] != decision.value) or ("status" in data and data["status"] != decision.status):
        db.add(DecisionHistory(decision_id=decision.id, meeting_id=data.get("meeting_id", decision.meeting_id), previous_value=decision.value, new_value=data.get("value", decision.value)))
    for key, value in data.items():
        setattr(decision, key, value)
    db.commit()
    db.refresh(decision)
    return decision


@router.delete("/decisions/{decision_id}", status_code=204)
async def delete_decision(decision_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> None:
    decision = get_decision_or_404(db, decision_id, current_user)
    require_project_manager(db, db.get(Project, decision.project_id), current_user.id)
    db.delete(decision)
    db.commit()
