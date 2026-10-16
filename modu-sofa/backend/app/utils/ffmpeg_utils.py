"""FFmpeg / ffprobe 래퍼.

ffprobe가 없으면(로컬 개발에서 imageio-ffmpeg만 있는 경우) `ffmpeg -i` 출력 파싱으로 대체한다.
"""

import json
import re
import shutil
import subprocess
from array import array
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.config import settings


class FFmpegError(RuntimeError):
    pass


@dataclass
class ProbeResult:
    format_name: str
    duration: float
    has_audio: bool
    has_video: bool
    audio_codec: str | None


@lru_cache
def ffmpeg_bin() -> str:
    if settings.FFMPEG_PATH:
        return settings.FFMPEG_PATH
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:  # pragma: no cover
        raise FFmpegError("ffmpeg를 찾을 수 없습니다. FFMPEG_PATH를 설정하세요.") from e


@lru_cache
def ffprobe_bin() -> str | None:
    if settings.FFPROBE_PATH:
        return settings.FFPROBE_PATH
    return shutil.which("ffprobe")


def _run(args: list[str], timeout: float | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, timeout=timeout)


def probe(source: str, timeout: float = 120) -> ProbeResult:
    """source: 로컬 경로 또는 HTTP URL."""
    fp = ffprobe_bin()
    if fp:
        r = _run(
            [fp, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", source],
            timeout=timeout,
        )
        if r.returncode != 0:
            raise FFmpegError(r.stderr.decode("utf-8", "replace")[-500:])
        data = json.loads(r.stdout or b"{}")
        streams = data.get("streams", [])
        fmt = data.get("format", {})
        audio = [s for s in streams if s.get("codec_type") == "audio"]
        # 앨범 아트(attached_pic)는 영상 스트림으로 보지 않는다.
        video = [
            s
            for s in streams
            if s.get("codec_type") == "video" and not (s.get("disposition") or {}).get("attached_pic")
        ]
        dur = fmt.get("duration") or (audio[0].get("duration") if audio else None)
        return ProbeResult(
            format_name=fmt.get("format_name", ""),
            duration=float(dur) if dur not in (None, "N/A") else 0.0,
            has_audio=bool(audio),
            has_video=bool(video),
            audio_codec=audio[0].get("codec_name") if audio else None,
        )

    # 대체 경로: ffmpeg -i 의 stderr 파싱
    r = _run([ffmpeg_bin(), "-hide_banner", "-i", source], timeout=timeout)
    err = r.stderr.decode("utf-8", "replace")
    m_in = re.search(r"Input #0, ([^,\n]+(?:,[^,\n ]+)*), from", err)
    m_dur = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", err)
    if not m_in:
        raise FFmpegError(err[-500:])
    audio_m = re.search(r"Stream #\S+.*?: Audio: (\w+)", err)
    video_lines = [ln for ln in err.splitlines() if ": Video:" in ln and "attached pic" not in ln]
    duration = 0.0
    if m_dur:
        h, mnt, s = m_dur.groups()
        duration = int(h) * 3600 + int(mnt) * 60 + float(s)
    return ProbeResult(
        format_name=m_in.group(1),
        duration=duration,
        has_audio=bool(audio_m),
        has_video=bool(video_lines),
        audio_codec=audio_m.group(1) if audio_m else None,
    )


def can_decode(source: str, seconds: int = 10, timeout: float = 120) -> bool:
    """앞부분을 실제로 디코딩해 재생 가능 여부를 확인한다."""
    r = _run(
        [ffmpeg_bin(), "-v", "error", "-xerror", "-t", str(seconds), "-i", source, "-vn", "-f", "null", "-"],
        timeout=timeout,
    )
    return r.returncode == 0


def to_playback_mp3(src: Path, dst: Path) -> None:
    """정확한 seek를 위한 재생용 MP3 CBR 128kbps, 44.1kHz."""
    r = _run(
        [
            ffmpeg_bin(), "-y", "-v", "error", "-i", str(src),
            "-vn", "-map", "0:a:0", "-ac", "2", "-ar", "44100",
            "-c:a", "libmp3lame", "-b:a", "128k", "-write_xing", "1",
            str(dst),
        ]
    )
    if r.returncode != 0:
        raise FFmpegError(r.stderr.decode("utf-8", "replace")[-800:])


def make_stt_chunk(src: Path, dst: Path, start: float, length: float) -> None:
    """STT용 모노 16kHz 64kbps MP3 청크."""
    r = _run(
        [
            ffmpeg_bin(), "-y", "-v", "error",
            "-ss", f"{start:.3f}", "-t", f"{length:.3f}", "-i", str(src),
            "-vn", "-ac", "1", "-ar", "16000", "-c:a", "libmp3lame", "-b:a", "64k",
            str(dst),
        ]
    )
    if r.returncode != 0:
        raise FFmpegError(r.stderr.decode("utf-8", "replace")[-800:])


def compute_peaks(src: Path, points_per_sec: int = 25, sample_rate: int = 8000) -> list[float]:
    """모노 8kHz PCM으로 디코딩해 구간별 최대 진폭(0~1)을 계산한다. 결과는 소수 3자리."""
    window = max(1, sample_rate // points_per_sec)
    proc = subprocess.Popen(
        [
            ffmpeg_bin(), "-v", "error", "-i", str(src),
            "-vn", "-ac", "1", "-ar", str(sample_rate), "-f", "s16le", "-",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.stdout is not None
    peaks: list[float] = []
    leftover = b""
    block_bytes = window * 2 * 1000
    while True:
        chunk = proc.stdout.read(block_bytes)
        if not chunk:
            break
        buf = leftover + chunk
        usable = len(buf) - (len(buf) % (window * 2))
        samples = array("h")
        samples.frombytes(buf[:usable])
        leftover = buf[usable:]
        for i in range(0, len(samples), window):
            seg = samples[i : i + window]
            peaks.append(max(max(seg), -min(seg)) / 32768.0)
    if len(leftover) >= 2:
        samples = array("h")
        samples.frombytes(leftover[: len(leftover) - (len(leftover) % 2)])
        if samples:
            peaks.append(max(max(samples), -min(samples)) / 32768.0)
    proc.wait()
    if proc.returncode != 0:
        assert proc.stderr is not None
        raise FFmpegError(proc.stderr.read().decode("utf-8", "replace")[-800:])
    top = max(peaks) if peaks else 0
    scale = 1 / top if top > 0 else 1
    return [round(min(1.0, p * scale), 3) for p in peaks]


def chunk_plan(duration: float, chunk_sec: int, overlap_sec: int) -> list[tuple[float, float]]:
    """(offset, length) 목록. 청크 i의 offset = i * (chunk - overlap)."""
    if duration <= chunk_sec:
        return [(0.0, duration)]
    step = chunk_sec - overlap_sec
    plans: list[tuple[float, float]] = []
    offset = 0.0
    while True:
        length = min(chunk_sec, duration - offset)
        plans.append((offset, length))
        if offset + length >= duration:
            break
        offset += step
    return plans
