from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.project import Project
from app.models.workspace import ProjectMember, WorkspaceMember


def workspace_role(db: Session, workspace_id: int, user_id: int) -> str:
    member = db.query(WorkspaceMember).filter_by(workspace_id=workspace_id, user_id=user_id).first()
    if not member:
        raise AppError("WORKSPACE_NOT_FOUND", "Workspace not found.", 404)
    return member.role


def visible_projects(db: Session, user_id: int):
    owner_workspaces = select(WorkspaceMember.workspace_id).where(
        WorkspaceMember.user_id == user_id, WorkspaceMember.role == "OWNER")
    memberships = select(ProjectMember.project_id).join(
        Project, Project.id == ProjectMember.project_id).join(
        WorkspaceMember, and_(WorkspaceMember.workspace_id == Project.workspace_id,
                              WorkspaceMember.user_id == user_id)).where(ProjectMember.user_id == user_id)
    return select(Project.id).where(or_(
        and_(Project.workspace_id.is_(None), Project.user_id == user_id),
        Project.workspace_id.in_(owner_workspaces), Project.id.in_(memberships)))


def require_project_manager(db: Session, project: Project, user_id: int) -> None:
    if project.workspace_id is None:
        if project.user_id == user_id:
            return
    elif workspace_role(db, project.workspace_id, user_id) in {"OWNER", "MANAGER"}:
        if db.query(Project).filter(Project.id == project.id, Project.id.in_(visible_projects(db, user_id))).first():
            return
    raise AppError("FORBIDDEN", "Project manager permission is required.", 403)


def is_project_manager(db: Session, project: Project, user_id: int) -> bool:
    try:
        require_project_manager(db, project, user_id)
        return True
    except AppError:
        return False


def require_meeting_editor(db: Session, meeting, user_id: int) -> None:
    if meeting.recorder_id == user_id and db.query(Project).filter(
            Project.id == meeting.project_id, Project.id.in_(visible_projects(db, user_id))).first():
        return
    require_project_manager(db, db.get(Project, meeting.project_id), user_id)


def require_task_access(db: Session, task, user_id: int) -> None:
    project = db.query(Project).filter(Project.id == task.project_id, Project.id.in_(visible_projects(db, user_id))).first()
    if project and (task.assignee_id == user_id or is_project_manager(db, project, user_id)):
        return
    raise AppError("TASK_NOT_FOUND", "Task not found.", 404)
