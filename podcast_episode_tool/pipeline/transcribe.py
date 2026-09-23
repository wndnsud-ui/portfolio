from __future__ import annotations

import re
import math
import tempfile
from pathlib import Path
from typing import Callable

from .media import ffprobe_duration, run_command
from .models import Segment, Transcript

TIMECODE_RE = re.compile(
    r"^\s*(?:\[(?P<a>\d{1,2}:\d{2}(?::\d{2})?)\]|\(? (?P<b>\d{1,2}:\d{2}(?::\d{2})?) \)?|(?P<c>\d{1,2}:\d{2}(?::\d{2})?))\s*(?P<text>.*)$",
    re.VERBOSE,
)


def parse_timecode(value: str) -> float:
    parts = [int(part) for part in value.split(":")]
    if len(parts) == 2:
        minute, second = parts
        return minute * 60 + second
    hour, minute, second = parts
    return hour * 3600 + minute * 60 + second


def parse_timed_text(source_name: str, text: str) -> Transcript:
    rows: list[tuple[float, str]] = []
    for line in text.splitlines():
        match = TIMECODE_RE.match(line)
        if not match:
            continue
        stamp = match.group("a") or match.group("b") or match.group("c")
        body = match.group("text").strip(" -\t")
        if body:
            rows.append((parse_timecode(stamp), body))
    if not rows:
        raise ValueError("시간 표시가 있는 줄을 찾지 못했습니다. 예: [00:12] 발화문")
    for idx in range(1, len(rows)):
        if rows[idx][0] < rows[idx - 1][0]:
            raise ValueError("타임코드가 역순입니다.")
    segments: list[Segment] = []
    for idx, (start, body) in enumerate(rows):
        next_start = rows[idx + 1][0] if idx + 1 < len(rows) else start + 30
        end = max(start + 1, next_start)
        segments.append(Segment(start=start, end=end, text=body))
    return Transcript(source_name=source_name, duration=segments[-1].end, segments=segments)


MAX_DIRECT_UPLOAD_BYTES = 24_000_000
CHUNK_SECONDS = 40 * 60


def _transcribe_file(client, path: Path, model: str) -> tuple[list[Segment], float | None]:
    with path.open("rb") as audio:
        if model == "whisper-1":
            result = client.audio.transcriptions.create(
                model=model,
                file=audio,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )
        else:
            result = client.audio.transcriptions.create(
                model=model,
                file=audio,
                response_format="json",
            )
    raw_segments = getattr(result, "segments", None) or []
    segments = [
        Segment(start=float(s.start), end=float(s.end), text=s.text.strip())
        for s in raw_segments
        if getattr(s, "text", "").strip()
    ]
    result_duration = getattr(result, "duration", None)
    if not segments:
        text = getattr(result, "text", "").strip()
        duration = float(result_duration or ffprobe_duration(path) or 30)
        segments = [Segment(start=0, end=duration, text=text)] if text else []
    return segments, float(result_duration) if result_duration else None


def _make_chunks(path: Path, target_dir: Path) -> list[tuple[Path, float]]:
    duration = ffprobe_duration(path)
    if not duration:
        raise RuntimeError("큰 음성 파일의 재생 시간을 확인하지 못했습니다. FFprobe 포함 여부를 확인해 주세요.")
    chunks: list[tuple[Path, float]] = []
    for index in range(math.ceil(duration / CHUNK_SECONDS)):
        start = index * CHUNK_SECONDS
        target = target_dir / f"chunk_{index + 1:03d}.mp3"
        result = run_command([
            "ffmpeg", "-y", "-ss", f"{start:.3f}", "-i", str(path),
            "-t", str(CHUNK_SECONDS), "-vn", "-ac", "1", "-ar", "16000",
            "-b:a", "56k", str(target),
        ])
        if result.returncode != 0 or not target.exists():
            raise RuntimeError(result.stderr.strip() or "전사용 음성 청크 생성에 실패했습니다.")
        if target.stat().st_size >= MAX_DIRECT_UPLOAD_BYTES:
            raise RuntimeError("분할한 음성도 업로드 한도를 초과했습니다. 더 짧은 파일로 나눠 주세요.")
        chunks.append((target, float(start)))
    return chunks


def transcribe_audio(
    path: Path,
    source_name: str,
    api_key: str,
    model: str,
    progress: Callable[[int, int, str], None] | None = None,
) -> Transcript:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    if path.stat().st_size < MAX_DIRECT_UPLOAD_BYTES:
        if progress:
            progress(0, 1, "음성을 OpenAI에 업로드하고 있습니다.")
        segments, result_duration = _transcribe_file(client, path, model)
        if progress:
            progress(1, 1, "음성 전사를 완료했습니다.")
        duration = segments[-1].end if segments else result_duration
        return Transcript(source_name=source_name, duration=duration, segments=segments)

    if progress:
        progress(0, 0, "25MB를 넘는 음성을 전사용 청크로 준비하고 있습니다.")
    with tempfile.TemporaryDirectory(prefix="podcast-transcribe-") as temp_dir:
        chunks = _make_chunks(path, Path(temp_dir))
        combined: list[Segment] = []
        for index, (chunk_path, offset) in enumerate(chunks, start=1):
            if progress:
                progress(index - 1, len(chunks), f"음성 청크 {index}/{len(chunks)} 전사 중...")
            segments, _ = _transcribe_file(client, chunk_path, model)
            combined.extend(
                Segment(start=segment.start + offset, end=segment.end + offset, text=segment.text)
                for segment in segments
            )
        if progress:
            progress(len(chunks), len(chunks), "전체 전사를 병합했습니다.")
    duration = combined[-1].end if combined else ffprobe_duration(path)
    return Transcript(source_name=source_name, duration=duration, segments=combined)
