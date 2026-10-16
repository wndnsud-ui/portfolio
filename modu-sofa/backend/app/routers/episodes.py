from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.db.session import get_db
from app.models import Episode
from app.routers.deps import owned_episode
from app.schemas.episode import EpisodeCreate, EpisodeDetail, EpisodeOut, EpisodeUpdate
from app.services import episode_service

router = APIRouter(prefix="/api/episodes", tags=["episodes"])


@router.post("", response_model=EpisodeOut, status_code=status.HTTP_201_CREATED)
def create_episode(
    body: EpisodeCreate, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)
):
    return episode_service.to_out(episode_service.create(db, user.id, body))


@router.get("", response_model=list[EpisodeOut])
def list_episodes(db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    return episode_service.list_out(db, user.id)


@router.get("/{episode_id}", response_model=EpisodeDetail)
def get_episode(ep: Episode = Depends(owned_episode), db: Session = Depends(get_db)):
    return episode_service.detail(db, ep)


@router.patch("/{episode_id}", response_model=EpisodeOut)
def update_episode(body: EpisodeUpdate, ep: Episode = Depends(owned_episode), db: Session = Depends(get_db)):
    return episode_service.to_out(episode_service.update(db, ep, body))


@router.delete("/{episode_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_episode(ep: Episode = Depends(owned_episode), db: Session = Depends(get_db)):
    episode_service.delete(db, ep)
