from sqlalchemy.orm import Session

from app.core.errors import conflict
from app.models import AiStatus, Episode, EpisodeStatus
from app.repositories import ai_repo, episode_repo
from app.schemas.ai import AiOut, ChapterOut, HighlightOut


def get_ai(db: Session, ep: Episode) -> AiOut:
    res = ai_repo.get_result(db, ep.id)
    out = AiOut(
        ai_status=ep.ai_status,
        error_message=ep.error_message if ep.error_stage == "ai" else None,
        chapters=[ChapterOut.model_validate(c) for c in ai_repo.list_chapters(db, ep.id)],
        highlights=[HighlightOut.model_validate(h) for h in ai_repo.list_highlights(db, ep.id)],
    )
    if res:
        out.summary = res.summary
        out.keywords = list(res.keywords or [])
        out.title_candidates = list(res.title_candidates or [])
        out.model = res.model
    return out


def start(db: Session, ep: Episode) -> None:
    if ep.status != EpisodeStatus.TRANSCRIBED:
        raise conflict("Transcript가 만들어진 뒤에 AI 분석을 실행할 수 있어요.", "not_transcribed")
    if ep.ai_status == AiStatus.RUNNING or not episode_repo.claim_ai(db, ep.id):
        raise conflict("AI 분석이 이미 진행 중이에요.", "busy")


def select_title(db: Session, ep: Episode, title: str) -> Episode:
    ep.title = title.strip()
    db.commit()
    db.refresh(ep)
    return ep
