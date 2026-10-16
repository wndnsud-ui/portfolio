import uuid

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.core.errors import not_found
from app.db.session import get_db
from app.models import Episode
from app.repositories import episode_repo


def owned_episode(
    episode_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> Episode:
    ep = episode_repo.get_owned(db, episode_id, user.id)
    if ep is None:
        raise not_found()
    return ep
