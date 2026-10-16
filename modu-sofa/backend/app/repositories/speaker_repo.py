import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import Episode, EpisodeSpeaker, SpeakerMerge, TranscriptSegment


def list_for_episode(db: Session, episode_id: uuid.UUID) -> list[EpisodeSpeaker]:
    return list(
        db.scalars(
            select(EpisodeSpeaker)
            .where(EpisodeSpeaker.episode_id == episode_id)
            .order_by(EpisodeSpeaker.speaker_code)
        )
    )


def get_owned(db: Session, speaker_id: uuid.UUID, user_id: uuid.UUID) -> EpisodeSpeaker | None:
    return db.scalar(
        select(EpisodeSpeaker)
        .join(Episode, Episode.id == EpisodeSpeaker.episode_id)
        .where(EpisodeSpeaker.id == speaker_id, Episode.user_id == user_id)
    )


def get_in_episode(db: Session, speaker_id: uuid.UUID, episode_id: uuid.UUID) -> EpisodeSpeaker | None:
    return db.scalar(
        select(EpisodeSpeaker).where(EpisodeSpeaker.id == speaker_id, EpisodeSpeaker.episode_id == episode_id)
    )


def stats(db: Session, episode_id: uuid.UUID) -> dict[uuid.UUID, dict]:
    """화자별 문장 수(삭제 제외)와 대표 구간(가장 긴 Segment)."""
    out: dict[uuid.UUID, dict] = {}
    rows = db.execute(
        select(TranscriptSegment.speaker_id, func.count())
        .where(TranscriptSegment.episode_id == episode_id, TranscriptSegment.is_deleted.is_(False))
        .group_by(TranscriptSegment.speaker_id)
    )
    for sid, n in rows:
        out[sid] = {"count": n, "sample": None}

    segs = db.execute(
        select(
            TranscriptSegment.speaker_id,
            TranscriptSegment.start_time,
            TranscriptSegment.end_time,
        ).where(TranscriptSegment.episode_id == episode_id, TranscriptSegment.is_deleted.is_(False))
    )
    best: dict[uuid.UUID, tuple[float, float]] = {}
    first: dict[uuid.UUID, float] = {}
    for sid, st, en in segs:
        if sid not in first or st < first[sid]:
            first[sid] = st
        cur = best.get(sid)
        if cur is None or (en - st) > (cur[1] - cur[0]):
            best[sid] = (st, en)
    for sid, rng in best.items():
        out.setdefault(sid, {"count": 0, "sample": None})["sample"] = rng
    for sid, st in first.items():
        out[sid]["first_start"] = st
    return out


def last_merge(db: Session, episode_id: uuid.UUID) -> SpeakerMerge | None:
    return db.scalar(
        select(SpeakerMerge).where(SpeakerMerge.episode_id == episode_id).order_by(SpeakerMerge.created_at.desc())
    )


def merge_count(db: Session, episode_id: uuid.UUID) -> int:
    return db.scalar(select(func.count()).select_from(SpeakerMerge).where(SpeakerMerge.episode_id == episode_id)) or 0


def named_count(db: Session, episode_id: uuid.UUID) -> int:
    return db.scalar(
        select(func.count())
        .select_from(EpisodeSpeaker)
        .where(EpisodeSpeaker.episode_id == episode_id, EpisodeSpeaker.display_name.is_not(None))
    ) or 0


def delete_for_episode(db: Session, episode_id: uuid.UUID) -> None:
    db.execute(delete(SpeakerMerge).where(SpeakerMerge.episode_id == episode_id))
    db.execute(delete(EpisodeSpeaker).where(EpisodeSpeaker.episode_id == episode_id))
