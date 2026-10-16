import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import AiResult, Chapter, Highlight


def get_result(db: Session, episode_id: uuid.UUID) -> AiResult | None:
    return db.scalar(select(AiResult).where(AiResult.episode_id == episode_id))


def list_chapters(db: Session, episode_id: uuid.UUID) -> list[Chapter]:
    return list(db.scalars(select(Chapter).where(Chapter.episode_id == episode_id).order_by(Chapter.seq)))


def list_highlights(db: Session, episode_id: uuid.UUID) -> list[Highlight]:
    return list(db.scalars(select(Highlight).where(Highlight.episode_id == episode_id).order_by(Highlight.seq)))


def delete_for_episode(db: Session, episode_id: uuid.UUID) -> None:
    db.execute(delete(Highlight).where(Highlight.episode_id == episode_id))
    db.execute(delete(Chapter).where(Chapter.episode_id == episode_id))
    db.execute(delete(AiResult).where(AiResult.episode_id == episode_id))
