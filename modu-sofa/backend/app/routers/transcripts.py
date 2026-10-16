import uuid

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.core.errors import not_found
from app.db.session import get_db
from app.models import Episode, TranscriptSegment
from app.repositories import segment_repo
from app.routers.deps import owned_episode
from app.schemas.episode import JobAccepted
from app.schemas.transcript import SegmentOut, SegmentUpdate, TranscriptOut
from app.services import transcript_service, transcription_service

router = APIRouter(tags=["transcripts"])


def owned_segment(
    segment_id: uuid.UUID, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)
) -> TranscriptSegment:
    seg = segment_repo.get_owned(db, segment_id, user.id)
    if seg is None:
        raise not_found()
    return seg


@router.post("/api/episodes/{episode_id}/transcribe", response_model=JobAccepted)
def reanalyze(bg: BackgroundTasks, ep: Episode = Depends(owned_episode), db: Session = Depends(get_db)):
    transcript_service.start_reanalysis(db, ep)
    bg.add_task(transcription_service.run_pipeline, ep.id)
    db.refresh(ep)
    return JobAccepted(episode_id=ep.id, status=ep.status, ai_status=ep.ai_status)


@router.post("/api/episodes/{episode_id}/cancel", response_model=JobAccepted)
def cancel(ep: Episode = Depends(owned_episode), db: Session = Depends(get_db)):
    transcript_service.cancel_analysis(db, ep)
    db.refresh(ep)
    return JobAccepted(episode_id=ep.id, status=ep.status, ai_status=ep.ai_status)


@router.get("/api/episodes/{episode_id}/transcript", response_model=TranscriptOut)
def get_transcript(ep: Episode = Depends(owned_episode), db: Session = Depends(get_db)):
    return transcript_service.get_transcript(db, ep)


@router.patch("/api/transcripts/{segment_id}", response_model=SegmentOut)
def update_segment(body: SegmentUpdate, seg: TranscriptSegment = Depends(owned_segment), db: Session = Depends(get_db)):
    return transcript_service.update_segment(db, seg, body)


@router.post("/api/transcripts/{segment_id}/revert", response_model=SegmentOut)
def revert_segment(seg: TranscriptSegment = Depends(owned_segment), db: Session = Depends(get_db)):
    return transcript_service.revert_segment(db, seg)


@router.delete("/api/transcripts/{segment_id}", response_model=SegmentOut)
def delete_segment(seg: TranscriptSegment = Depends(owned_segment), db: Session = Depends(get_db)):
    return transcript_service.set_deleted(db, seg, True)


@router.post("/api/transcripts/{segment_id}/restore", response_model=SegmentOut)
def restore_segment(seg: TranscriptSegment = Depends(owned_segment), db: Session = Depends(get_db)):
    return transcript_service.set_deleted(db, seg, False)
