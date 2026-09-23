from __future__ import annotations

import re
from pathlib import Path

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


def transcribe_audio(path: Path, source_name: str, api_key: str, model: str) -> Transcript:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
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
    if not segments:
        text = getattr(result, "text", "").strip()
        duration = getattr(result, "duration", None) or 30
        segments = [Segment(start=0, end=float(duration), text=text)] if text else []
    duration = segments[-1].end if segments else None
    return Transcript(source_name=source_name, duration=duration, segments=segments)
