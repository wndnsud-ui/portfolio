"""분석 취소: 화면 상태는 즉시 바뀌고, 백그라운드 작업은 결과를 덮어쓰지 않는다."""

import threading
import uuid

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models import Episode
from app.repositories import episode_repo
from app.services import openai_client, transcription_service
from tests.test_api_flow import A, _make_audio, _upload


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _status(client, eid):
    return client.get(f"/api/episodes/{eid}", headers=A).json()


def _run_blocked_pipeline(monkeypatch, eid):
    """받아쓰기가 release 될 때까지 멈춰 있는 파이프라인을 스레드로 돌린다."""
    started, release = threading.Event(), threading.Event()
    real = openai_client.transcribe_chunk

    def slow(path, offset, length):
        started.set()
        release.wait(10)
        return real(path, offset, length)

    monkeypatch.setattr(openai_client, "transcribe_chunk", slow)
    with SessionLocal() as db:
        assert episode_repo.claim(db, uuid.UUID(eid), "processing", ["uploaded", "failed", "transcribed"])
    t = threading.Thread(target=transcription_service.run_pipeline, args=(uuid.UUID(eid),))
    t.start()
    assert started.wait(30)
    return t, release


def test_cancel_first_analysis(client, tmp_dir, monkeypatch):
    src = tmp_dir / "cancel.wav"
    _make_audio(src, 30, ["-ar", "16000", "-ac", "1"])
    # 업로드만 하고 파이프라인은 직접 돌린다
    monkeypatch.setattr(transcription_service, "run_pipeline", lambda _id: None)
    eid, done = _upload(client, src, "cancel.wav")
    monkeypatch.undo()
    assert done.status_code == 200
    with SessionLocal() as db:  # upload-complete가 선점한 상태를 되돌려 직접 실행
        ep = db.get(Episode, uuid.UUID(eid))
        ep.status = "uploaded"
        db.commit()

    t, release = _run_blocked_pipeline(monkeypatch, eid)
    r = client.post(f"/api/episodes/{eid}/cancel", headers=A)
    assert r.status_code == 200
    got = _status(client, eid)
    assert got["status"] == "failed" and got["error_message"] == "분석을 취소했어요."

    release.set()
    t.join(30)
    got = _status(client, eid)
    assert got["status"] == "failed" and got["error_message"] == "분석을 취소했어요."  # 덮어쓰지 않음
    assert client.get(f"/api/episodes/{eid}/transcript", headers=A).json()["segments"] == []

    # 취소 후 다시 분석하면 정상 완료
    assert client.post(f"/api/episodes/{eid}/transcribe", headers=A).status_code == 200
    assert _status(client, eid)["status"] == "transcribed"


def test_cancel_reanalysis_keeps_old_transcript(client, tmp_dir, monkeypatch):
    src = tmp_dir / "keep.wav"
    _make_audio(src, 30, ["-ar", "16000", "-ac", "1"])
    eid, _ = _upload(client, src, "keep.wav")
    before = client.get(f"/api/episodes/{eid}/transcript", headers=A).json()["segments"]
    assert before
    seg = before[0]
    client.patch(f"/api/transcripts/{seg['id']}", json={"edited_text": "내가 고친 문장"}, headers=A)

    t, release = _run_blocked_pipeline(monkeypatch, eid)
    assert client.post(f"/api/episodes/{eid}/cancel", headers=A).status_code == 200
    assert _status(client, eid)["status"] == "transcribed"
    release.set()
    t.join(30)

    after = client.get(f"/api/episodes/{eid}/transcript", headers=A).json()
    assert [s["id"] for s in after["segments"]] == [s["id"] for s in before]
    assert after["segments"][0]["edited_text"] == "내가 고친 문장"
    assert _status(client, eid)["status"] == "transcribed"


def test_cancel_when_nothing_running(client):
    ep = client.post("/api/episodes", json={}, headers=A).json()
    assert client.post(f"/api/episodes/{ep['id']}/cancel", headers=A).status_code == 409
