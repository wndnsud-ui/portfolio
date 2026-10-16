from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Episode, EpisodeStatus
from app.repositories import episode_repo
from app.routers.deps import owned_episode
from app.schemas.episode import JobAccepted, UploadUrlRequest, UploadUrlResponse
from app.services import transcription_service, upload_service

router = APIRouter(prefix="/api/episodes", tags=["uploads"])


@router.post("/{episode_id}/upload-url", response_model=UploadUrlResponse)
def create_upload_url(body: UploadUrlRequest, ep: Episode = Depends(owned_episode), db: Session = Depends(get_db)):
    return upload_service.create_upload_url(db, ep, body)


@router.post("/{episode_id}/upload-complete", response_model=JobAccepted)
def upload_complete(bg: BackgroundTasks, ep: Episode = Depends(owned_episode), db: Session = Depends(get_db)):
    upload_service.complete_upload(db, ep)
    if episode_repo.claim(db, ep.id, EpisodeStatus.PROCESSING, [EpisodeStatus.UPLOADED]):
        bg.add_task(transcription_service.run_pipeline, ep.id)
    db.refresh(ep)
    return JobAccepted(episode_id=ep.id, status=ep.status, ai_status=ep.ai_status)
