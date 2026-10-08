import os
import unittest
from tempfile import TemporaryDirectory
from datetime import date

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-only-secret"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.core.config import settings


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.files = TemporaryDirectory(dir=".")
        self.previous_attachment_dir = settings.attachment_dir
        settings.attachment_dir = self.files.name
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine)
        self.app = create_app()
        def database():
            with self.sessions() as session:
                yield session
        self.app.dependency_overrides[get_db] = database
        self.client = TestClient(self.app)
        self.users = []
        for name in ["owner", "member", "outsider", "manager"]:
            response = self.client.post("/api/auth/register", json={"email": f"{name}@example.com", "password": "test-password"})
            self.assertEqual(response.status_code, 200, response.text)
            value = response.json()
            self.users.append((value["user"]["id"], {"Authorization": f"Bearer {value['access_token']}"}))
        self.owner, self.member, self.outsider, self.manager = self.users
        self.workspace = self.client.post("/api/workspaces", headers=self.owner[1], json={"name": "Team"}).json()["id"]
        for user, role in [(self.member, "MEMBER"), (self.manager, "MANAGER")]:
            response = self.client.put(f"/api/workspaces/{self.workspace}/members/{user[0]}", headers=self.owner[1], json={"user_id": user[0], "role": role})
            self.assertEqual(response.status_code, 200, response.text)
        self.project = self.client.post("/api/projects", headers=self.owner[1], json={"name": "Shared", "workspace_id": self.workspace}).json()["id"]

    def tearDown(self):
        self.client.close()
        self.engine.dispose()
        settings.attachment_dir = self.previous_attachment_dir
        self.files.cleanup()

    def test_project_membership_and_manager_permissions(self):
        for user in [self.member, self.outsider, self.manager]:
            self.assertEqual(self.client.get(f"/api/projects/{self.project}", headers=user[1]).status_code, 404)
        for user in [self.member, self.manager]:
            self.assertEqual(self.client.put(f"/api/projects/{self.project}/members/{user[0]}", headers=self.owner[1]).status_code, 200)
        self.assertEqual(self.client.get(f"/api/projects/{self.project}", headers=self.member[1]).status_code, 200)
        self.assertEqual(self.client.patch(f"/api/projects/{self.project}", headers=self.member[1], json={"name": "illegal"}).status_code, 403)
        self.assertEqual(self.client.patch(f"/api/projects/{self.project}", headers=self.manager[1], json={"name": "updated"}).status_code, 200)

    def test_meeting_visibility_and_confirmation_bypass(self):
        self.client.put(f"/api/projects/{self.project}/members/{self.member[0]}", headers=self.owner[1])
        response = self.client.post("/api/meetings", headers=self.owner[1], json={"project_id": self.project, "title": "Review", "meeting_date": str(date.today()), "transcript": "hello"})
        self.assertEqual(response.status_code, 200, response.text)
        mid = response.json()["id"]
        self.assertEqual(self.client.get(f"/api/meetings/{mid}", headers=self.member[1]).status_code, 200)
        self.assertEqual(self.client.get(f"/api/meetings/{mid}", headers=self.outsider[1]).status_code, 404)
        self.assertEqual(self.client.post(f"/api/meetings/{mid}/decisions/confirm", headers=self.member[1], json={"decisions": []}).status_code, 403)
        self.assertEqual(self.client.post("/api/decisions", headers=self.member[1], json={"project_id": self.project, "topic": "illegal", "value": "illegal", "status": "confirmed"}).status_code, 403)

    def test_manager_adds_and_invites_members_without_promoting(self):
        path = f"/api/workspaces/{self.workspace}"
        response = self.client.post(path + "/members", headers=self.manager[1], json={"email": "outsider@example.com"})
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["role"], "MEMBER")
        self.assertEqual(self.client.post(path + "/members", headers=self.manager[1], json={"email": "outsider@example.com"}).status_code, 409)
        self.assertEqual(self.client.post(path + "/members", headers=self.member[1], json={"email": "owner@example.com"}).status_code, 403)
        self.assertEqual(self.client.post(path + "/members", headers=self.manager[1], json={"email": "missing@example.com"}).status_code, 404)
        invitation = self.client.post(path + "/invites", headers=self.manager[1], json={"email": "outsider@example.com"})
        self.assertEqual(invitation.status_code, 201, invitation.text)
        self.assertEqual(self.client.post(path + "/invites", headers=self.manager[1], json={"email": "outsider@example.com", "role": "MANAGER"}).status_code, 403)

    def test_login_and_owner_protection(self):
        response = self.client.post("/api/auth/login", json={"email": "owner@example.com", "password": "test-password"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me", headers=self.owner[1]).status_code, 200)
        self.assertEqual(self.client.get("/api/auth/google/callback?code=test&state=invalid").status_code, 400)
        self.assertEqual(self.client.put(f"/api/workspaces/{self.workspace}/members/{self.owner[0]}", headers=self.owner[1], json={"user_id": self.owner[0], "role": "MEMBER"}).status_code, 409)
        self.assertEqual(self.client.put(f"/api/workspaces/{self.workspace}/members/{self.outsider[0]}", headers=self.member[1], json={"user_id": self.outsider[0], "role": "MANAGER"}).status_code, 403)

    def test_invite_whitespace_and_email_errors(self):
        invitation = self.client.post(f"/api/workspaces/{self.workspace}/invites", headers=self.owner[1], json={"email":"outsider@example.com"}).json()
        token = invitation["token"]
        mismatch = self.client.post("/api/workspace-invites/accept", headers=self.member[1], json={"token":token})
        self.assertEqual(mismatch.json()["error"]["code"], "INVITE_EMAIL_MISMATCH")
        accepted = self.client.post("/api/workspace-invites/accept", headers=self.outsider[1], json={"token":" \n"+token+"\n "})
        self.assertEqual(accepted.status_code, 200, accepted.text)
        reused = self.client.post("/api/workspace-invites/accept", headers=self.outsider[1], json={"token":token})
        self.assertEqual(reused.json()["error"]["code"], "INVITE_USED")


if __name__ == "__main__":
    unittest.main()
