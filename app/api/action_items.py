from app.models.project import Project
from datetime import date, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.services.permissions import visible_projects, require_project_manager, workspace_role, require_task_access, is_project_manager
from app.services.workflow_service import validate_project_user, activity, notify
from app.api.deps import get_current_user
from app.api.meetings import get_meeting_or_404
from app.api.projects import get_project_or_404
from app.core.exceptions import AppError
from app.db.session import get_db
from app.models.action_item import ActionItem
from app.models.meeting import Meeting
from app.models.enums import ActionStatus, RiskLevel
from app.models.user import User
from app.schemas.action_item import ActionItemCreate, ActionItemRead, ActionItemUpdate
from app.services.risk_service import risk_service

router = APIRouter(prefix="/action-items", tags=["Action Items"])


def get_action_item_or_404(db: Session, action_item_id: int, user: User | None = None) -> ActionItem:
    query = db.query(ActionItem).filter(ActionItem.id == action_item_id)
    if user:
        query = query.filter(ActionItem.project_id.in_(visible_projects(db, user.id)))
    item = query.first()
    if not item:
        raise AppError("ACTION_ITEM_NOT_FOUND", "Action item not found.", 404)
    if user:
        require_task_access(db, item, user.id)
    return item


def apply_risk(item: ActionItem) -> None:
    score, level = risk_service.score(item)
    item.risk_score = score
    item.risk_level = level


@router.post("", response_model=ActionItemRead)
async def create_action_item(payload: ActionItemCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> ActionItem:
    require_project_manager(db, get_project_or_404(db, payload.project_id, current_user), current_user.id)
    if payload.meeting_id:
        meeting = get_meeting_or_404(db, payload.meeting_id, current_user)
        if meeting.project_id != payload.project_id:
            raise AppError("INVALID_MEETING", "Meeting does not belong to the selected project.", 400)
        if payload.assignee_id and meeting.report_status not in {"APPROVED", "PUBLISHED"}:
            raise AppError("APPROVAL_REQUIRED", "Approve the meeting before assigning its tasks.", 409)
    validate_project_user(db, payload.project_id, payload.assignee_id)
    if payload.assignee_id and payload.status not in {ActionStatus.todo}:
        raise AppError("INVALID_STATUS", "Assigned tasks start at ASSIGNED.", 400)
    item = ActionItem(**payload.model_dump(), user_id=current_user.id)
    if item.assignee_id:
        item.assigned_by = current_user.id
        item.workflow_status = "ASSIGNED"
        person = db.get(User, item.assignee_id)
        item.assignee = person.nickname or person.email
    if item.status == ActionStatus.done:
        item.completed_at = datetime.utcnow()
    apply_risk(item)
    db.add(item)
    db.flush()
    if item.assignee_id:
        activity(db, item.project_id, current_user.id, "task_assigned", "task", item.id)
        notify(db, [item.assignee_id], "task_assigned", item.task, "task", item.id, actor=current_user.id)
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
    query = db.query(ActionItem).filter(ActionItem.project_id.in_(visible_projects(db, current_user.id)))
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
    return [item for item in query.order_by(ActionItem.due_date.asc().nullslast(), ActionItem.created_at.desc()).all()
            if item.assignee_id == current_user.id or is_project_manager(db, db.get(Project, item.project_id), current_user.id)]


@router.get("/{action_item_id}", response_model=ActionItemRead)
async def read_action_item(action_item_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> ActionItem:
    return get_action_item_or_404(db, action_item_id, current_user)


@router.patch("/{action_item_id}", response_model=ActionItemRead)
async def update_action_item(action_item_id: int, payload: ActionItemUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> ActionItem:
    item = get_action_item_or_404(db, action_item_id, current_user)
    db.refresh(item, with_for_update=True)
    require_project_manager(db, db.get(Project, item.project_id), current_user.id)
    data = payload.model_dump(exclude_unset=True)
    if item.workflow_status and "status" in data:
        raise AppError("WORKFLOW_REQUIRED", "Use task workflow actions to change status.", 409)
    if item.workflow_status in {"APPROVED", "CANCELLED", "READY_FOR_REVIEW"}:
        raise AppError("TASK_LOCKED", "Reviewed tasks cannot be edited directly.", 409)
    if "meeting_id" in data and data["meeting_id"]:
        meeting = get_meeting_or_404(db, data["meeting_id"], current_user)
        if meeting.project_id != item.project_id:
            raise AppError("INVALID_MEETING", "Meeting does not belong to task project.", 400)
    if "assignee_id" in data:
        if data["assignee_id"] is None and item.workflow_status:
            raise AppError("ASSIGNEE_REQUIRED", "Reassign task to a project member.", 400)
        validate_project_user(db, item.project_id, data["assignee_id"])
        source_id = data.get("meeting_id", item.meeting_id)
        if data["assignee_id"] and source_id and db.get(Meeting, source_id).report_status not in {"APPROVED", "PUBLISHED"}:
            raise AppError("APPROVAL_REQUIRED", "Approve the meeting before assigning its tasks.", 409)
        if data["assignee_id"] and data["assignee_id"] != item.assignee_id:
            item.workflow_status = "ASSIGNED"
            item.status = ActionStatus.todo
            item.assigned_by = current_user.id
            item.completed_at = None
            person = db.get(User, data["assignee_id"])
            data["assignee"] = person.nickname or person.email
            activity(db, item.project_id, current_user.id, "task_assigned", "task", item.id)
            notify(db, [data["assignee_id"]], "task_assigned", item.task, "task", item.id, actor=current_user.id)
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
    require_project_manager(db, db.get(Project, item.project_id), current_user.id)
    if item.workflow_status:
        raise AppError("WORKFLOW_REQUIRED", "Cancel tasks through the review workflow to preserve history.", 409)
    db.delete(item)
    db.commit()
