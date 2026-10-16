from sqlalchemy.orm import Session

from app.core.errors import UserFacingError, bad_request, conflict
from app.models import Episode, EpisodeStatus, ErrorStage
from app.repositories import episode_repo
from app.schemas.episode import UploadUrlRequest, UploadUrlResponse
from app.services import audio_service
from app.services.storage_service import episode_prefix, get_storage

UPLOADABLE = {EpisodeStatus.CREATED, EpisodeStatus.UPLOADING}


def _can_upload(ep: Episode) -> bool:
    return ep.status in UPLOADABLE or (ep.status == EpisodeStatus.FAILED and ep.error_stage == ErrorStage.UPLOAD)


def create_upload_url(db: Session, ep: Episode, body: UploadUrlRequest) -> UploadUrlResponse:
    if not _can_upload(ep):
        raise conflict("이미 파일이 올라간 에피소드예요.", "already_uploaded")
    try:
        ext = audio_service.validate_request(body.filename, body.size)
    except UserFacingError as e:
        raise bad_request(e.message, e.code) from e

    path = f"{episode_prefix(ep.user_id, ep.id)}/original.{ext}"
    signed = get_storage().create_signed_upload(path, audio_service.CONTENT_TYPES[ext])
    ep.original_path = path
    ep.original_filename = body.filename[:255]
    ep.file_size = body.size
    episode_repo.set_status(db, ep, EpisodeStatus.UPLOADING, error_stage=None, error_message=None)
    return UploadUrlResponse(upload_url=signed.url, method=signed.method, headers=signed.headers, path=path)


def complete_upload(db: Session, ep: Episode) -> None:
    """ffprobe 검증 → status = uploaded. 실패하면 error_stage = upload 로 기록하고 400."""
    if ep.status != EpisodeStatus.UPLOADING or not ep.original_path:
        raise conflict("업로드를 먼저 시작해 주세요.", "not_uploading")
    ext = audio_service.ext_of(ep.original_path)
    storage = get_storage()
    try:
        info = audio_service.validate_uploaded(storage, ep.original_path, ext)
    except UserFacingError as e:
        episode_repo.set_status(db, ep, EpisodeStatus.FAILED, error_stage=ErrorStage.UPLOAD, error_message=e.message)
        try:
            storage.delete_prefix(ep.original_path)
        except Exception:  # noqa: BLE001
            pass
        raise bad_request(e.message, e.code) from e

    ep.duration = info.duration
    ep.file_size = info.size
    episode_repo.set_status(db, ep, EpisodeStatus.UPLOADED, error_stage=None, error_message=None)
