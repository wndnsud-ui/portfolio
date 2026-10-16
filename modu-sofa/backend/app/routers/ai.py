from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Episode
from app.routers.deps import owned_episode
from app.schemas.ai import AiOut, TitleSelect
from app.schemas.episode import EpisodeOut, JobAccepted
from app.services import ai_service, episode_service, summary_service

router = APIRouter(prefix="/api/episodes", tags=["ai"])


@router.post("/{episode_id}/ai/analyze", response_model=JobAccepted)
def analyze(bg: BackgroundTasks, ep: Episode = Depends(owned_episode), db: Session = Depends(get_db)):
    ai_service.start(db, ep)
    bg.add_task(summary_service.run_analysis, ep.id)
    db.refresh(ep)
    return JobAccepted(episode_id=ep.id, status=ep.status, ai_status=ep.ai_status)


@router.get("/{episode_id}/ai", response_model=AiOut)
def get_ai(ep: Episode = Depends(owned_episode), db: Session = Depends(get_db)):
    return ai_service.get_ai(db, ep)


@router.post("/{episode_id}/ai/title", response_model=EpisodeOut)
def select_title(body: TitleSelect, ep: Episode = Depends(owned_episode), db: Session = Depends(get_db)):
    return episode_service.to_out(ai_service.select_title(db, ep, body.title))
