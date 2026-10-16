"""완성 오디오 내보내기: 자르기 · 음량/잡음 보정 · AI 잡음 제거 · 시작음을 적용한 새 MP3를 만든다.

원본 파일은 그대로 두고 {prefix}/exports/{export_id}.mp3 로 저장한다.
"""

import logging
import re
import tempfile
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import bad_request, conflict, not_found
from app.db.session import SessionLocal
from app.models import (
    Episode,
    EpisodeStatus,
    ExportJob,
    ExportStatus,
    IntroClip,
    IntroStatus,
)
from app.schemas.edit import ExportCreate, ExportOut
from app.services import edit_service
from app.services.storage_service import episode_prefix, get_storage
from app.utils import ffmpeg_utils, render_utils

log = logging.getLogger(__name__)


def list_exports(db: Session, ep: Episode) -> list[ExportOut]:
    rows = db.scalars(select(ExportJob).where(ExportJob.episode_id == ep.id).order_by(ExportJob.created_at.desc()))
    return [ExportOut.model_validate(r) for r in rows]


def create(db: Session, ep: Episode, body: ExportCreate) -> ExportJob:
    if ep.status != EpisodeStatus.TRANSCRIBED or not ep.original_path:
        raise conflict("분석이 끝난 에피소드만 내보낼 수 있어요.", "not_ready")
    running = db.scalar(
        select(ExportJob).where(ExportJob.episode_id == ep.id, ExportJob.status == ExportStatus.RUNNING)
    )
    if running:
        raise conflict("이미 내보내는 중이에요. 끝난 뒤 다시 시도해 주세요.", "busy")
    if body.intro_id:
        intro = db.get(IntroClip, body.intro_id)
        if not intro or intro.user_id != ep.user_id:
            raise not_found()
        if intro.status != IntroStatus.COMPLETED:
            raise bad_request("시작음이 아직 준비되지 않았어요.", "intro_not_ready")
    job = ExportJob(episode_id=ep.id, status=ExportStatus.RUNNING, options=body.model_dump(mode="json"))
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _filename(ep: Episode) -> str:
    base = ep.title or (ep.original_filename or "episode").rsplit(".", 1)[0]
    base = re.sub(r'[\\/:*?"<>|]+', " ", base).strip() or "episode"
    return f"{base[:80]}.mp3"


def download_url(db: Session, ep: Episode, export_id: uuid.UUID) -> str:
    job = db.get(ExportJob, export_id)
    if not job or job.episode_id != ep.id or job.status != ExportStatus.COMPLETED or not job.output_path:
        raise not_found()
    return get_storage().download_url(job.output_path, _filename(ep))


def delete(db: Session, ep: Episode, export_id: uuid.UUID) -> None:
    job = db.get(ExportJob, export_id)
    if not job or job.episode_id != ep.id:
        raise not_found()
    if job.status == ExportStatus.RUNNING:
        raise conflict("내보내는 중에는 지울 수 없어요.", "busy")
    if job.output_path:
        try:
            get_storage().delete_prefix(job.output_path)
        except Exception:  # noqa: BLE001
            log.warning("export file delete failed", exc_info=True)
    db.delete(job)
    db.commit()


def run(export_id: uuid.UUID) -> None:
    """BackgroundTasks에서 실행."""
    try:
        _run(export_id)
    except Exception as e:  # noqa: BLE001
        log.exception("export failed")
        with SessionLocal() as db:
            job = db.get(ExportJob, export_id)
            if job:
                job.status = ExportStatus.FAILED
                job.error_message = f"파일을 만들지 못했어요. ({type(e).__name__})"
                db.commit()


def _run(export_id: uuid.UUID) -> None:
    storage = get_storage()
    with SessionLocal() as db:
        job = db.get(ExportJob, export_id)
        if not job or job.status != ExportStatus.RUNNING:
            return
        ep = db.get(Episode, job.episode_id)
        opts = dict(job.options or {})
        cuts = [(c.start_time, c.end_time) for c in edit_service.list_cuts(db, ep.id)] if opts.get("apply_cuts") else []
        intro = db.get(IntroClip, uuid.UUID(opts["intro_id"])) if opts.get("intro_id") else None
        intro_path, intro_dur = (intro.path, intro.duration) if intro else (None, None)
        src_path, prefix = ep.original_path, episode_prefix(ep.user_id, ep.id)

    with tempfile.TemporaryDirectory(prefix="modu-sofa-export-") as tmp:
        work = Path(tmp)
        src = work / ("source" + Path(src_path).suffix)
        storage.download(src_path, src)
        intro_file = None
        if intro_path:
            intro_file = work / "intro.mp3"
            storage.download(intro_path, intro_file)
        out = work / "export.mp3"
        render_utils.render(
            src, out, cuts,
            enhance=bool(opts.get("enhance")),
            ai_denoise=bool(opts.get("ai_denoise")),
            intro=intro_file,
            intro_duration=intro_dur,
        )
        duration = ffmpeg_utils.probe(str(out)).duration
        dest = f"{prefix}/exports/{export_id}.mp3"
        storage.upload_file(dest, out, "audio/mpeg")
        size = out.stat().st_size

    with SessionLocal() as db:
        job = db.get(ExportJob, export_id)
        if not job:  # 그사이 에피소드가 삭제됨
            return
        job.status = ExportStatus.COMPLETED
        job.output_path = dest
        job.duration = duration
        job.file_size = size
        db.commit()
