from __future__ import annotations

import json
import subprocess
from pathlib import Path


def run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, check=False)


def ffprobe_duration(path: Path) -> float | None:
    result = run_command([
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(path),
    ])
    if result.returncode != 0:
        return None
    try:
        return float(json.loads(result.stdout)["format"]["duration"])
    except (KeyError, ValueError, json.JSONDecodeError):
        return None


def cut_audio(source: Path, start: float, end: float, target: Path) -> tuple[bool, str]:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return True, "이미 존재하는 클립을 재사용했습니다."
    duration = max(0.0, end - start)
    if duration <= 0:
        return False, "끝 시간이 시작 시간보다 커야 합니다."
    result = run_command([
        "ffmpeg",
        "-y",
        "-ss",
        f"{start:.3f}",
        "-i",
        str(source),
        "-t",
        f"{duration:.3f}",
        "-vn",
        "-codec:a",
        "libmp3lame",
        "-q:a",
        "2",
        str(target),
    ])
    if result.returncode != 0:
        return False, result.stderr.strip() or "ffmpeg 분할 실패"
    return True, "분할 완료"
