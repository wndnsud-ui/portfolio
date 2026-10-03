"""Run only against the isolated decisionflow_check PostgreSQL database."""
import os
import sys

url = sys.argv[1]
if not url.endswith("/decisionflow_check") or "127.0.0.1" not in url:
    raise SystemExit("Use the isolated local decisionflow_check database.")
os.environ["DATABASE_URL"] = url
os.environ["SECRET_KEY"] = "postgres-smoke-test-only"

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from fastapi.testclient import TestClient

config = Config("alembic.ini")
command.upgrade(config, "0001_initial_schema")
engine = create_engine(url)
with engine.begin() as connection:
    connection.execute(text("INSERT INTO users (email,created_at,updated_at) VALUES ('legacy@example.com',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP) ON CONFLICT(email) DO NOTHING"))
    connection.execute(text("INSERT INTO projects (user_id,name,created_at,updated_at) SELECT id,'Preserved PostgreSQL Project',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP FROM users WHERE email='legacy@example.com' AND NOT EXISTS (SELECT 1 FROM projects WHERE name='Preserved PostgreSQL Project')"))
command.upgrade(config, "head")
with engine.connect() as connection:
    assert connection.execute(text("SELECT workspace_id FROM projects WHERE name='Preserved PostgreSQL Project'")).scalar() is not None
    assert connection.execute(text("SELECT role FROM workspace_members JOIN users ON users.id=workspace_members.user_id WHERE email='legacy@example.com'")).scalar() == "OWNER"
from app.main import create_app
with TestClient(create_app()) as client:
    assert client.get("/health").status_code == 200
    assert client.get("/openapi.json").status_code == 200
    users = []
    for name in ["pgowner", "pgmember"]:
        response = client.post("/api/auth/register", json={"email": name + "@example.com", "password": "test-password"})
        if response.status_code == 409:
            response = client.post("/api/auth/login", json={"email": name + "@example.com", "password": "test-password"})
        response.raise_for_status()
        result = response.json()
        users.append((result["user"]["id"], {"Authorization": "Bearer " + result["access_token"]}))
    owner, member = users
    wid = client.post("/api/workspaces", headers=owner[1], json={"name": "PG smoke"}).json()["id"]
    assert client.put(f"/api/workspaces/{wid}/members/{member[0]}", headers=owner[1], json={"user_id": member[0], "role": "MEMBER"}).status_code == 200
    pid = client.post("/api/projects", headers=owner[1], json={"name": "PG Task", "workspace_id": wid}).json()["id"]
    assert client.put(f"/api/projects/{pid}/members/{member[0]}", headers=owner[1]).status_code == 200
    response = client.post("/api/action-items", headers=owner[1], json={"project_id": pid, "task": "PostgreSQL approval", "assignee_id": member[0]})
    assert response.status_code == 200, response.text
    tid = response.json()["id"]
    for name, person, content in [("accept", member, ""), ("start", member, ""), ("submit-review", member, "Result persisted"), ("approve", owner, "")]:
        response = client.post(f"/api/tasks/{tid}/{name}", headers=person[1], json={"content": content})
        assert response.status_code == 200, response.text
    assert len(client.get(f"/api/projects/{pid}/final-results", headers=owner[1]).json()) == 1
    assert client.post(f"/api/tasks/{tid}/approve", headers=owner[1]).status_code == 409
engine.dispose()
print("PostgreSQL: migration preserves legacy projects; membership, task approval, unique final result, health and OpenAPI passed.")
