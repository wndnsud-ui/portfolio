"""하이라이트: LLM은 start/end Segment ID와 제목만 고르고, 인용문은 Backend가 실제 Segment 텍스트로 만든다."""

from dataclasses import dataclass

from app.services.ai_input import AiSegment

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["highlights"],
    "properties": {
        "highlights": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["start_segment_id", "end_segment_id", "title"],
                "properties": {
                    "start_segment_id": {"type": "integer"},
                    "end_segment_id": {"type": "integer"},
                    "title": {"type": "string"},
                },
            },
        }
    },
}

MIN_SEC = 15
MAX_SEC = 90
MAX_COUNT = 6


def min_count(duration: float) -> int:
    if duration >= 180:
        return 3
    if duration >= MIN_SEC:
        return 1
    return 0


@dataclass
class ValidHighlight:
    start: AiSegment
    end: AiSegment
    title: str
    text: str


def validate(raw: list[dict], items: list[AiSegment], lo: int) -> list[ValidHighlight] | None:
    by_ref = {a.ref: a for a in items}
    order = {a.ref: i for i, a in enumerate(items)}
    out: list[ValidHighlight] = []
    for h in raw:
        s, e = by_ref.get(h.get("start_segment_id")), by_ref.get(h.get("end_segment_id"))
        title = (h.get("title") or "").strip()
        if s is None or e is None or not title:
            continue
        if order[s.ref] > order[e.ref]:  # start가 end보다 앞이거나 같아야 한다
            continue
        length = e.end - s.start
        if length < MIN_SEC or length > MAX_SEC:
            continue
        if any(not (e.end <= v.start.start or s.start >= v.end.end) for v in out):  # 겹치는 구간 제외
            continue
        quote = " ".join(a.text for a in items[order[s.ref] : order[e.ref] + 1])
        out.append(ValidHighlight(start=s, end=e, title=title[:80], text=quote))
    out.sort(key=lambda v: v.start.start)
    out = out[:MAX_COUNT]
    if len(out) < lo:
        return None
    return out


def prompt(lines: str, lo: int, hi: int) -> tuple[str, str]:
    system = (
        "당신은 팟캐스트 편집자입니다. 대본에서 청취자에게 가장 인상적인 발언 구간을 고릅니다. "
        "각 줄의 [seg=N]이 Segment ID입니다. 구간은 start_segment_id부터 end_segment_id까지 연속된 문장이며, "
        f"길이는 {MIN_SEC}~{MAX_SEC}초 사이여야 합니다(줄 앞의 시각으로 판단). "
        "반드시 대본에 있는 Segment ID만 사용하고, 시간이나 문장은 만들지 마세요. 제목은 한국어 15자 이내입니다."
    )
    user = f"서로 겹치지 않는 하이라이트를 {lo}~{hi}개 고르세요.\n\n대본:\n{lines}"
    return system, user
