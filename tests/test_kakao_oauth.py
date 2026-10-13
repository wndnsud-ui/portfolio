from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse
import httpx
import test_workspace_permissions as fixtures
from app.models.user import AuthAccount


class KakaoTests(fixtures.WorkspaceTests):
    def test_signup_and_repeat_login_without_email(self):
        profile = {"id": 123456789, "kakao_account": {"profile": {"nickname": "Kakao tester"}}}
        ids = []
        for expected_new in ["1", "0"]:
            self.client.cookies.set("kakao_oauth_state", "test-state")
            with patch("app.api.auth.exchange_kakao_code", new=AsyncMock(return_value=profile)):
                response = self.client.get("/api/auth/kakao/callback?state=test-state&code=test", follow_redirects=False)
            self.assertEqual(response.status_code, 307)
            fragment = parse_qs(urlparse(response.headers["location"]).fragment)
            self.assertEqual(fragment["onboarding"], [expected_new])
            me = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {fragment['token'][0]}"})
            self.assertEqual(me.status_code, 200)
            self.assertEqual(me.json()["nickname"], "Kakao tester")
            ids.append(me.json()["id"])
            self.assertIn("Max-Age=0", response.headers["set-cookie"])
        self.assertEqual(ids[0], ids[1])
        with self.sessions() as db:
            self.assertEqual(db.query(AuthAccount).filter_by(provider="kakao").count(), 1)
            self.assertIsNone(db.query(AuthAccount).filter_by(provider="kakao").one().provider_email)

    def test_invalid_state_cancellation_and_provider_failure(self):
        with patch("app.api.auth.exchange_kakao_code", new=AsyncMock()) as exchange:
            r = self.client.get("/api/auth/kakao/callback?state=invalid&code=test", follow_redirects=False)
            self.assertIn("auth_error=kakao_state", r.headers["location"])
            exchange.assert_not_called()
        for query, reason, failure in [
            ("error=access_denied", "kakao_cancelled", None),
            ("code=test", "kakao_network", httpx.ConnectError("offline")),
            ("code=test", "kakao_failed", None),
        ]:
            self.client.cookies.set("kakao_oauth_state", "test-state")
            with patch("app.api.auth.exchange_kakao_code", new=AsyncMock(side_effect=failure, return_value={"id": None})):
                r = self.client.get(f"/api/auth/kakao/callback?state=test-state&{query}", follow_redirects=False)
            self.assertIn(f"auth_error={reason}", r.headers["location"])
            self.assertNotIn("#token=", r.headers["location"])

    def kakao_login(self, kakao_id=987654321):
        profile = {"id": kakao_id, "kakao_account": {"profile": {"nickname": "No email"}}}
        self.client.cookies.set("kakao_oauth_state", "test-state")
        with patch("app.api.auth.exchange_kakao_code", new=AsyncMock(return_value=profile)):
            response = self.client.get("/api/auth/kakao/callback?state=test-state&code=test", follow_redirects=False)
        headers = {"Authorization": f"Bearer {parse_qs(urlparse(response.headers['location']).fragment)['token'][0]}"}
        return self.client.get("/api/auth/me", headers=headers).json(), headers

    def test_manager_adds_kakao_user_by_member_code(self):
        me, headers = self.kakao_login()
        self.assertRegex(me["member_code"], r"^[A-Z2-9]{8}$")
        path = f"/api/workspaces/{self.workspace}/members"
        typed = me["member_code"][:4].lower() + "-" + me["member_code"][4:].lower()
        added = self.client.post(path, headers=self.manager[1], json={"member_code": typed})
        self.assertEqual(added.status_code, 201, added.text)
        self.assertIsNone(added.json()["email"])
        self.assertEqual(self.client.post(path, headers=self.manager[1], json={"member_code": me["member_code"]}).status_code, 409)
        self.assertEqual(self.client.post(path, headers=self.manager[1], json={"member_code": "ZZZZZZZZ"}).status_code, 404)
        self.assertEqual(self.client.post(path, headers=self.manager[1], json={}).status_code, 400)
        members = self.client.get(path, headers=headers).json()
        row = next(m for m in members if m["user_id"] == me["id"])
        self.assertIsNone(row["email"])
        self.assertEqual(row["member_code"], me["member_code"])
        self.assertTrue(all(".invalid" not in (m["email"] or "") for m in members))

    def test_link_invite_without_email_is_single_use(self):
        _, headers = self.kakao_login()
        token = self.client.post(f"/api/workspaces/{self.workspace}/invites", headers=self.owner[1], json={}).json()["token"]
        accepted = self.client.post("/api/workspace-invites/accept", headers=headers, json={"token": token})
        self.assertEqual(accepted.status_code, 200, accepted.text)
        self.assertEqual(accepted.json()["workspace_id"], self.workspace)
        reused = self.client.post("/api/workspace-invites/accept", headers=self.outsider[1], json={"token": token})
        self.assertEqual(reused.json()["error"]["code"], "INVITE_USED")
        self.assertEqual(self.client.post(f"/api/workspaces/{self.workspace}/invites", headers=self.owner[1], json={"email": "not-an-email"}).status_code, 400)
