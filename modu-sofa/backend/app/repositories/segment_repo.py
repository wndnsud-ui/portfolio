import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import Episode, TranscriptSegment


def list_for_episode(db: Session, episode_id: uuid.UUID) -> list[TranscriptSegment]:
    return list(
        db.scalars(
            select(TranscriptSegment)
            .where(TranscriptSegment.episode_id == episode_id)
            .order_by(TranscriptSegment.seq)
        )
    )


def get_owned(db: Session, segment_id: uuid.UUID, user_id: uuid.UUID) -> TranscriptSegment | None:
    return db.scalar(
        select(TranscriptSegment)
        .join(Episode, Episode.id == TranscriptSegment.episode_id)
        .where(TranscriptSegment.id == segment_id, Episode.user_id == user_id)
    )


def count_edited(db: Session, episode_id: uuid.UUID) -> int:
    return db.scalar(
        select(func.count())
        .select_from(TranscriptSegment)
        .where(TranscriptSegment.episode_id == episode_id, TranscriptSegment.edited_text.is_not(None))
    ) or 0


def count_deleted(db: Session, episode_id: uuid.UUID) -> int:
    return db.scalar(
        select(func.count())
        .select_from(TranscriptSegment)
        .where(TranscriptSegment.episode_id == episode_id, TranscriptSegment.is_deleted.is_(True))
    ) or 0


def delete_for_episode(db: Session, episode_id: uuid.UUID) -> None:
    db.execute(delete(TranscriptSegment).where(TranscriptSegment.episode_id == episode_id))
