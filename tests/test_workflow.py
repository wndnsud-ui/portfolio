import io
from unittest.mock import AsyncMock, patch
import unittest
import test_workspace_permissions as fixtures
from app.models.meeting import Meeting
from app.models.workflow import FinalResult
from app.services.encryption_service import encrypt_secret
from app.models.user import User


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        fixtures.WorkspaceTests.setUp(self)
        self.client.put(f"/api/projects/{self.project}/members/{self.member[0]}", headers=self.owner[1])
        response = self.client.post("/api/meetings", headers=self.owner[1], json={"project_id": self.project,
            "recorder_id": self.member[0], "title": "Planning", "meeting_date": "2026-10-04", "transcript": "Speaker 1: 결정"})
        self.assertEqual(response.status_code, 200, response.text)
        self.mid = response.json()["id"]
        with self.sessions() as db:
            db.get(Meeting, self.mid).report_status = "APPROVED"
            db.commit()
        response = self.client.post("/api/action-items", headers=self.owner[1], json={"project_id": self.project,
            "meeting_id": self.mid, "assignee_id": self.member[0], "task": "Implement OAuth"})
        self.assertEqual(response.status_code, 200, response.text)
        self.tid = response.json()["id"]
        with self.sessions() as db:
            db.get(Meeting, self.mid).report_status = "DRAFT"
            db.commit()

    def tearDown(self):
        fixtures.WorkspaceTests.tearDown(self)

    def action(self, name, user=None, content=""):
        return self.client.post(f"/api/tasks/{self.tid}/{name}", headers=(user or self.member)[1], json={"content": content})

    def test_explicit_progress_and_dashboard_review_counts(self):
        self.action("accept")
        self.action("start")
        path = f"/api/tasks/{self.tid}/progress"
        payload = {"content": "Draft complete", "progress_percent": 65}
        self.assertEqual(self.client.post(path, headers=self.owner[1], json=payload).status_code, 403)
        for value in [-1, 101, 12.5]:
            self.assertEqual(self.client.post(path, headers=self.member[1],
                json={**payload, "progress_percent": value}).status_code, 422)
        self.assertEqual(self.client.post(path, headers=self.member[1], json=payload).status_code, 201)
        detail = self.client.get(f"/api/tasks/{self.tid}", headers=self.owner[1]).json()
        self.assertEqual(detail["progress_percent"], 65)
        self.assertEqual(detail["progress_content"], "Draft complete")
        self.assertIsNotNone(detail["progress_updated_at"])
        self.action("submit-review", content="Delivery")
        workspace = self.client.get(f"/api/projects/{self.project}", headers=self.owner[1]).json()["workspace_id"]
        dashboard = self.client.get(f"/api/workspaces/{workspace}/dashboard", headers=self.owner[1]).json()
        self.assertEqual(dashboard["kpis"]["review"], 1)
        self.assertEqual(dashboard["kpis"]["completed"], 0)
        self.assertEqual(dashboard["team_workload"][0]["review"], 1)
        self.assertEqual(dashboard["team_workload"][0]["active"], 0)
        self.assertEqual(dashboard["tasks"][0]["progress_percent"], 65)
        self.action("approve", self.owner)
        dashboard = self.client.get(f"/api/workspaces/{workspace}/dashboard", headers=self.owner[1]).json()
        self.assertEqual(dashboard["kpis"]["completed"], 1)
        self.assertEqual(dashboard["kpis"]["review"], 0)
        self.assertEqual(self.client.post(path, headers=self.member[1], json=payload).status_code, 403)

    def test_direct_manager_assignment_and_result_file(self):
        self.client.put(f"/api/projects/{self.project}/members/{self.manager[0]}", headers=self.owner[1])
        payload = {"project_id": self.project, "assignee_id": self.member[0],
                   "task": "Prepare delivery", "description": "Upload the delivery document", "priority": "high"}
        self.assertEqual(self.client.post("/api/action-items", headers=self.member[1], json=payload).status_code, 403)
        response = self.client.post("/api/action-items", headers=self.manager[1], json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        task = response.json()
        self.assertIsNone(task["meeting_id"])
        self.assertEqual(task["workflow_status"], "ASSIGNED")
        self.assertEqual(task["assigned_by"], self.manager[0])
        tid = task["id"]
        notices = self.client.get("/api/notifications", headers=self.member[1]).json()
        self.assertTrue(any(n["type"] == "task_assigned" and n["target_id"] == tid for n in notices))
        for action in ["accept", "start"]:
            self.assertEqual(self.client.post(f"/api/tasks/{tid}/{action}", headers=self.member[1]).status_code, 200)
        uploaded = self.client.post(f"/api/tasks/{tid}/attachments", headers=self.member[1],
                                   files={"file": ("delivery.txt", b"Delivery result", "text/plain")})
        self.assertEqual(uploaded.status_code, 201, uploaded.text)
        aid = uploaded.json()["id"]
        detail = self.client.get(f"/api/tasks/{tid}", headers=self.manager[1]).json()
        self.assertEqual(detail["attachments"][0]["file_name"], "delivery.txt")
        self.assertEqual(self.client.get(f"/api/task-attachments/{aid}", headers=self.manager[1]).content, b"Delivery result")
        self.assertEqual(self.client.get(f"/api/task-attachments/{aid}", headers=self.outsider[1]).status_code, 404)
        self.assertEqual(self.client.post(f"/api/tasks/{tid}/submit-review", headers=self.member[1],
                                         json={"content": "See delivery.txt"}).status_code, 200)
        self.assertEqual(self.client.post(f"/api/tasks/{tid}/approve", headers=self.manager[1]).status_code, 200)
        results = self.client.get(f"/api/projects/{self.project}/final-results", headers=self.member[1]).json()
        self.assertTrue(any(r["task_id"] == tid for r in results))
        self.assertEqual(self.client.get(f"/api/task-attachments/{aid}", headers=self.member[1]).content, b"Delivery result")

    def test_full_task_review_and_resubmission(self):
        self.assertEqual(self.action("start").status_code, 409)
        self.assertEqual(self.action("accept", self.owner).status_code, 403)
        for action in ["accept", "start"]:
            self.assertEqual(self.action(action).status_code, 200)
        self.assertEqual(self.client.post(f"/api/tasks/{self.tid}/progress", headers=self.member[1], json={"content": "OAuth callback added"}).status_code, 201)
        self.assertEqual(self.client.patch(f"/api/action-items/{self.tid}", headers=self.owner[1], json={"status": "done"}).status_code, 409)
        self.assertEqual(self.action("submit-review", content="Completed callback").status_code, 200)
        self.assertEqual(self.action("approve").status_code, 403)
        self.assertEqual(self.action("request-changes", self.owner, "Add deployed callback URI").status_code, 200)
        self.assertEqual(self.action("start").status_code, 200)
        self.assertEqual(self.action("submit-review", content="Added production URI").status_code, 200)
        approved = self.action("approve", self.owner)
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(approved.json()["workflow_status"], "APPROVED")
        self.assertEqual(self.action("approve", self.owner).status_code, 409)
        results = self.client.get(f"/api/projects/{self.project}/final-results", headers=self.member[1]).json()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["content"], "Added production URI")

    def test_recorder_manager_review_and_publication(self):
        self.assertEqual(self.client.post(f"/api/meetings/{self.mid}/approve", headers=self.member[1]).status_code, 403)
        self.assertEqual(self.client.post(f"/api/meetings/{self.mid}/publish", headers=self.owner[1]).status_code, 409)
        self.assertEqual(self.client.patch(f"/api/meetings/{self.mid}", headers=self.member[1], json={"summary": "Draft"}).status_code, 200)
        self.assertEqual(self.client.patch(f"/api/meetings/{self.mid}", headers=self.member[1], json={"recorder_id": self.member[0]}).status_code, 403)
        with self.sessions() as db:
            db.get(Meeting, self.mid).report_status = "AI_ANALYZED"
            db.commit()
        for action, person, body in [("submit-review", self.member, {}), ("request-changes", self.owner, {"content": "Revise summary"}),
                                    ("submit-review", self.member, {}), ("approve", self.owner, {}), ("publish", self.owner, {})]:
            response = self.client.post(f"/api/meetings/{self.mid}/{action}", headers=person[1], json=body)
            self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.client.patch(f"/api/meetings/{self.mid}", headers=self.owner[1], json={"summary": "Unauthorized published rewrite"}).status_code, 409)

    def test_comments_attachments_and_notification_isolation(self):
        response = self.client.post(f"/api/tasks/{self.tid}/comments", headers=self.owner[1], json={"content": "@member@example.com please review"})
        self.assertEqual(response.status_code, 201, response.text)
        cid = response.json()["id"]
        self.assertEqual(self.client.delete(f"/api/task-comments/{cid}", headers=self.member[1]).status_code, 403)
        self.assertEqual(self.client.get(f"/api/tasks/{self.tid}", headers=self.outsider[1]).status_code, 404)
        response = self.client.post(f"/api/tasks/{self.tid}/attachments", headers=self.member[1], files={"file": ("../notes.txt", b"notes", "text/plain")})
        self.assertEqual(response.status_code, 201, response.text)
        aid = response.json()["id"]
        self.assertEqual(response.json()["file_name"], "notes.txt")
        self.assertEqual(self.client.get(f"/api/task-attachments/{aid}", headers=self.outsider[1]).status_code, 404)
        self.assertEqual(self.client.get(f"/api/task-attachments/{aid}", headers=self.member[1]).content, b"notes")
        notifications = self.client.get("/api/notifications", headers=self.member[1]).json()
        self.assertTrue(any(n["type"] == "task_mention" for n in notifications))
        self.assertEqual(self.client.patch(f"/api/notifications/{notifications[0]['id']}/read", headers=self.outsider[1]).status_code, 404)

    def test_text_upload_skips_stt_and_speakers_preserve_original(self):
        with patch("app.services.transcription_service.transcription_service.transcribe", new_callable=AsyncMock) as stt:
            response = self.client.post(f"/api/meetings/{self.mid}/input/file", headers=self.member[1], files={"file": ("transcript.md", "Speaker 1: 확정\r\nSpeaker 2: 확인".encode(), "text/markdown")})
            self.assertEqual(response.status_code, 202, response.text)
            stt.assert_not_called()
        response = self.client.patch(f"/api/meetings/{self.mid}/speakers", headers=self.member[1], json={"speaker_names": {"Speaker 1": "혜영", "Speaker 2": "팀장"}})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("혜영", response.json()["transcript"])
        original = self.client.get(f"/api/meetings/{self.mid}", headers=self.member[1]).json()["transcript"]
        self.assertIn("Speaker 1", original)
        self.assertNotIn("\r", original)

    def test_invitation_binds_email_and_prevents_reuse(self):
        response = self.client.post(f"/api/workspaces/{self.workspace}/invites", headers=self.owner[1], json={"email": "outsider@example.com"})
        token = response.json()["token"]
        self.assertEqual(self.client.post("/api/workspace-invites/accept", headers=self.member[1], json={"token": token}).status_code, 400)
        self.assertEqual(self.client.post("/api/workspace-invites/accept", headers=self.outsider[1], json={"token": token}).status_code, 200)
        self.assertEqual(self.client.post("/api/workspace-invites/accept", headers=self.outsider[1], json={"token": token}).status_code, 400)
        self.assertEqual(self.client.get(f"/api/projects/{self.project}", headers=self.outsider[1]).status_code, 404)

    def test_notion_draft_and_unauthed_transcription_are_blocked(self):
        self.assertEqual(self.client.post(f"/api/meetings/{self.mid}/notion-sync", headers=self.owner[1]).status_code, 409)
        self.assertEqual(self.client.post("/api/transcriptions", files={"file": ("audio.wav", b"test")}).status_code, 401)

    def test_personal_openai_keys_remain_request_scoped(self):
        from app.services.integration_context import integration_value, credentials
        seen = []
        async def summarize(*args):
            seen.append(integration_value("openai_api_key"))
            return {"summary": "Draft", "issues": [], "decisions": [], "action_items": [], "open_questions": []}
        for person, key in [(self.owner, "owner-test-key"), (self.member, "member-test-key")]:
            self.client.patch("/api/settings", headers=person[1], json={"openai_api_key": key})
            with patch("app.services.ai_service.ai_service.summarize_meeting", side_effect=summarize):
                response = self.client.post(f"/api/meetings/{self.mid}/summarize", headers=person[1])
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["analysis_status"], "draft")
        self.assertEqual(seen, ["owner-test-key", "member-test-key"])
        self.assertIsNone(credentials.get())

    def test_audio_chunks_are_persisted_and_errors_are_safe(self):
        from app.models.workflow import TranscriptChunk
        self.client.patch("/api/settings", headers=self.member[1], json={"openai_api_key": "test-key"})
        async def transcribe(filename, content, content_type, on_chunk=None):
            on_chunk(2, 2, "second chunk")
            on_chunk(1, 2, "first chunk")
            return "first chunk\n\nsecond chunk"
        with patch("app.services.transcription_service.transcription_service.transcribe", side_effect=transcribe):
            response = self.client.post(f"/api/meetings/{self.mid}/input/file", headers=self.member[1], files={"file": ("audio.wav", b"mock")})
            self.assertEqual(response.status_code, 202, response.text)
        jobs = self.client.get(f"/api/meetings/{self.mid}/input/jobs", headers=self.member[1]).json()
        self.assertEqual(jobs[0]["status"], "TRANSCRIBED")
        self.assertEqual(jobs[0]["progress"], 100)
        with self.sessions() as db:
            self.assertEqual(db.query(TranscriptChunk).count(), 2)
        with patch("app.services.transcription_service.transcription_service.transcribe", side_effect=RuntimeError("must-not-leak-test-key")):
            self.client.post(f"/api/meetings/{self.mid}/input/file", headers=self.member[1], files={"file": ("audio.wav", b"mock")})
        jobs = self.client.get(f"/api/meetings/{self.mid}/input/jobs", headers=self.member[1]).json()
        self.assertEqual(jobs[0]["status"], "FAILED")
        self.assertNotIn("test-key", jobs[0]["error"])

    def test_full_ai_analysis_saves_candidates_without_confirmation(self):
        from app.schemas.analysis import SpeakerAnalysisResult, DecisionCandidate
        summary = {"summary": "AI draft", "issues": ["Issue"], "decisions": [], "open_questions": ["Follow-up"], "action_items": []}
        speakers = SpeakerAnalysisResult(meeting_id=0, summary="Draft", issues=[], speakers=[], action_items=[])
        decisions = [DecisionCandidate(topic="OAuth", value="Use Google OAuth", evidence="Speaker 1", confidence=0.9)]
        with patch("app.services.ai_service.ai_service.summarize_meeting", new_callable=AsyncMock, return_value=summary), \
             patch("app.services.ai_service.ai_service.analyze_speakers", new_callable=AsyncMock, return_value=speakers), \
             patch("app.services.ai_service.ai_service.extract_decision_candidates", new_callable=AsyncMock, return_value=decisions):
            response = self.client.post(f"/api/meetings/{self.mid}/analyze", headers=self.member[1])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["report_status"], "AI_ANALYZED")
        self.assertEqual(response.json()["analysis_status"], "draft")
        self.assertEqual(response.json()["candidates"]["decisions"][0]["topic"], "OAuth")
        self.assertEqual(self.client.get(f"/api/meetings/{self.mid}/input/jobs", headers=self.member[1]).json()[0]["status"], "REVIEW_READY")
        self.assertEqual(self.client.get(f"/api/projects/{self.project}/decisions", headers=self.owner[1]).json(), [])

    def test_published_notion_and_blog_use_authorized_sources(self):
        with self.sessions() as db:
            db.get(Meeting, self.mid).report_status = "PUBLISHED"
            db.commit()
        with patch("app.services.notion_service.notion_service.sync_meeting", new_callable=AsyncMock,
                   return_value={"meeting_id": self.mid, "notion_page_id": "mock-page", "status": "SYNCED"}) as sync:
            response = self.client.post(f"/api/meetings/{self.mid}/notion-sync", headers=self.owner[1])
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(self.client.post(f"/api/meetings/{self.mid}/notion-sync", headers=self.owner[1]).json()["status"], "ALREADY_SYNCED")
            self.assertEqual(sync.await_count, 1)
        self.assertEqual(self.client.post(f"/api/meetings/{self.mid}/notion-sync", headers=self.member[1]).status_code, 403)
        with patch("app.services.ai_service.ai_service._structured_response", new_callable=AsyncMock,
                   return_value={"content": "# Approved-source retrospective"}):
            response = self.client.post("/api/blog/generate", headers=self.owner[1], json={"source_type": "project", "source_id": self.project, "content_type": "retrospective"})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["status"], "draft")
            self.assertEqual(self.client.get("/api/blog/public").json(), [])

    def test_due_notifications_deduplicate_and_removal_revokes_access(self):
        from app.models.action_item import ActionItem
        from datetime import datetime
        from zoneinfo import ZoneInfo
        with self.sessions() as db:
            db.get(ActionItem, self.tid).due_date = datetime.now(ZoneInfo("Asia/Seoul")).date()
            db.commit()
        for _ in range(2):
            notices = self.client.get("/api/notifications", headers=self.member[1]).json()
        self.assertEqual(sum(n["type"] == "task_due_soon" for n in notices), 1)
        self.assertEqual(self.client.delete(f"/api/workspaces/{self.workspace}/members/{self.member[0]}", headers=self.owner[1]).status_code, 204)
        self.assertEqual(self.client.get(f"/api/tasks/{self.tid}", headers=self.member[1]).status_code, 404)
        self.assertEqual(self.client.get(f"/api/meetings/{self.mid}", headers=self.member[1]).status_code, 404)
