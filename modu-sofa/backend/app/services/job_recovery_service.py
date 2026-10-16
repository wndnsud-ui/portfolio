"""서버 시작 시 멈춘 작업 정리.

status ∈ {processing, transcribing} 또는 ai_status = running 인 Episode를 failed로 바꾸고 단계와 사유를 기록한다.
"""

import logging

from sqlalchemy import select

from app.core.errors import MSG_SERVER_RESTART
from app.db.session import SessionLocal
from app.models import (
    AiStatus,
    Episode,
    EpisodeStatus,
    ErrorStage,
    ExportJob,
    ExportStatus,
    IntroClip,
    IntroStatus,
)
from app.models.base import utcnow

log = logging.getLogger(__name__)


def recover_stuck_jobs() -> int:
    n = 0
    with SessionLocal() as db:
        rows = db.scalars(
            select(Episode).where(
                (Episode.status.in_([EpisodeStatus.PROCESSING, EpisodeStatus.TRANSCRIBING]))
                | (Episode.ai_status == AiStatus.RUNNING)
            )
        ).all()
        for ep in rows:
            if ep.status in (EpisodeStatus.PROCESSING, EpisodeStatus.TRANSCRIBING):
                ep.error_stage = (
                    ErrorStage.PROCESSING if ep.status == EpisodeStatus.PROCESSING else ErrorStage.TRANSCRIPTION
                )
                ep.status = EpisodeStatus.FAILED
            else:
                ep.ai_status = AiStatus.FAILED
                ep.error_stage = ErrorStage.AI
            ep.error_message = MSG_SERVER_RESTART
            ep.status_updated_at = utcnow()
            n += 1
        for job in db.scalars(select(ExportJob).where(ExportJob.status == ExportStatus.RUNNING)):
            job.status = ExportStatus.FAILED
            job.error_message = MSG_SERVER_RESTART
            n += 1
        for clip in db.scalars(select(IntroClip).where(IntroClip.status == IntroStatus.RUNNING)):
            clip.status = IntroStatus.FAILED
            clip.error_message = MSG_SERVER_RESTART
            n += 1
        db.commit()
    if n:
        log.warning("recovered %s stuck job(s)", n)
    return n
