from typing import Literal
from datetime import datetime, timedelta
import hashlib
import secrets

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.projects import get_project_or_404
from app.core.exceptions import AppError
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import ProjectMember, Workspace, WorkspaceMember
from app.models.workspace import WorkspaceInvite
from app.services.workflow_service import notify
from app.services.permissions import require_project_manager, workspace_role

router = APIRouter(tags=["Workspaces"])


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class MemberCreate(BaseModel):
    user_id: int
    role: Literal["MANAGER", "MEMBER"] = "MEMBER"


class InviteCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    role: Literal["MANAGER", "MEMBER"] = "MEMBER"


class InviteAccept(BaseModel):
    token: str = Field(min_length=20, max_length=200)

    @field_validator("token", mode="before")
    @classmethod
    def strip_token(cls, value):
        return value.strip() if isinstance(value, str) else value


def require_owner(db, wid, uid):
    if workspace_role(db, wid, uid) != "OWNER":
        raise AppError("FORBIDDEN", "Workspace owner permission is required.", 403)


@router.patch("/workspaces/{workspace_id}")
def rename_workspace(workspace_id: int, payload: WorkspaceCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_owner(db, workspace_id, user.id)
    if not payload.name.strip():
        raise AppError("INVALID_NAME", "Name is required.", 400)
    workspace = db.get(Workspace, workspace_id)
    workspace.name = payload.name.strip()
    db.commit()
    return {"id": workspace_id, "name": workspace.name}


@router.post("/workspaces/{workspace_id}/invites", status_code=201)
def invite(workspace_id: int, payload: InviteCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    actor_role = workspace_role(db, workspace_id, user.id)
    if actor_role not in {"OWNER", "MANAGER"} or (actor_role == "MANAGER" and payload.role != "MEMBER"):
        raise AppError("FORBIDDEN", "팀장은 팀원만 초대할 수 있습니다.", 403)
    email = payload.email.strip().lower()
    if "@" not in email:
        raise AppError("INVALID_EMAIL", "Email is required.", 400)
    token = secrets.token_urlsafe(32)
    db.add(WorkspaceInvite(workspace_id=workspace_id, email=email, role=payload.role,
        token_hash=hashlib.sha256(token.encode()).hexdigest(), expires_at=datetime.utcnow() + timedelta(days=7)))
    existing = db.query(User).filter_by(email=email).first()
    if existing:
        notify(db, [existing.id], "workspace_invite", db.get(Workspace, workspace_id).name, "workspace", workspace_id, "Workspace 초대를 받았습니다.", user.id)
    db.commit()
    return {"token": token, "email": email, "expires_in_days": 7}


@router.post("/workspaces/{workspace_id}/members", status_code=201)
def add_member_by_email(workspace_id: int, payload: InviteCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    actor_role = workspace_role(db, workspace_id, user.id)
    if actor_role not in {"OWNER", "MANAGER"} or payload.role != "MEMBER":
        raise AppError("FORBIDDEN", "팀원 추가 권한이 필요합니다.", 403)
    target = db.query(User).filter_by(email=payload.email.strip().lower()).first()
    if not target:
        raise AppError("USER_NOT_FOUND", "가입된 계정이 없습니다. 초대 코드를 생성해 전달해 주세요.", 404)
    if db.query(WorkspaceMember).filter_by(workspace_id=workspace_id, user_id=target.id).first():
        raise AppError("ALREADY_MEMBER", "이미 Workspace에 등록된 팀원입니다.", 409)
    db.add(WorkspaceMember(workspace_id=workspace_id, user_id=target.id, role="MEMBER"))
    notify(db, [target.id], "workspace_member_added", db.get(Workspace, workspace_id).name, "workspace", workspace_id, "Workspace 팀원으로 추가되었습니다.", user.id)
    db.commit()
    return {"user_id": target.id, "email": target.email, "role": "MEMBER"}


@router.post("/workspace-invites/accept")
def accept_invite(payload: InviteAccept, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    invitation = db.query(WorkspaceInvite).filter_by(token_hash=hashlib.sha256(payload.token.encode()).hexdigest()).with_for_update().first()
    if not invitation:
        raise AppError("INVALID_INVITE", "초대 코드를 찾을 수 없습니다. 코드만 복사해 입력해 주세요.", 400)
    if invitation.email.strip().lower() != user.email.strip().lower():
        raise AppError("INVITE_EMAIL_MISMATCH", "초대받은 이메일과 로그인 계정이 다릅니다. 초대받은 계정으로 로그인해 주세요.", 400)
    if invitation.accepted_at:
        raise AppError("INVITE_USED", "이미 수락한 초대입니다. 상단에서 해당 팀을 선택해 주세요.", 400)
    if invitation.expires_at < datetime.utcnow():
        raise AppError("INVITE_EXPIRED", "초대 코드가 만료되었습니다. 팀장에게 새 코드를 요청해 주세요.", 400)
    if not db.query(WorkspaceMember).filter_by(workspace_id=invitation.workspace_id, user_id=user.id).first():
        db.add(WorkspaceMember(workspace_id=invitation.workspace_id, user_id=user.id, role=invitation.role))
    invitation.accepted_at = datetime.utcnow()
    db.commit()
    return {"workspace_id": invitation.workspace_id}


@router.delete("/workspaces/{workspace_id}/members/{member_id}", status_code=204)
def remove_member(workspace_id: int, member_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_owner(db, workspace_id, user.id)
    member = db.query(WorkspaceMember).filter_by(workspace_id=workspace_id, user_id=member_id).first()
    if not member:
        raise AppError("MEMBER_NOT_FOUND", "Member not found.", 404)
    if member.role == "OWNER":
        raise AppError("OWNER_PROTECTED", "Owner cannot be removed.", 409)
    from app.models.project import Project
    ids = [p.id for p in db.query(Project).filter_by(workspace_id=workspace_id)]
    db.query(ProjectMember).filter(ProjectMember.project_id.in_(ids), ProjectMember.user_id == member_id).delete(synchronize_session=False)
    db.delete(member)
    db.commit()


@router.get("/projects/{project_id}/members")
def project_members(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = get_project_or_404(db, project_id, user)
    from app.services.workflow_service import project_users
    return [{"user_id": p.id, "nickname": p.nickname, "email": p.email} for p in db.query(User).filter(User.id.in_(project_users(db, project.id))).all()]


@router.delete("/projects/{project_id}/members/{member_id}", status_code=204)
def remove_project_member(project_id: int, member_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = get_project_or_404(db, project_id, user)
    require_project_manager(db, project, user.id)
    if member_id == user.id:
        raise AppError("SELF_REMOVAL", "Ask the owner to remove your project membership.", 409)
    member = db.query(ProjectMember).filter_by(project_id=project_id, user_id=member_id).first()
    if not member:
        raise AppError("MEMBER_NOT_FOUND", "Project member not found.", 404)
    db.delete(member)
    db.commit()


@router.delete("/workspaces/{workspace_id}", status_code=204)
def delete_workspace(workspace_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_owner(db, workspace_id, user.id)
    from app.models.project import Project
    for project in db.query(Project).filter_by(workspace_id=workspace_id).all():
        db.delete(project)
    db.flush()
    db.query(WorkspaceInvite).filter_by(workspace_id=workspace_id).delete()
    db.query(WorkspaceMember).filter_by(workspace_id=workspace_id).delete()
    db.delete(db.get(Workspace, workspace_id))
    db.commit()


@router.get("/workspaces")
def list_workspaces(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Workspace, WorkspaceMember.role).join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id).filter(WorkspaceMember.user_id == user.id).all()
    return [{"id": w.id, "name": w.name, "role": role} for w, role in rows]


@router.post("/workspaces", status_code=201)
def create_workspace(payload: WorkspaceCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not payload.name.strip():
        raise AppError("INVALID_NAME", "Workspace name is required.", 400)
    workspace = Workspace(name=payload.name.strip(), created_by=user.id)
    db.add(workspace)
    db.flush()
    db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="OWNER"))
    db.commit()
    return {"id": workspace.id, "name": workspace.name, "role": "OWNER"}


@router.get("/workspaces/{workspace_id}/members")
def list_members(workspace_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    workspace_role(db, workspace_id, user.id)
    rows = db.query(WorkspaceMember, User).join(User, User.id == WorkspaceMember.user_id).filter(WorkspaceMember.workspace_id == workspace_id).all()
    return [{"user_id": u.id, "nickname": u.nickname, "email": u.email, "role": m.role} for m, u in rows]


@router.put("/workspaces/{workspace_id}/members/{member_id}")
def set_member(workspace_id: int, member_id: int, payload: MemberCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if workspace_role(db, workspace_id, user.id) != "OWNER":
        raise AppError("FORBIDDEN", "Workspace owner permission is required.", 403)
    if payload.user_id != member_id or not db.get(User, member_id):
        raise AppError("INVALID_MEMBER", "Invalid member.", 400)
    member = db.query(WorkspaceMember).filter_by(workspace_id=workspace_id, user_id=member_id).first()
    if member and member.role == "OWNER":
        raise AppError("OWNER_PROTECTED", "Owner role cannot be changed.", 409)
    if member:
        member.role = payload.role
    else:
        db.add(WorkspaceMember(workspace_id=workspace_id, user_id=member_id, role=payload.role))
    db.commit()
    return {"user_id": member_id, "role": payload.role}


@router.put("/projects/{project_id}/members/{member_id}")
def add_project_member(project_id: int, member_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = get_project_or_404(db, project_id, user)
    require_project_manager(db, project, user.id)
    if project.workspace_id is None:
        raise AppError("WORKSPACE_REQUIRED", "A workspace project is required.", 400)
    workspace_role(db, project.workspace_id, member_id)
    if not db.query(ProjectMember).filter_by(project_id=project_id, user_id=member_id).first():
        db.add(ProjectMember(project_id=project_id, user_id=member_id))
    db.commit()
    return {"project_id": project_id, "user_id": member_id}
