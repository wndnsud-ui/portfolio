from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.services.permissions import visible_projects, require_project_manager, workspace_role
from app.api.deps import get_current_user
from app.core.exceptions import AppError
from app.db.session import get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["Projects"])


def get_project_or_404(db: Session, project_id: int, user: User | None = None) -> Project:
    query = db.query(Project).filter(Project.id == project_id)
    if user:
        query = query.filter(Project.id.in_(visible_projects(db, user.id)))
    project = query.first()
    if not project:
        raise AppError("PROJECT_NOT_FOUND", "Project not found.", 404)
    return project


@router.post("", response_model=ProjectRead)
async def create_project(payload: ProjectCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Project:
    if payload.workspace_id is not None:
        if workspace_role(db, payload.workspace_id, current_user.id) not in {"OWNER", "MANAGER"}:
            raise AppError("FORBIDDEN", "Manager permission is required.", 403)
    project = Project(**payload.model_dump(), user_id=current_user.id)
    db.add(project)
    db.flush()
    if project.workspace_id is not None:
        from app.models.workspace import ProjectMember
        db.add(ProjectMember(project_id=project.id, user_id=current_user.id))
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectRead])
async def list_projects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[Project]:
    return db.query(Project).filter(Project.id.in_(visible_projects(db, current_user.id))).order_by(Project.created_at.desc()).all()


@router.get("/{project_id}", response_model=ProjectRead)
async def read_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Project:
    return get_project_or_404(db, project_id, current_user)


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Project:
    project = get_project_or_404(db, project_id, current_user)
    require_project_manager(db, project, current_user.id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> None:
    project = get_project_or_404(db, project_id, current_user)
    require_project_manager(db, project, current_user.id)
    db.delete(project)
    db.commit()
