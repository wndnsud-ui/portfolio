from unittest.mock import patch
import test_workspace_permissions as fixtures
from app.models.project import Project
from app.services.google_oauth_service import upsert_google_user
from app.services.onboarding_service import create_examples
from app.models.user import User

class OnboardingTests(fixtures.WorkspaceTests):
    def test_registration_examples_are_private_and_cleanup_preserves_real_projects(self):
        self.assertFalse(any(p["is_example"] for p in self.client.get("/api/projects",headers=self.owner[1]).json()))
        with self.sessions() as db:
            for user_id in [self.owner[0],self.outsider[0]]:
                create_examples(db,db.get(User,user_id))
            db.commit()
        examples=self.client.get("/api/projects",headers=self.owner[1]).json()
        guide=next(p for p in examples if p["is_example"])
        self.assertIsNone(guide["workspace_id"])
        self.assertEqual(self.client.get(f"/api/projects/{guide['id']}",headers=self.outsider[1]).status_code,404)
        tasks=self.client.get("/api/action-items",headers=self.owner[1]).json()
        self.assertEqual({t["status"] for t in tasks if t["project_id"]==guide["id"]},{"todo","in_progress","done"})
        self.assertFalse(any(n["type"]=="task_due_soon" for n in self.client.get("/api/notifications",headers=self.owner[1]).json()))
        # A real project with the same name must never be deleted as an example.
        real=self.client.post("/api/projects",headers=self.owner[1],json={"name":guide["name"]}).json()
        self.assertEqual(self.client.delete("/api/auth/example-data",headers=self.owner[1]).status_code,204)
        self.assertEqual(self.client.get(f"/api/projects/{real['id']}",headers=self.owner[1]).status_code,200)
        self.assertEqual(self.client.get(f"/api/projects/{guide['id']}",headers=self.owner[1]).status_code,404)
        self.assertTrue(any(p["is_example"] for p in self.client.get("/api/projects",headers=self.outsider[1]).json()))
        self.client.post("/api/auth/login",json={"email":"owner@example.com","password":"test-password"})
        self.assertFalse(any(p["is_example"] for p in self.client.get("/api/projects",headers=self.owner[1]).json()))

    def test_google_registration_does_not_create_examples(self):
        with self.sessions() as db:
            profile={"sub":"new-google-guide","email":"new-google@example.com","email_verified":True}
            user,created=upsert_google_user(db,profile)
            self.assertTrue(created)
            self.assertEqual(db.query(Project).filter_by(user_id=user.id).count(),0)
            upsert_google_user(db,profile)
            self.assertEqual(db.query(Project).filter_by(user_id=user.id).count(),0)
            _,created=upsert_google_user(db,{"sub":"existing-google-guide","email":"owner@example.com","email_verified":True})
            self.assertFalse(created)
            self.assertEqual(db.query(Project).filter_by(user_id=self.owner[0],is_example=True).count(),0)
