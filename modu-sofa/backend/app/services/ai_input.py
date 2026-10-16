"""LLM 입력 구성. 형식: [seg=12][00:12.4][혜영] 문장

LLM에는 Segment의 seq 번호를 Segment ID로 보여주고, 반환된 ID를 Backend가 실제 Segment로 확정한다.
"""

from dataclasses import dataclass

from app.models import EpisodeSpeaker, TranscriptSegment


@dataclass
class AiSegment:
    ref: int  # LLM에 보여주는 Segment ID (= seq)
    segment: TranscriptSegment
    speaker: str
    text: str

    @property
    def start(self) -> float:
        return self.segment.start_time

    @property
    def end(self) -> float:
        return self.segment.end_time


def fmt_ts(sec: float) -> str:
    m, s = divmod(sec, 60)
    return f"{int(m):02d}:{s:04.1f}"


def build(segments: list[TranscriptSegment], speakers: list[EpisodeSpeaker]) -> list[AiSegment]:
    names = {s.id: (s.display_name or s.speaker_code) for s in speakers}
    out = []
    for seg in segments:
        if seg.is_deleted:  # 삭제 문장 제외
            continue
        out.append(AiSegment(ref=seg.seq, segment=seg, speaker=names.get(seg.speaker_id, "?"), text=seg.text))
    return out


def line(a: AiSegment) -> str:
    return f"[seg={a.ref}][{fmt_ts(a.start)}][{a.speaker}] {a.text}"


def split_parts(items: list[AiSegment], max_chars: int) -> list[list[AiSegment]]:
    parts: list[list[AiSegment]] = [[]]
    size = 0
    for a in items:
        ln = len(line(a)) + 1
        if parts[-1] and size + ln > max_chars:
            parts.append([])
            size = 0
        parts[-1].append(a)
        size += ln
    return [p for p in parts if p]
