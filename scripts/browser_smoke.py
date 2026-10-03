"""Actual UI smoke test against an isolated local application; never production."""
from pathlib import Path
from uuid import uuid4
import sys
import httpx
from playwright.sync_api import sync_playwright

url = sys.argv[1].rstrip("/")
if not url.startswith("http://127.0.0.1:"):
    raise SystemExit("Browser smoke may only run against the isolated local test server.")
suffix = uuid4().hex[:8]
password = "browser-test-password"
client = httpx.Client(base_url=url + "/api", timeout=30)
users = []
for name in ["owner", "member"]:
    email = f"browser-{name}-{suffix}@example.com"
    result = client.post("/auth/register", json={"email": email, "nickname": name, "password": password})
    result.raise_for_status()
    value = result.json()
    users.append((email, value["user"]["id"], {"Authorization": "Bearer " + value["access_token"]}))
owner, member = users
wid = client.post("/workspaces", headers=owner[2], json={"name": "Browser Team " + suffix}).json()["id"]
client.put(f"/workspaces/{wid}/members/{member[1]}", headers=owner[2], json={"user_id": member[1], "role": "MEMBER"}).raise_for_status()
pid = client.post("/projects", headers=owner[2], json={"name": "Browser Project", "workspace_id": wid}).json()["id"]
client.put(f"/projects/{pid}/members/{member[1]}", headers=owner[2]).raise_for_status()
mid = client.post("/meetings", headers=owner[2], json={"project_id": pid, "recorder_id": member[1], "title": "Browser Planning", "meeting_date": "2026-10-04", "transcript": "Speaker 1: implement callback"}).json()["id"]
client.patch(f"/meetings/{mid}", headers=member[2], json={"summary": "Verified draft"}).raise_for_status()
for action, person in [("submit-review", member), ("approve", owner), ("publish", owner)]:
    client.post(f"/meetings/{mid}/{action}", headers=person[2]).raise_for_status()
tid = client.post("/action-items", headers=owner[2], json={"project_id": pid, "meeting_id": mid, "task": "Browser OAuth task", "assignee_id": member[1]}).json()["id"]
artifact = Path(".tools/browser-smoke")
artifact.mkdir(parents=True, exist_ok=True)
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel="msedge", headless=True)
    errors = []
    def login(email, mobile=False):
        context = browser.new_context(viewport={"width": 390 if mobile else 1440, "height": 844 if mobile else 1000}, device_scale_factor=1)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url)
        page.get_by_placeholder("이메일", exact=True).fill(email)
        page.get_by_placeholder("비밀번호", exact=True).fill(password)
        page.locator("form").get_by_role("button", name="로그인", exact=True).click()
        page.get_by_role("combobox", name="Workspace 전환").select_option(str(wid))
        page.get_by_role("heading", name="Browser Team " + suffix).wait_for()
        return context, page
    member_context, page = login(member[0])
    page.get_by_role("button", name="내 업무", exact=True).click()
    page.get_by_role("button", name="Browser OAuth task", exact=False).click()
    page.get_by_role("button", name="업무 수락", exact=True).click()
    page.get_by_role("button", name="업무 시작", exact=True).click()
    page.get_by_placeholder("완료 결과 또는 요청 사유를 작성하세요.").fill("Browser verified result")
    page.get_by_role("button", name="결재 요청", exact=True).click()
    page.get_by_text("결재 대기", exact=True).first.wait_for()
    page.screenshot(path=str(artifact / "member-task.png"), full_page=True)
    page.get_by_role("button", name="닫기", exact=True).click()
    page.get_by_title("로그아웃").click()
    page.get_by_placeholder("이메일", exact=True).wait_for()
    assert page.evaluate("localStorage.getItem('decisionflow_token')") is None
    owner_context, owner_page = login(owner[0])
    owner_page.get_by_role("button", name="업무 · 결재함", exact=True).click()
    owner_page.get_by_role("button", name="Browser OAuth task", exact=False).click()
    owner_page.get_by_role("button", name="승인 · 결과 게시", exact=True).click()
    owner_page.get_by_text("승인 완료", exact=True).first.wait_for()
    owner_page.get_by_role("button", name="닫기", exact=True).click()
    owner_page.get_by_role("button", name="최종 결과", exact=True).click()
    owner_page.get_by_text("Browser verified result", exact=True).wait_for()
    owner_page.screenshot(path=str(artifact / "owner-results.png"), full_page=True)
    mobile_context, mobile = login(member[0], mobile=True)
    mobile.screenshot(path=str(artifact / "member-mobile.png"), full_page=True)
    assert mobile.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "Mobile page overflows horizontally"
    assert not errors, errors
    browser.close()
client.close()
print("Browser: member accepts/starts/submits task, owner approves and views result, logout removes token, mobile has no overflow, no JavaScript errors.")
