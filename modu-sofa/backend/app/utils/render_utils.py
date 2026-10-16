"""내보내기 렌더링 (FFmpeg filter_complex).

순서: 자르기 → (AI 잡음 제거) → (음량·잡음 보정) → 시작음 크로스페이드 → (라우드니스 표준화) → MP3 192kbps
"""

import subprocess
from pathlib import Path

from app.utils.ffmpeg_utils import FFmpegError, ffmpeg_bin

RNNOISE_DIR = Path(__file__).resolve().parents[1] / "assets" / "rnnoise"
RNNOISE_MODEL = "sh.rnnn"  # GregorR/rnnoise-models somnolent-hogwash (음성 + 녹음 잡음)

# 팟캐스트 권장 라우드니스 -16 LUFS
LOUDNORM = "loudnorm=I=-16:LRA=11:TP=-1.5"
# 저역 험 제거 + FFT 잡음 감소 + 목소리 존재감(3kHz) 살짝
ENHANCE = "highpass=f=80,afftdn=nf=-25,equalizer=f=3000:t=q:w=1.2:g=2"
FORMAT = "aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo"


def select_expr(cuts: list[tuple[float, float]]) -> str:
    terms = "+".join(f"between(t\\,{s:.3f}\\,{e:.3f})" for s, e in cuts)
    return f"aselect='not({terms})',asetpts=N/SR/TB"


def build_filter(
    cuts: list[tuple[float, float]],
    enhance: bool,
    ai_denoise: bool,
    intro_duration: float | None,
) -> str:
    main: list[str] = []
    if cuts:
        main.append(select_expr(cuts))
    if ai_denoise:
        # RNNoise는 48kHz 기준
        main += ["aresample=48000", f"arnndn=m={RNNOISE_MODEL}"]
    if enhance:
        main.append(ENHANCE)
    main.append(FORMAT)
    parts = [f"[0:a]{','.join(main)}[m]"]

    if intro_duration:
        fade = min(1.5, max(0.3, intro_duration / 4))
        parts.append(f"[1:a]{FORMAT},afade=t=out:st={max(0.0, intro_duration - fade):.3f}:d={fade:.3f}[i]")
        parts.append(f"[i][m]acrossfade=d={min(1.0, fade):.3f}:c1=tri:c2=tri[x]")
        last = "x"
    else:
        last = "m"

    if enhance:
        parts.append(f"[{last}]{LOUDNORM},{FORMAT}[out]")
    else:
        parts.append(f"[{last}]anull[out]")
    return ";".join(parts)


def render(
    src: Path,
    dst: Path,
    cuts: list[tuple[float, float]],
    enhance: bool,
    ai_denoise: bool,
    intro: Path | None = None,
    intro_duration: float | None = None,
) -> None:
    args = [ffmpeg_bin(), "-y", "-v", "error", "-i", str(src)]
    if intro is not None:
        args += ["-i", str(intro)]
    graph = build_filter(cuts, enhance, ai_denoise, intro_duration if intro is not None else None)
    args += [
        "-filter_complex", graph, "-map", "[out]",
        "-c:a", "libmp3lame", "-b:a", "192k", "-ar", "44100", "-ac", "2", str(dst),
    ]
    # arnndn 모델 경로에 드라이브 문자(C:)가 들어가면 필터 문법과 충돌하므로 모델 폴더에서 실행한다
    r = subprocess.run(args, capture_output=True, cwd=str(RNNOISE_DIR))
    if r.returncode != 0:
        raise FFmpegError(r.stderr.decode("utf-8", "replace")[-800:])
