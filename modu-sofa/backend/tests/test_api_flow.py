"""실제 오디오 파일(ffmpeg로 생성)로 업로드 → 전처리 → STT(mock) → AI(mock) → 편집 API까지 확인."""

import subprocess
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.utils.ffmpeg_utils import ffmpeg_bin

A = {"Authorization": "Bearer dev:tester"}
B = {"Authorization": "Bearer dev:other"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _make_audio(path, seconds, fmt_args):
    subprocess.run(
        [ffmpeg_bin(), "-y", "-v", "error", "-f", "lavfi", "-i", f"sine=frequency=220:duration={seconds}", *fmt_args, str(path)],
        check=True,
    )


def _upload(client, path, filename, headers=A):
    ep = client.post("/api/episodes", json={"title": None}, headers=headers).json()
    size = path.stat().st_size
    r = client.post(f"/api/episodes/{ep['id']}/upload-url", json={"filename": filename, "size": size}, headers=headers)
    assert r.status_code == 200, r.text
    u = urlparse(r.json()["upload_url"])
    put = client.put(f"{u.path}?{u.query}", content=path.read_bytes(), headers=r.json()["headers"])
    assert put.status_code == 200, put.text
    done = client.post(f"/api/episodes/{ep['id']}/upload-complete", headers=headers)
    return ep["id"], done


def test_requires_auth(client):
    assert client.get("/api/episodes").status_code == 401


def test_rejects_unsupported_extension(client):
    ep = client.post("/api/episodes", json={}, headers=A).json()
    r = client.post(f"/api/episodes/{ep['id']}/upload-url", json={"filename": "a.mp4", "size": 10}, headers=A)
    assert r.status_code == 400
    assert "MP3, WAV, M4A" in r.json()["detail"]["message"]


def test_rejects_corrupted_file(client, tmp_dir):
    bad = tmp_dir / "broken.m4a"
    bad.write_bytes(b"not really audio" * 100)
    _, done = _upload(client, bad, "녹음_손상.m4a")
    assert done.status_code == 400
    assert "재생할 수 없어요" in done.json()["detail"]["message"]


def test_full_flow(client, tmp_dir):
    src = tmp_dir / "ep.wav"
    _make_audio(src, 95, ["-ar", "22050", "-ac", "1"])
    eid, done = _upload(client, src, "ep05_대운이야기.wav")
    assert done.status_code == 200, done.text

    # TestClient는 BackgroundTasks를 응답 직후 동기로 실행한다
    ep = client.get(f"/api/episodes/{eid}", headers=A).json()
    assert ep["status"] == "transcribed", ep
    assert ep["ai_status"] == "completed", ep
    assert abs(ep["duration"] - 95) < 0.5
    assert ep["playback_url"] and ep["peaks_url"]
    assert ep["stt_model"] == "mock"

    # 접근 제어: 다른 사용자는 404
    assert client.get(f"/api/episodes/{eid}", headers=B).status_code == 404
    assert client.get(f"/api/episodes/{eid}/transcript", headers=B).status_code == 404

    # 재생 파일 Range 요청
    u = urlparse(ep["playback_url"])
    rng = client.get(f"{u.path}?{u.query}", headers={"Range": "bytes=0-99"})
    assert rng.status_code == 206 and len(rng.content) == 100

    tr = client.get(f"/api/episodes/{eid}/transcript", headers=A).json()
    segs = tr["segments"]
    assert segs and all(s["end_time"] <= ep["duration"] + 0.01 for s in segs)
    assert [s["seq"] for s in segs] == list(range(1, len(segs) + 1))

    # 문장 수정: original_text 불변
    s0 = segs[1]
    r = client.patch(f"/api/transcripts/{s0['id']}", json={"edited_text": "고친 문장"}, headers=A).json()
    assert r["edited_text"] == "고친 문장" and r["original_text"] == s0["original_text"]
    r = client.post(f"/api/transcripts/{s0['id']}/revert", headers=A).json()
    assert r["edited_text"] is None
    assert client.patch(f"/api/transcripts/{s0['id']}", json={"edited_text": "x"}, headers=B).status_code == 404

    # Soft delete / restore
    assert client.delete(f"/api/transcripts/{s0['id']}", headers=A).json()["is_deleted"] is True
    assert client.post(f"/api/transcripts/{s0['id']}/restore", headers=A).json()["is_deleted"] is False

    # 화자 이름 / 병합 / 되돌리기
    sp = client.get(f"/api/episodes/{eid}/speakers", headers=A).json()["speakers"]
    assert len(sp) >= 2
    r = client.patch(f"/api/speakers/{sp[0]['id']}", json={"display_name": "혜영"}, headers=A).json()
    assert r["speakers"][0]["display_name"] == "혜영"
    merged = client.post(
        f"/api/episodes/{eid}/speakers/merge", json={"from_id": sp[1]["id"], "into_id": sp[0]["id"]}, headers=A
    ).json()
    assert len(merged["speakers"]) == len(sp) - 1
    assert merged["last_merge"]["segment_count"] == sp[1]["segment_count"]
    undone = client.post(f"/api/episodes/{eid}/speakers/merge/undo", headers=A).json()
    assert len(undone["speakers"]) == len(sp)
    assert {s["id"]: s["segment_count"] for s in undone["speakers"]} == {s["id"]: s["segment_count"] for s in sp}

    # AI 결과: 챕터 시간 = 실제 Segment 시간, 오름차순 / 하이라이트 인용문 = 실제 텍스트
    ai = client.get(f"/api/episodes/{eid}/ai", headers=A).json()
    assert len(ai["title_candidates"]) == 3
    by_id = {s["id"]: s for s in segs}
    times = [c["start_time"] for c in ai["chapters"]]
    assert times == sorted(times) and len(times) >= 3
    assert all(by_id[c["start_segment_id"]]["start_time"] == c["start_time"] for c in ai["chapters"])
    for h in ai["highlights"]:
        assert by_id[h["start_segment_id"]]["start_time"] == h["start_time"]
        assert by_id[h["end_segment_id"]]["end_time"] == h["end_time"]
        assert by_id[h["start_segment_id"]]["original_text"] in h["text"]

    r = client.post(f"/api/episodes/{eid}/ai/title", json={"title": ai["title_candidates"][1]}, headers=A).json()
    assert r["title"] == ai["title_candidates"][1]

    # 재분석 → 수정 내용 초기화
    client.patch(f"/api/transcripts/{segs[0]['id']}", json={"edited_text": "수정"}, headers=A)
    assert client.post(f"/api/episodes/{eid}/transcribe", headers=A).status_code == 200
    tr2 = client.get(f"/api/episodes/{eid}/transcript", headers=A).json()
    assert tr2["edited_count"] == 0 and tr2["named_speaker_count"] == 0

    # 목록 카운트 + 삭제
    lst = client.get("/api/episodes", headers=A).json()
    assert any(e["id"] == eid and e["counts"]["chapters"] >= 3 for e in lst)
    assert client.delete(f"/api/episodes/{eid}", headers=A).status_code == 204
    assert client.get(f"/api/episodes/{eid}", headers=A).status_code == 404


def test_job_recovery_marks_failed(client):
    from app.db.session import SessionLocal
    from app.models import Episode
    from app.services.job_recovery_service import recover_stuck_jobs
    from app.services.transcript_service import REANALYZABLE  # noqa: F401

    ep = client.post("/api/episodes", json={}, headers=A).json()
    with SessionLocal() as db:
        row = db.get(Episode, __import__("uuid").UUID(ep["id"]))
        row.status = "transcribing"
        db.commit()
    assert recover_stuck_jobs() >= 1
    got = client.get(f"/api/episodes/{ep['id']}", headers=A).json()
    assert got["status"] == "failed" and got["error_stage"] == "transcription"
    assert got["error_message"] == "서버 재시작으로 작업이 중단되었습니다"


def test_claim_prevents_duplicate_run():
    import uuid

    from app.db.session import SessionLocal
    from app.models import Episode
    from app.repositories import episode_repo

    with SessionLocal() as db:
        ep = Episode(user_id=uuid.uuid4(), status="uploaded", ai_status="none")
        db.add(ep)
        db.commit()
        assert episode_repo.claim(db, ep.id, "processing", ["uploaded", "failed"]) is True
        assert episode_repo.claim(db, ep.id, "processing", ["uploaded", "failed"]) is False
