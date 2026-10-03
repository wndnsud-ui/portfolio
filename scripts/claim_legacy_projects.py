"""Assign explicitly selected, unowned legacy projects to an EXISTING account.

Usage: python scripts/claim_legacy_projects.py owner@example.com 1 [2 ...]
Review the email and project IDs before running. No account is created here.
"""
from pathlib import Path
import sys
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import settings


def claim(email, project_ids):
    engine = create_engine(settings.database_url)
    if engine.dialect.name != "postgresql" or not project_ids:
        raise RuntimeError("Select explicit project IDs in PostgreSQL")
    with engine.begin() as db:
        uid = db.execute(text("SELECT id FROM users WHERE email=:email"), {"email": email}).scalar_one_or_none()
        if uid is None:
            raise RuntimeError("Owner must register before legacy projects can be assigned")
        for pid in project_ids:
            project = db.execute(text("SELECT user_id, workspace_id FROM projects WHERE id=:id FOR UPDATE"), {"id": pid}).mappings().one()
            if project["user_id"] is not None or project["workspace_id"] is not None:
                raise RuntimeError(f"Project {pid} already has ownership; no changes applied")
        wid = db.execute(text("INSERT INTO workspaces (name,created_by,created_at) VALUES (:name,:uid,CURRENT_TIMESTAMP) RETURNING id"), {"name": "복원된 프로젝트", "uid": uid}).scalar_one()
        db.execute(text("INSERT INTO workspace_members (workspace_id,user_id,role) VALUES (:wid,:uid,'OWNER')"), {"wid": wid, "uid": uid})
        for pid in project_ids:
            db.execute(text("UPDATE projects SET user_id=:uid, workspace_id=:wid WHERE id=:pid"), {"uid": uid, "wid": wid, "pid": pid})
            for table in ["meetings", "action_items", "decisions"]:
                db.execute(text(f"UPDATE {table} SET user_id=:uid WHERE project_id=:pid AND user_id IS NULL"), {"uid": uid, "pid": pid})
        print(f"Assigned {len(project_ids)} legacy project(s) to existing user {uid}, workspace {wid}.")
    engine.dispose()


if __name__ == "__main__":
    claim(sys.argv[1], [int(value) for value in sys.argv[2:]])
