"""Create shared MANAGER/MEMBER accounts for manual permission testing."""

import argparse

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.project import Project
from app.models.user import User, UserSettings
from app.models.workspace import ProjectMember, Workspace, WorkspaceMember
from app.services.auth_service import hash_password, verify_password


ACCOUNTS = (
    ("leader@decisionflow.test", "LeaderTest123!", "테스트 팀장", "MANAGER"),
    ("member@decisionflow.test", "MemberTest123!", "테스트 팀원", "MEMBER"),
)


def seed(*, allow_production: bool = False) -> None:
    if settings.app_env == "production" and not allow_production:
        raise RuntimeError("Use --allow-production to explicitly create test accounts in production.")
    with SessionLocal() as db:
        users = []
        for email, password, nickname, role in ACCOUNTS:
            user = db.query(User).filter_by(email=email).first()
            if user is None:
                user = User(email=email, nickname=nickname, password_hash=hash_password(password))
                user.settings = UserSettings()
                db.add(user)
                db.flush()
            elif not verify_password(password, user.password_hash):
                raise RuntimeError(f"Existing account has a different password: {email}; no changes saved.")
            users.append((user, role))

        leader = users[0][0]
        workspace = db.query(Workspace).filter_by(
            name="권한 테스트 Workspace", created_by=leader.id
        ).first()
        if workspace is None:
            workspace = Workspace(name="권한 테스트 Workspace", created_by=leader.id)
            db.add(workspace)
            db.flush()
        project = db.query(Project).filter_by(
            workspace_id=workspace.id, name="팀장·팀원 권한 테스트"
        ).first()
        if project is None:
            project = Project(
                workspace_id=workspace.id, user_id=leader.id,
                name="팀장·팀원 권한 테스트",
                description="팀장(MANAGER)과 팀원(MEMBER)의 업무 및 결재 권한을 테스트하는 프로젝트입니다.",
            )
            db.add(project)
            db.flush()
        for user, role in users:
            membership = db.query(WorkspaceMember).filter_by(
                workspace_id=workspace.id, user_id=user.id
            ).first()
            if membership is None:
                db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role=role))
            elif membership.role != role:
                raise RuntimeError(f"Existing test membership has a different role: {user.email}; no changes saved.")
            if not db.query(ProjectMember).filter_by(project_id=project.id, user_id=user.id).first():
                db.add(ProjectMember(project_id=project.id, user_id=user.id))
        db.commit()
        print(f"Test accounts ready; workspace_id={workspace.id}, project_id={project.id}")
        for email, _, _, role in ACCOUNTS:
            print(f"{role}: {email}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-production", action="store_true")
    seed(allow_production=parser.parse_args().allow_production)
