import uuid
from collections.abc import Iterable

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import Chapter, Episode, EpisodeSpeaker, Highlight
from app.models.base import utcnow


def get_owned(db: Session, episode_id: uuid.UUID, user_id: uuid.UUID) -> Episode | None:
    return db.scalar(select(Episode).where(Episode.id == episode_id, Episode.user_id == user_id))


def get(db: Session, episode_id: uuid.UUID) -> Episode | None:
    return db.get(Episode, episode_id)


def list_owned(db: Session, user_id: uuid.UUID) -> list[Episode]:
    return list(db.scalars(select(Episode).where(Episode.user_id == user_id).order_by(Episode.created_at.desc())))


def counts_for(db: Session, episode_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, dict[str, int]]:
    ids = list(episode_ids)
    out: dict[uuid.UUID, dict[str, int]] = {i: {"speakers": 0, "chapters": 0, "highlights": 0} for i in ids}
    if not ids:
        return out
    for model, key in ((EpisodeSpeaker, "speakers"), (Chapter, "chapters"), (Highlight, "highlights")):
        rows = db.execute(
            select(model.episode_id, func.count()).where(model.episode_id.in_(ids)).group_by(model.episode_id)
        )
        for eid, n in rows:
            out[eid][key] = n
    return out


def set_status(db: Session, ep: Episode, status: str, **fields) -> None:
    ep.status = status
    ep.status_updated_at = utcnow()
    for k, v in fields.items():
        setattr(ep, k, v)
    db.commit()


def claim(db: Session, episode_id: uuid.UUID, to_status: str, from_statuses: Iterable[str]) -> bool:
    """조건부 UPDATE로 작업을 선점한다. 반환 행이 없으면 이미 다른 작업이 진행 중이다."""
    res = db.execute(
        update(Episode)
        .where(Episode.id == episode_id, Episode.status.in_(list(from_statuses)))
        .values(
            status=to_status,
            status_updated_at=utcnow(),
            error_stage=None,
            error_message=None,
            progress_current=0,
            progress_total=0,
        )
        .returning(Episode.id)
    )
    row = res.first()
    db.commit()
    return row is not None


def claim_ai(db: Session, episode_id: uuid.UUID) -> bool:
    res = db.execute(
        update(Episode)
        .where(Episode.id == episode_id, Episode.status == "transcribed", Episode.ai_status != "running")
        .values(ai_status="running", status_updated_at=utcnow(), error_stage=None, error_message=None)
        .returning(Episode.id)
    )
    row = res.first()
    db.commit()
    return row is not None
