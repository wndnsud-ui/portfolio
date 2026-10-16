"""챕터: LLM이 고른 start_segment_id를 검증하고 시간은 Segment에서 확정한다."""

import math
from dataclasses import dataclass

from app.services.ai_input import AiSegment

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["chapters"],
    "properties": {
        "chapters": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["start_segment_id", "title", "description"],
                "properties": {
                    "start_segment_id": {"type": "integer"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                },
            },
        }
    },
}


def target_range(duration: float, n_segments: int) -> tuple[int, int]:
    """10분당 1~2개, 최소 3개 최대 12개 (Segment 수가 적으면 그만큼으로 제한)."""
    tens = max(1, math.ceil(duration / 600))
    lo = max(3, tens)
    hi = min(12, max(lo, tens * 2))
    lo = min(lo, 12)
    return min(lo, n_segments), min(hi, n_segments)


@dataclass
class ValidChapter:
    seg: AiSegment
    title: str
    description: str


def validate(raw: list[dict], items: list[AiSegment], lo: int, hi: int) -> list[ValidChapter] | None:
    by_ref = {a.ref: a for a in items}
    seen: set[int] = set()
    out: list[ValidChapter] = []
    for c in raw:
        ref = c.get("start_segment_id")
        a = by_ref.get(ref) if isinstance(ref, int) else None
        title = (c.get("title") or "").strip()
        if a is None or not title or ref in seen:  # 없는 ID는 그 항목만 버린다
            continue
        seen.add(ref)
        out.append(ValidChapter(seg=a, title=title[:120], description=(c.get("description") or "").strip()))
    out.sort(key=lambda v: v.seg.start)  # 시간 오름차순
    if not out:
        return None if lo > 0 else []
    # 첫 챕터는 첫 Segment에서 시작
    if out[0].seg.ref != items[0].ref:
        out[0] = ValidChapter(seg=items[0], title=out[0].title, description=out[0].description)
        # 같은 Segment가 중복되면 제거
        dedup: list[ValidChapter] = []
        for v in out:
            if dedup and dedup[-1].seg.ref == v.seg.ref:
                continue
            dedup.append(v)
        out = dedup
    out = out[:hi]
    if len(out) < lo:
        return None
    return out


def prompt(lines: str, lo: int, hi: int) -> tuple[str, str]:
    system = (
        "당신은 팟캐스트 편집자입니다. 대본을 읽고 주제가 바뀌는 지점에서 챕터를 나눕니다. "
        "각 줄의 [seg=N]이 Segment ID입니다. 반드시 대본에 있는 Segment ID만 사용하고, 시간은 절대 만들지 마세요. "
        "첫 챕터는 첫 Segment에서 시작합니다. 챕터 제목은 한국어로 15자 이내, 설명은 한 문장입니다."
    )
    user = f"챕터를 {lo}~{hi}개 만들어 시간 순서대로 반환하세요.\n\n대본:\n{lines}"
    return system, user
