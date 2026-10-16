import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.core.errors import not_found
from app.db.session import get_db
from app.models import Episode
from app.repositories import speaker_repo
from app.routers.deps import owned_episode
from app.schemas.speaker import SpeakerMergeRequest, SpeakersOut, SpeakerUpdate
from app.services import speaker_merge_service

router = APIRouter(tags=["speakers"])


@router.get("/api/episodes/{episode_id}/speakers", response_model=SpeakersOut)
def list_speakers(ep: Episode = Depends(owned_episode), db: Session = Depends(get_db)):
    return speaker_merge_service.list_speakers(db, ep)


@router.patch("/api/speakers/{speaker_id}", response_model=SpeakersOut)
def update_speaker(
    speaker_id: uuid.UUID,
    body: SpeakerUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    sp = speaker_repo.get_owned(db, speaker_id, user.id)
    if sp is None:
        raise not_found()
    ep = speaker_merge_service.update_speaker(db, sp, body)
    return speaker_merge_service.list_speakers(db, ep)


@router.post("/api/episodes/{episode_id}/speakers/merge", response_model=SpeakersOut)
def merge_speakers(body: SpeakerMergeRequest, ep: Episode = Depends(owned_episode), db: Session = Depends(get_db)):
    speaker_merge_service.merge(db, ep, body.from_id, body.into_id)
    return speaker_merge_service.list_speakers(db, ep)


@router.post("/api/episodes/{episode_id}/speakers/merge/undo", response_model=SpeakersOut)
def undo_merge(ep: Episode = Depends(owned_episode), db: Session = Depends(get_db)):
    speaker_merge_service.undo_last(db, ep)
    return speaker_merge_service.list_speakers(db, ep)
