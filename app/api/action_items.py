from datetime import date, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.meetings import get_meeting_or_404
from app.api.projects import get_project_or_404
from app.core.exceptions import AppError
from app.db.session import get_db
from app.models.action_item import ActionItem
from app.models.enums import ActionStatus, RiskLevel
from app.models.user import User
from app.schemas.action_item import ActionItemCreate, ActionItemRead, ActionItemUpdate
from app.services.risk_service import risk_service

router = APIRouter(prefix="/action-items", tags=["Action Items"])


def get_action_item_or_404(db: Session, action_item_id: int, user: User | None = None) -> ActionItem:
    query = db.query(ActionItem).filter(ActionItem.id == action_item_id)
    if user:
        query = query.filter(ActionItem.user_id == user.id)
    item = query.first()
    if not item:
        raise AppError("ACTION_ITEM_NOT_FOUND", "Action item not found.", 404)
    return item


def apply_risk(item: ActionItem) -> None:
    score, level = risk_service.score(item)
    item.risk_score = score
    item.risk_level = level


@router.post("", response_model=ActionItemRead)
async def create_action_item(payload: ActionItemCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> ActionItem:
    get_project_or_404(db, payload.project_id, current_user)
    if payload.meeting_id:
        meeting = get_meeting_or_404(db, payload.meeting_id, current_user)
        if meeting.project_id != payload.project_id:
            raise AppError("INVALID_MEETING", "Meeting does not belong to the selected project.", 400)
    item = ActionItem(**payload.model_dump(), user_id=current_user.id)
    if item.status == ActionStatus.done:
        item.completed_at = datetime.utcnow()
    apply_risk(item)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=list[ActionItemRead])
async def list_action_items(
    project_id: int | None = None,
    status: ActionStatus | None = None,
    assignee: str | None = None,
    risk_level: RiskLevel | None = None,
    due_from: date | None = None,
    due_to: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ActionItem]:
    query = db.query(ActionItem).filter(ActionItem.user_id == current_user.id)
    if project_id:
        query = query.filter(ActionItem.project_id == project_id)
    if status:
        query = query.filter(ActionItem.status == status)
    if assignee:
        query = query.filter(ActionItem.assignee == assignee)
    if risk_level:
        query = query.filter(ActionItem.risk_level == risk_level)
    if due_from:
        query = query.filter(ActionItem.due_date >= due_from)
    if due_to:
        query = query.filter(ActionItem.due_date <= due_to)
    return query.order_by(ActionItem.due_date.asc().nullslast(), ActionItem.created_at.desc()).all()


@router.get("/{action_item_id}", response_model=ActionItemRead)
async def read_action_item(action_item_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> ActionItem:
    return get_action_item_or_404(db, action_item_id, current_user)


@router.patch("/{action_item_id}", response_model=ActionItemRead)
async def update_action_item(action_item_id: int, payload: ActionItemUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> ActionItem:
    item = get_action_item_or_404(db, action_item_id, current_user)
    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] != item.status:
        item.status_changed_at = datetime.utcnow()
        item.completed_at = datetime.utcnow() if data["status"] == ActionStatus.done else None
    for key, value in data.items():
        setattr(item, key, value)
    apply_risk(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{action_item_id}", status_code=204)
async def delete_action_item(action_item_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> None:
    item = get_action_item_or_404(db, action_item_id, current_user)
    db.delete(item)
    db.commit()
