"""업로드 검증과 FFmpeg 전처리 (재생용 CBR 파일, peaks, STT 청크)."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.core.errors import (
    MSG_TOO_LARGE,
    MSG_TOO_LONG,
    MSG_UNPLAYABLE,
    MSG_UNSUPPORTED_FORMAT,
    UserFacingError,
)
from app.services.storage_service import StorageBackend
from app.utils import ffmpeg_utils

log = logging.getLogger(__name__)

ALLOWED_EXT = {"mp3", "wav", "m4a"}
CONTENT_TYPES = {"mp3": "audio/mpeg", "wav": "audio/wav", "m4a": "audio/mp4"}
# ffprobe format_name 기준 허용 컨테이너
ALLOWED_FORMATS = {"mp3": ("mp3",), "wav": ("wav",), "m4a": ("mov", "mp4", "m4a")}


def ext_of(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def validate_request(filename: str, size: int) -> str:
    """브라우저 1차 검증과 같은 규칙을 서버에서 다시 확인한다. 확장자를 반환."""
    ext = ext_of(filename)
    if ext not in ALLOWED_EXT:
        raise UserFacingError(MSG_UNSUPPORTED_FORMAT, "unsupported_format")
    if size <= 0:
        raise UserFacingError(MSG_UNPLAYABLE, "unplayable")
    if size > settings.max_upload_bytes:
        raise UserFacingError(MSG_TOO_LARGE, "too_large")
    return ext


@dataclass
class ValidatedAudio:
    duration: float
    size: int


def validate_uploaded(storage: StorageBackend, path: str, ext: str) -> ValidatedAudio:
    """ffprobe로 실제 형식·길이·재생 가능 여부를 확인한다."""
    size = storage.size(path)
    if size is None:
        raise UserFacingError("업로드된 파일을 찾을 수 없어요. 다시 올려 주세요.", "not_uploaded")
    if size > settings.max_upload_bytes:
        raise UserFacingError(MSG_TOO_LARGE, "too_large")

    src = storage.probe_source(path)
    try:
        info = ffmpeg_utils.probe(src)
    except ffmpeg_utils.FFmpegError as e:
        log.info("probe failed: %s", e)
        raise UserFacingError(MSG_UNPLAYABLE, "unplayable") from e

    formats = info.format_name.split(",")
    if info.has_video or not any(f in formats for f in ALLOWED_FORMATS[ext]):
        raise UserFacingError(MSG_UNSUPPORTED_FORMAT, "unsupported_format")
    if not info.has_audio or info.duration <= 0:
        raise UserFacingError(MSG_UNPLAYABLE, "unplayable")
    if info.duration > settings.MAX_DURATION_SEC:
        raise UserFacingError(MSG_TOO_LONG, "too_long")
    if not ffmpeg_utils.can_decode(src):
        raise UserFacingError(MSG_UNPLAYABLE, "unplayable")
    return ValidatedAudio(duration=info.duration, size=size)


@dataclass
class ChunkFile:
    index: int
    offset: float
    length: float
    path: Path


@dataclass
class Preprocessed:
    playback_path: str
    peaks_path: str
    duration: float
    chunks: list[ChunkFile]


def preprocess(storage: StorageBackend, prefix: str, original_path: str, workdir: Path) -> Preprocessed:
    src = workdir / Path(original_path).name
    storage.download(original_path, src)

    playback = workdir / "playback.mp3"
    ffmpeg_utils.to_playback_mp3(src, playback)
    # 재생용 파일 기준으로 duration을 다시 잰다.
    duration = ffmpeg_utils.probe(str(playback)).duration
    storage.upload_file(f"{prefix}/playback.mp3", playback, "audio/mpeg")

    peaks = ffmpeg_utils.compute_peaks(playback, points_per_sec=25)
    peaks_doc = {"version": 1, "points_per_sec": 25, "duration": duration, "data": peaks}
    storage.upload_bytes(
        f"{prefix}/peaks.json", json.dumps(peaks_doc, separators=(",", ":")).encode(), "application/json"
    )

    chunks: list[ChunkFile] = []
    plan = ffmpeg_utils.chunk_plan(duration, settings.STT_CHUNK_SEC, settings.STT_OVERLAP_SEC)
    for i, (offset, length) in enumerate(plan):
        out = workdir / f"chunk_{i:02d}.mp3"
        # 청크는 재생용 파일에서 자른다 → 재생 시각과 STT 시각의 기준이 같다.
        ffmpeg_utils.make_stt_chunk(playback, out, offset, length)
        storage.upload_file(f"{prefix}/chunks/chunk_{i:02d}.mp3", out, "audio/mpeg")
        chunks.append(ChunkFile(index=i, offset=offset, length=length, path=out))

    return Preprocessed(
        playback_path=f"{prefix}/playback.mp3",
        peaks_path=f"{prefix}/peaks.json",
        duration=duration,
        chunks=chunks,
    )
