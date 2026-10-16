import logging
import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import bad_request, conflict
from app.models import AiStatus, Episode, EpisodeStatus, ErrorStage
from app.repositories import episode_repo
from app.schemas.episode import (
    EpisodeCounts,
    EpisodeCreate,
    EpisodeDetail,
    EpisodeOut,
    EpisodeUpdate,
)
from app.services.storage_service import episode_prefix, get_storage

log = logging.getLogger(__name__)

BUSY_STATUSES = {EpisodeStatus.PROCESSING, EpisodeStatus.TRANSCRIBING}


def create(db: Session, user_id: uuid.UUID, body: EpisodeCreate) -> Episode:
    ep = Episode(
        user_id=user_id,
        title=(body.title or "").strip() or None,
        description=body.description,
        status=EpisodeStatus.CREATED,
        ai_status=AiStatus.NONE,
    )
    db.add(ep)
    db.commit()
    db.refresh(ep)
    return ep


def to_out(ep: Episode, counts: dict | None = None) -> EpisodeOut:
    out = EpisodeOut.model_validate(ep)
    if counts is not None:
        out.counts = EpisodeCounts(**counts)
    return out


def list_out(db: Session, user_id: uuid.UUID) -> list[EpisodeOut]:
    eps = episode_repo.list_owned(db, user_id)
    counts = episode_repo.counts_for(db, [e.id for e in eps])
    return [to_out(e, counts.get(e.id)) for e in eps]


def detail(db: Session, ep: Episode) -> EpisodeDetail:
    counts = episode_repo.counts_for(db, [ep.id])[ep.id]
    out = EpisodeDetail(
        **to_out(ep, counts).model_dump(),
        stt_chunk_sec=settings.STT_CHUNK_SEC,
        stt_overlap_sec=settings.STT_OVERLAP_SEC,
    )
    storage = get_storage()
    try:
        if ep.playback_path:
            out.playback_url = storage.signed_url(ep.playback_path)
        if ep.peaks_path:
            out.peaks_url = storage.signed_url(ep.peaks_path)
    except Exception:  # noqa: BLE001
        log.warning("failed to sign urls", exc_info=True)
    return out


def update(db: Session, ep: Episode, body: EpisodeUpdate) -> Episode:
    fields = body.model_fields_set
    if "title" in fields:
        ep.title = (body.title or "").strip() or None
    if "description" in fields:
        ep.description = body.description
    db.commit()
    db.refresh(ep)
    return ep


def delete(db: Session, ep: Episode) -> None:
    if ep.status in BUSY_STATUSES or ep.ai_status == AiStatus.RUNNING:
        raise conflict("분석 중에는 삭제할 수 없어요. 끝난 뒤 다시 시도해 주세요.", "busy")
    prefix = episode_prefix(ep.user_id, ep.id)
    try:
        get_storage().delete_prefix(prefix)
    except Exception:  # noqa: BLE001
        log.exception("storage delete failed for %s", prefix)
        raise bad_request("저장된 파일을 지우지 못했어요. 잠시 후 다시 시도해 주세요.", "storage_delete_failed")
    db.delete(ep)
    db.commit()


def mark_upload_failed(db: Session, ep: Episode, message: str) -> None:
    episode_repo.set_status(db, ep, EpisodeStatus.FAILED, error_stage=ErrorStage.UPLOAD, error_message=message)
