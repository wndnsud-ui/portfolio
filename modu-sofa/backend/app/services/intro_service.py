"""AI 시작음 생성 (ElevenLabs Music API).

ELEVENLABS_API_KEY가 없으면 모의 Provider가 FFmpeg로 짧은 합성 차임을 만든다.
"""

import logging
import tempfile
import uuid
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import reload_analysis_settings, settings
from app.core.errors import conflict, not_found
from app.db.session import SessionLocal
from app.models import Episode, IntroClip, IntroStatus
from app.repositories import ai_repo
from app.schemas.edit import IntroCreate, IntroOut
from app.services.storage_service import get_storage
from app.utils import ffmpeg_utils

log = logging.getLogger(__name__)

ELEVENLABS_URL = "https://api.elevenlabs.io/v1/music"


def suggest_prompt(db: Session, ep: Episode) -> str:
    """에피소드 키워드로 시작음 프롬프트 초안을 만든다. 사용자가 화면에서 고칠 수 있다."""
    res = ai_repo.get_result(db, ep.id)
    kws = ", ".join((res.keywords or [])[:4]) if res else ""
    topic = f" The episode is about: {kws}." if kws else ""
    return (
        "Short instrumental podcast intro jingle, warm and friendly, modern acoustic and soft synth, "
        f"clear melodic hook, gentle build and a clean ending.{topic} No vocals."
    )


def list_intros(db: Session, user_id: uuid.UUID) -> list[IntroOut]:
    rows = db.scalars(select(IntroClip).where(IntroClip.user_id == user_id).order_by(IntroClip.created_at.desc()))
    storage = get_storage()
    out = []
    for r in rows:
        o = IntroOut.model_validate(r)
        if r.status == IntroStatus.COMPLETED and r.path:
            o.preview_url = storage.signed_url(r.path)
        out.append(o)
    return out


def create(db: Session, user_id: uuid.UUID, body: IntroCreate) -> IntroClip:
    reload_analysis_settings()
    running = db.scalar(
        select(IntroClip).where(IntroClip.user_id == user_id, IntroClip.status == IntroStatus.RUNNING)
    )
    if running:
        raise conflict("시작음을 만드는 중이에요. 끝난 뒤 다시 시도해 주세요.", "busy")
    clip = IntroClip(
        user_id=user_id, status=IntroStatus.RUNNING, prompt=body.prompt.strip(), provider=settings.intro_provider
    )
    db.add(clip)
    db.commit()
    db.refresh(clip)
    return clip


def delete(db: Session, user_id: uuid.UUID, intro_id: uuid.UUID) -> None:
    clip = db.get(IntroClip, intro_id)
    if not clip or clip.user_id != user_id:
        raise not_found()
    if clip.status == IntroStatus.RUNNING:
        raise conflict("만드는 중에는 지울 수 없어요.", "busy")
    if clip.path:
        try:
            get_storage().delete_prefix(clip.path)
        except Exception:  # noqa: BLE001
            log.warning("intro delete failed", exc_info=True)
    db.delete(clip)
    db.commit()


def _elevenlabs(prompt: str, seconds: int) -> bytes:
    r = httpx.post(
        ELEVENLABS_URL,
        params={"output_format": "mp3_44100_128"},
        headers={"xi-api-key": settings.ELEVENLABS_API_KEY},
        json={
            "prompt": prompt,
            "music_length_ms": seconds * 1000,
            "model_id": settings.ELEVENLABS_MUSIC_MODEL,
            "force_instrumental": True,
        },
        timeout=300,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"ElevenLabs {r.status_code}: {r.text[:300]}")
    return r.content


def _mock(seconds: int, out: Path) -> None:
    # 도-미-솔-도 아르페지오 차임 (각 음이 감쇠)
    step = seconds / 4
    expr = (
        f"0.25*sin(2*PI*if(lt(t,{step}),523.25,if(lt(t,{2*step}),659.25,if(lt(t,{3*step}),783.99,1046.5)))*t)"
        f"*exp(-2.2*mod(t,{step}))"
    )
    r = ffmpeg_utils._run(
        [ffmpeg_utils.ffmpeg_bin(), "-y", "-v", "error", "-f", "lavfi", "-i", f"aevalsrc='{expr}':d={seconds}:s=44100",
         "-ac", "2", "-c:a", "libmp3lame", "-b:a", "128k", str(out)]
    )
    if r.returncode != 0:
        raise ffmpeg_utils.FFmpegError(r.stderr.decode("utf-8", "replace")[-500:])


def run(intro_id: uuid.UUID, seconds: int) -> None:
    try:
        _run(intro_id, seconds)
    except Exception as e:  # noqa: BLE001
        log.exception("intro generation failed")
        with SessionLocal() as db:
            clip = db.get(IntroClip, intro_id)
            if clip:
                clip.status = IntroStatus.FAILED
                clip.error_message = str(e)[:300] if "ElevenLabs" in str(e) else f"시작음을 만들지 못했어요. ({type(e).__name__})"
                db.commit()


def _run(intro_id: uuid.UUID, seconds: int) -> None:
    with SessionLocal() as db:
        clip = db.get(IntroClip, intro_id)
        if not clip or clip.status != IntroStatus.RUNNING:
            return
        prompt, provider, user_id = clip.prompt, clip.provider, clip.user_id

    with tempfile.TemporaryDirectory(prefix="modu-sofa-intro-") as tmp:
        out = Path(tmp) / "intro.mp3"
        if provider == "elevenlabs":
            out.write_bytes(_elevenlabs(prompt, seconds))
        else:
            _mock(seconds, out)
        duration = ffmpeg_utils.probe(str(out)).duration
        path = f"{user_id}/intros/{intro_id}.mp3"
        get_storage().upload_file(path, out, "audio/mpeg")

    with SessionLocal() as db:
        clip = db.get(IntroClip, intro_id)
        if clip:
            clip.status = IntroStatus.COMPLETED
            clip.path = path
            clip.duration = duration
            db.commit()
