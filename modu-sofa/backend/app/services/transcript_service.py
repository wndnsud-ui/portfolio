from sqlalchemy.orm import Session

from app.core.errors import MSG_CANCELLED, bad_request, conflict
from app.models import AiStatus, Episode, EpisodeStatus, ErrorStage, TranscriptSegment
from app.repositories import ai_repo, episode_repo, segment_repo, speaker_repo
from app.schemas.transcript import SegmentUpdate, TranscriptOut
from app.services import job_control, speaker_merge_service

REANALYZABLE = {EpisodeStatus.UPLOADED, EpisodeStatus.FAILED, EpisodeStatus.TRANSCRIBED}


def get_transcript(db: Session, ep: Episode) -> TranscriptOut:
    return TranscriptOut(
        segments=segment_repo.list_for_episode(db, ep.id),
        speakers=speaker_merge_service.list_speakers(db, ep).speakers,
        edited_count=segment_repo.count_edited(db, ep.id),
        deleted_count=segment_repo.count_deleted(db, ep.id),
        named_speaker_count=speaker_repo.named_count(db, ep.id),
        merge_count=speaker_repo.merge_count(db, ep.id),
    )


def update_segment(db: Session, seg: TranscriptSegment, body: SegmentUpdate) -> TranscriptSegment:
    fields = body.model_fields_set
    if "edited_text" in fields and body.edited_text is not None:
        text = body.edited_text.strip()
        if not text:
            raise bad_request("빈 문장은 저장할 수 없어요. 문장을 지우려면 삭제를 사용하세요.", "empty_text")
        # 원문과 같으면 수정본을 두지 않는다. original_text는 절대 바꾸지 않는다.
        seg.edited_text = None if text == seg.original_text else text
    if "speaker_id" in fields and body.speaker_id is not None:
        if speaker_repo.get_in_episode(db, body.speaker_id, seg.episode_id) is None:
            raise bad_request("이 에피소드에 없는 화자예요.", "invalid_speaker")
        seg.speaker_id = body.speaker_id
    db.commit()
    db.refresh(seg)
    return seg


def revert_segment(db: Session, seg: TranscriptSegment) -> TranscriptSegment:
    seg.edited_text = None
    db.commit()
    db.refresh(seg)
    return seg


def set_deleted(db: Session, seg: TranscriptSegment, deleted: bool) -> TranscriptSegment:
    seg.is_deleted = deleted
    db.commit()
    db.refresh(seg)
    return seg


def start_reanalysis(db: Session, ep: Episode) -> None:
    if ep.ai_status == AiStatus.RUNNING:
        raise conflict("AI 분석이 끝난 뒤 다시 시도해 주세요.", "busy")
    if not ep.original_path:
        raise conflict("업로드된 파일이 없어요.", "no_file")
    if ep.status == EpisodeStatus.FAILED and ep.error_stage == "upload":
        raise conflict("파일을 다시 올려 주세요.", "upload_failed")
    if not episode_repo.claim(db, ep.id, EpisodeStatus.PROCESSING, REANALYZABLE):
        raise conflict("이미 분석이 진행 중이에요.", "busy")


def cancel_analysis(db: Session, ep: Episode) -> None:
    """진행 중인 분석을 취소한다. 화면 상태는 즉시 바뀌고, 백그라운드 작업은 다음 확인 지점에서 멈춘다.

    - 음성 분석 중: 기존 대본이 있으면(재분석) 그대로 되돌리고, 없으면 failed + "분석을 취소했어요."
    - AI 분석 중: 이전 결과가 있으면 completed, 없으면 none
    """
    if ep.status in (EpisodeStatus.PROCESSING, EpisodeStatus.TRANSCRIBING):
        job_control.cancel_stt(ep.id)
        if segment_repo.list_for_episode(db, ep.id):
            episode_repo.set_status(db, ep, EpisodeStatus.TRANSCRIBED, error_stage=None, error_message=None,
                                    progress_current=0, progress_total=0)
        else:
            stage = ErrorStage.PROCESSING if ep.status == EpisodeStatus.PROCESSING else ErrorStage.TRANSCRIPTION
            episode_repo.set_status(db, ep, EpisodeStatus.FAILED, error_stage=stage, error_message=MSG_CANCELLED)
        return
    if ep.ai_status == AiStatus.RUNNING:
        job_control.cancel_ai(ep.id)
        ep.ai_status = AiStatus.COMPLETED if ai_repo.get_result(db, ep.id) else AiStatus.NONE
        db.commit()
        return
    raise conflict("진행 중인 분석이 없어요.", "not_running")
