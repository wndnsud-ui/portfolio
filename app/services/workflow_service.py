from sqlalchemy import or_, select, update
from app.core.exceptions import AppError
from app.models.project import Project
from app.models.workspace import WorkspaceMember, ProjectMember
from app.models.workflow import ActivityLog, Notification
from app.services.permissions import visible_projects


def validate_project_user(db, project_id, user_id):
    if user_id is not None and not db.query(Project).filter(Project.id == project_id, Project.id.in_(visible_projects(db, user_id))).first():
        raise AppError("INVALID_MEMBER", "User must belong to this project.", 400)


def project_users(db, project_id, managers=False):
    project = db.get(Project, project_id)
    if project.workspace_id is None:
        return [project.user_id] if project.user_id else []
    query = db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == project.workspace_id)
    if managers:
        query = query.filter(WorkspaceMember.role.in_(["OWNER", "MANAGER"]))
    rows = query.filter(or_(WorkspaceMember.role == "OWNER", WorkspaceMember.user_id.in_(
        select(ProjectMember.user_id).where(ProjectMember.project_id == project_id)))).all()
    return [m.user_id for m in rows]


def notify(db, recipients, event, title, kind, target_id, message="", actor=None):
    for uid in set(recipients):
        if uid is not None and uid != actor:
            db.add(Notification(user_id=uid, type=event, title=title, message=message,
                                target_type=kind, target_id=target_id))


def activity(db, project_id, actor_id, event, kind, target_id, content=""):
    db.add(ActivityLog(project_id=project_id, actor_id=actor_id, event=event,
                       target_type=kind, target_id=target_id, content=content))


def transition(db, entity, attribute, allowed, destination):
    previous = getattr(entity, attribute)
    if previous not in allowed:
        raise AppError("INVALID_TRANSITION", f"Cannot change {previous} to {destination}.", 409)
    result = db.execute(update(type(entity)).where(type(entity).id == entity.id,
        getattr(type(entity), attribute) == previous).values({attribute: destination}),
        execution_options={"synchronize_session": False})
    if result.rowcount != 1:
        raise AppError("CONCURRENT_CHANGE", "The record changed. Reload and try again.", 409)
    db.refresh(entity)
    return previous
