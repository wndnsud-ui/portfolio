"""Read-only production verification; never creates users or business data."""
import sys
from pathlib import Path
import httpx

url = sys.argv[1].rstrip("/")
with httpx.Client(base_url=url, timeout=30) as client:
    health = client.get("/health")
    health.raise_for_status()
    assert health.json()["status"] == "ok"
    client.get("/").raise_for_status()
    schema = client.get("/openapi.json")
    schema.raise_for_status()
    paths = schema.json()["paths"]
    for route in ["/api/workspaces", "/api/tasks", "/api/notifications", "/api/workspaces/{workspace_id}/dashboard", "/api/meetings/{meeting_id}/approve"]:
        assert route in paths, route
    for route in ["/api/workspaces", "/api/tasks", "/api/notifications"]:
        assert client.get(route).status_code == 401, route
print("Production: health/home/OpenAPI 200; workspace/task/notification APIs present and anonymous access denied.")

if "--browser" in sys.argv:
    from playwright.sync_api import sync_playwright
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url, wait_until="networkidle")
        page.get_by_placeholder("이메일", exact=True).wait_for()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        assert not errors, errors
        artifact = Path(".tools/browser-smoke")
        artifact.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(artifact / "production-login.png"), full_page=True)
        browser.close()
    print("Production browser: login page loads, no JavaScript errors or mobile horizontal overflow.")
