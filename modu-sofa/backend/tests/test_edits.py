"""자르기 · 내보내기 · AI 시작음(모의) — 실제 오디오로 렌더링 결과 길이를 확인한다."""

from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.edit_service import keep_ranges, normalize
from app.utils import ffmpeg_utils, render_utils
from tests.test_api_flow import A, B, _make_audio, _upload


@pytest.fixture(scope="module")
def client():
    settings.INTRO_PROVIDER = "mock"
    with TestClient(app) as c:
        yield c


def test_normalize_and_keep_ranges():
    cuts = normalize([(30, 40), (5, 10), (9, 12), (50, 50.1), (-3, 1), (95, 200)], 100)
    assert cuts == [(0.0, 1.0), (5.0, 12.0), (30.0, 40.0), (95.0, 100.0)]
    assert keep_ranges(cuts, 100) == [(1.0, 5.0), (12.0, 30.0), (40.0, 95.0)]


@pytest.mark.parametrize("enhance,ai", [(False, False), (True, True)])
def test_render_cuts_and_intro(tmp_dir, enhance, ai):
    src = tmp_dir / f"r_{enhance}.wav"
    _make_audio(src, 60, ["-ar", "44100", "-ac", "1"])
    intro = tmp_dir / "intro.mp3"
    from app.services.intro_service import _mock

    _mock(6, intro)
    intro_dur = ffmpeg_utils.probe(str(intro)).duration

    out = tmp_dir / f"out_{enhance}.mp3"
    render_utils.render(src, out, [(10, 20), (40, 45)], enhance=enhance, ai_denoise=ai)
    assert abs(ffmpeg_utils.probe(str(out)).duration - 45) < 0.3

    out2 = tmp_dir / f"out2_{enhance}.mp3"
    render_utils.render(src, out2, [(10, 20)], enhance=enhance, ai_denoise=ai, intro=intro, intro_duration=intro_dur)
    fade = min(1.0, min(1.5, max(0.3, intro_dur / 4)))
    assert abs(ffmpeg_utils.probe(str(out2)).duration - (50 + intro_dur - fade)) < 0.4


def test_cut_export_intro_api_flow(client, tmp_dir):
    src = tmp_dir / "flow.wav"
    _make_audio(src, 40, ["-ar", "22050", "-ac", "1"])
    eid, done = _upload(client, src, "flow.wav")
    assert done.status_code == 200

    r = client.put(f"/api/episodes/{eid}/cuts", json={"cuts": [{"start_time": 5, "end_time": 10}, {"start_time": 8, "end_time": 12}]}, headers=A)
    assert r.status_code == 200 and [(c["start_time"], c["end_time"]) for c in r.json()] == [(5, 12)]
    assert client.put(f"/api/episodes/{eid}/cuts", json={"cuts": []}, headers=B).status_code == 404
    assert client.put(f"/api/episodes/{eid}/cuts", json={"cuts": [{"start_time": 0, "end_time": 40}]}, headers=A).status_code == 400

    p = client.get(f"/api/episodes/{eid}/intro-prompt", headers=A).json()
    assert p["provider"] == "mock" and "No vocals" in p["prompt"]
    intro = client.post("/api/intros", json={"prompt": p["prompt"], "seconds": 5}, headers=A)
    assert intro.status_code == 202
    intros = client.get("/api/intros", headers=A).json()
    assert intros[0]["status"] == "completed" and intros[0]["preview_url"]
    assert client.get("/api/intros", headers=B).json() == []

    ex = client.post(
        f"/api/episodes/{eid}/exports",
        json={"apply_cuts": True, "enhance": True, "ai_denoise": True, "intro_id": intros[0]["id"]},
        headers=A,
    )
    assert ex.status_code == 202, ex.text
    jobs = client.get(f"/api/episodes/{eid}/exports", headers=A).json()
    assert jobs[0]["status"] == "completed", jobs[0]
    assert 35 < jobs[0]["duration"] < 40  # 40 - 7 + 5 - 크로스페이드

    url = client.get(f"/api/episodes/{eid}/exports/{jobs[0]['id']}/download", headers=A).json()["url"]
    u = urlparse(url)
    dl = client.get(f"{u.path}?{u.query}")
    assert dl.status_code == 200 and "attachment" in dl.headers["content-disposition"]
    assert dl.content[:3] == b"ID3" or dl.content[:2] == b"\xff\xfb"

    assert client.delete(f"/api/episodes/{eid}/exports/{jobs[0]['id']}", headers=A).status_code == 204
    assert client.delete(f"/api/intros/{intros[0]['id']}", headers=A).status_code == 204
