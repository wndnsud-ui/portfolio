from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

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
        query = query.filter(Project.user_id == user.id)
    project = query.first()
    if not project:
        raise AppError("PROJECT_NOT_FOUND", "Project not found.", 404)
    return project


@router.post("", response_model=ProjectRead)
async def create_project(payload: ProjectCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Project:
    project = Project(**payload.model_dump(), user_id=current_user.id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectRead])
async def list_projects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[Project]:
    return db.query(Project).filter(Project.user_id == current_user.id).order_by(Project.created_at.desc()).all()


@router.get("/{project_id}", response_model=ProjectRead)
async def read_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Project:
    return get_project_or_404(db, project_id, current_user)


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Project:
    project = get_project_or_404(db, project_id, current_user)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> None:
    project = get_project_or_404(db, project_id, current_user)
    db.delete(project)
    db.commit()
