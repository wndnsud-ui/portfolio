import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.core.config import reload_analysis_settings, settings
from app.db.session import get_db
from app.models import Episode
from app.routers.deps import owned_episode
from app.schemas.edit import (
    CutOut,
    CutsIn,
    DownloadOut,
    ExportCreate,
    ExportOut,
    IntroCreate,
    IntroOut,
    IntroPrompt,
)
from app.services import edit_service, export_service, intro_service

router = APIRouter(tags=["edits"])


# ───────── 자르기 ─────────
@router.get("/api/episodes/{episode_id}/cuts", response_model=list[CutOut])
def list_cuts(ep: Episode = Depends(owned_episode), db: Session = Depends(get_db)):
    return edit_service.list_cuts(db, ep.id)


@router.put("/api/episodes/{episode_id}/cuts", response_model=list[CutOut])
def replace_cuts(body: CutsIn, ep: Episode = Depends(owned_episode), db: Session = Depends(get_db)):
    return edit_service.replace_cuts(db, ep, [(c.start_time, c.end_time) for c in body.cuts])


# ───────── 내보내기 ─────────
@router.get("/api/episodes/{episode_id}/exports", response_model=list[ExportOut])
def list_exports(ep: Episode = Depends(owned_episode), db: Session = Depends(get_db)):
    return export_service.list_exports(db, ep)


@router.post("/api/episodes/{episode_id}/exports", response_model=ExportOut, status_code=status.HTTP_202_ACCEPTED)
def create_export(
    body: ExportCreate, bg: BackgroundTasks, ep: Episode = Depends(owned_episode), db: Session = Depends(get_db)
):
    job = export_service.create(db, ep, body)
    bg.add_task(export_service.run, job.id)
    return job


@router.get("/api/episodes/{episode_id}/exports/{export_id}/download", response_model=DownloadOut)
def download_export(export_id: uuid.UUID, ep: Episode = Depends(owned_episode), db: Session = Depends(get_db)):
    return DownloadOut(url=export_service.download_url(db, ep, export_id))


@router.delete("/api/episodes/{episode_id}/exports/{export_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_export(export_id: uuid.UUID, ep: Episode = Depends(owned_episode), db: Session = Depends(get_db)):
    export_service.delete(db, ep, export_id)


# ───────── AI 시작음 ─────────
@router.get("/api/episodes/{episode_id}/intro-prompt", response_model=IntroPrompt)
def intro_prompt(ep: Episode = Depends(owned_episode), db: Session = Depends(get_db)):
    reload_analysis_settings()
    return IntroPrompt(prompt=intro_service.suggest_prompt(db, ep), provider=settings.intro_provider)


@router.get("/api/intros", response_model=list[IntroOut])
def list_intros(db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    return intro_service.list_intros(db, user.id)


@router.post("/api/intros", response_model=IntroOut, status_code=status.HTTP_202_ACCEPTED)
def create_intro(
    body: IntroCreate, bg: BackgroundTasks, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)
):
    clip = intro_service.create(db, user.id, body)
    bg.add_task(intro_service.run, clip.id, body.seconds)
    return clip


@router.delete("/api/intros/{intro_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_intro(intro_id: uuid.UUID, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    intro_service.delete(db, user.id, intro_id)
