import hashlib
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock
import test_workspace_permissions as fixtures
from app.core.config import settings
from app.models.user import PasswordReset

class RecoveryTests(fixtures.WorkspaceTests):
    def test_reset_single_use_revokes_sessions_and_hides_account_existence(self):
        with patch.object(settings, "smtp_host", "smtp.test"), patch.object(settings, "smtp_from", "sender@test.local"), patch("app.services.password_reset_service.send_reset_email") as mail:
            existing = self.client.post("/api/auth/forgot-password", json={"email":"owner@example.com"})
            unknown = self.client.post("/api/auth/forgot-password", json={"email":"missing@example.com"})
            self.assertEqual(existing.json(), unknown.json())
            token = mail.call_args.args[1]
            self.client.post("/api/auth/forgot-password", json={"email":"owner@example.com"})
            self.assertEqual(mail.call_count, 1)
        response = self.client.post("/api/auth/reset-password", json={"token":token, "password":"replacement-password"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.client.get("/api/auth/me", headers=self.owner[1]).status_code, 401)
        self.assertEqual(self.client.post("/api/auth/reset-password", json={"token":token, "password":"another-password"}).status_code, 400)
        self.assertEqual(self.client.post("/api/auth/login", json={"email":"owner@example.com","password":"test-password"}).status_code, 401)
        self.assertEqual(self.client.post("/api/auth/login", json={"email":"owner@example.com","password":"replacement-password"}).status_code, 200)

    def test_expired_token_and_short_password(self):
        token = "expired-reset-token-for-testing"
        with self.sessions() as db:
            db.add(PasswordReset(user_id=self.owner[0], token_hash=hashlib.sha256(token.encode()).hexdigest(), expires_at=datetime.utcnow()-timedelta(minutes=1)))
            db.commit()
        self.assertEqual(self.client.post("/api/auth/reset-password", json={"token":token,"password":"valid-password"}).status_code, 400)
        self.assertEqual(self.client.post("/api/auth/reset-password", json={"token":token,"password":"short"}).status_code, 422)

    def test_google_success_cancellation_and_unverified_email(self):
        self.client.cookies.set("google_oauth_state", "test-state")
        with patch("app.api.auth.exchange_google_code", new=AsyncMock(return_value={"sub":"google-user-test","email":"owner@example.com","email_verified":True})):
            response = self.client.get("/api/auth/google/callback?state=test-state&code=test", follow_redirects=False)
            self.assertEqual(response.status_code, 307)
            self.assertIn("/#token=", response.headers["location"])
        self.client.cookies.set("google_oauth_state", "test-state")
        response = self.client.get("/api/auth/google/callback?state=test-state&error=access_denied", follow_redirects=False)
        self.assertIn("auth_error=google_cancelled", response.headers["location"])
        self.client.cookies.set("google_oauth_state", "test-state")
        with patch("app.api.auth.exchange_google_code", new=AsyncMock(return_value={"sub":"unverified-user","email":"owner@example.com","email_verified":False})):
            self.assertEqual(self.client.get("/api/auth/google/callback?state=test-state&code=test").status_code, 400)
