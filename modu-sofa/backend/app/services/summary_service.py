"""AI 분석 오케스트레이션: 요약 · 키워드 · 제목 후보 · 챕터 · 하이라이트.

- 입력: edited_text ?? original_text, display_name ?? speaker_code, 삭제 문장 제외
- 출력: JSON Schema(Structured Outputs) 강제, Segment ID만 반환 → Backend가 존재 검증 후 시간 확정
- 유효 항목이 최소 개수에 못 미치면 1회 재요청 후 실패
- 컨텍스트 한도를 넘으면 구간별로 처리 후 합친다(map-reduce)
"""

import logging
import re
import uuid
from collections import Counter

from app.core.config import reload_analysis_settings, settings
from app.db.session import SessionLocal
from app.models import AiResult, AiStatus, Chapter, ErrorStage, Highlight
from app.models.base import utcnow
from app.repositories import ai_repo, episode_repo, segment_repo, speaker_repo
from app.services import (
    ai_input,
    chapter_service,
    highlight_service,
    job_control,
    openai_client,
)
from app.services.ai_input import AiSegment

log = logging.getLogger(__name__)

LLM_MAX_CHARS = 120_000

SUMMARY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "keywords", "title_candidates"],
    "properties": {
        "summary": {"type": "string"},
        "keywords": {"type": "array", "items": {"type": "string"}},
        "title_candidates": {"type": "array", "items": {"type": "string"}},
    },
}
PART_SUMMARY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary"],
    "properties": {"summary": {"type": "string"}},
}


class AiFailed(Exception):
    pass


# ───────────────────────── 요약 ─────────────────────────


def _summary_openai(parts: list[list[AiSegment]]) -> dict:
    system = (
        "당신은 한국어 팟캐스트 편집자입니다. 대본을 읽고 3~4문장 요약, 핵심 키워드 3~6개, "
        "청취자가 클릭하고 싶은 에피소드 제목 후보 정확히 3개를 만듭니다. 제목은 25자 이내입니다."
    )
    if len(parts) == 1:
        lines = "\n".join(ai_input.line(a) for a in parts[0])
        return openai_client.structured_completion(system, f"대본:\n{lines}", "episode_summary", SUMMARY_SCHEMA)
    partials = []
    for i, p in enumerate(parts, 1):
        lines = "\n".join(ai_input.line(a) for a in p)
        r = openai_client.structured_completion(
            "당신은 한국어 팟캐스트 편집자입니다. 대본 일부를 4~6문장으로 요약합니다.",
            f"대본 {i}/{len(parts)}부:\n{lines}",
            "part_summary",
            PART_SUMMARY_SCHEMA,
        )
        partials.append(f"[{i}부] {r.get('summary', '')}")
    return openai_client.structured_completion(
        system, "아래는 에피소드를 구간별로 요약한 것입니다.\n\n" + "\n".join(partials), "episode_summary", SUMMARY_SCHEMA
    )


_STOP = {"그리고", "그러면", "그래서", "있어요", "있나요", "거군요", "하는", "있다고", "오늘은", "이야기해볼게요"}


def _with_wa(word: str) -> str:
    last = ord(word[-1]) if word else 0
    has_final = 0xAC00 <= last <= 0xD7A3 and (last - 0xAC00) % 28 != 0
    return word + ("과" if has_final else "와")


def _summary_mock(items: list[AiSegment]) -> dict:
    words = Counter()
    for a in items:
        for w in re.findall(r"[가-힣]{2,}", a.text):
            w = re.sub(r"(은|는|이|가|을|를|과|와|의|에|도|만|까지|부터|에서|이에요|예요|이라서)$", "", w)
            if len(w) >= 2 and w not in _STOP:
                words[w] += 1
    kws = [w for w, _ in words.most_common(5)] or ["팟캐스트"]
    speakers = sorted({a.speaker for a in items})
    first = items[0].text if items else ""
    return {
        "summary": (
            f"[모의 AI] {len(speakers)}명의 화자가 이야기를 나눕니다. "
            f"주요 키워드는 {', '.join(kws[:3])}입니다. 첫 문장: “{first[:60]}”"
        ),
        "keywords": kws,
        "title_candidates": [f"{kws[0]} 이야기", f"{_with_wa(kws[0])} {kws[min(1, len(kws) - 1)]}, 무엇이 다를까?", "오늘의 핵심 정리"],
    }


# ───────────────────────── 챕터 / 하이라이트 생성 ─────────────────────────


def _part_ranges(parts: list[list[AiSegment]], lo: int, hi: int, total: float) -> list[tuple[int, int]]:
    out = []
    for p in parts:
        share = max(0.0, (p[-1].end - p[0].start)) / total if total > 0 else 1 / len(parts)
        out.append((max(1, round(lo * share)), max(1, round(hi * share))))
    return out


def _chapters_raw(parts, lo, hi, total) -> list[dict]:
    if settings.llm_provider == "mock":
        items = [a for p in parts for a in p]
        n = max(lo, min(hi, 5))
        step = max(1, len(items) // n)
        return [
            {"start_segment_id": items[i].ref, "title": f"챕터 {k + 1}", "description": items[i].text[:40]}
            for k, i in enumerate(range(0, len(items), step))
        ][:n]
    raw: list[dict] = []
    for p, (plo, phi) in zip(parts, _part_ranges(parts, lo, hi, total)):
        system, user = chapter_service.prompt("\n".join(ai_input.line(a) for a in p), plo, phi)
        raw += openai_client.structured_completion(system, user, "chapters", chapter_service.SCHEMA).get("chapters", [])
    return raw


def _highlights_raw(parts, lo, hi, total) -> list[dict]:
    if settings.llm_provider == "mock":
        items = [a for p in parts for a in p]
        out = []
        i = 0
        stride = max(1, len(items) // max(1, hi))
        while i < len(items) and len(out) < hi:
            j = i
            while j + 1 < len(items) and items[j].end - items[i].start < 25:
                j += 1
            if 15 <= items[j].end - items[i].start <= 90:
                out.append(
                    {"start_segment_id": items[i].ref, "end_segment_id": items[j].ref, "title": f"하이라이트 {len(out) + 1}"}
                )
            i = max(j + 1, i + stride)
        return out
    raw: list[dict] = []
    for p, (plo, phi) in zip(parts, _part_ranges(parts, lo, hi, total)):
        system, user = highlight_service.prompt("\n".join(ai_input.line(a) for a in p), plo, phi)
        raw += openai_client.structured_completion(system, user, "highlights", highlight_service.SCHEMA).get(
            "highlights", []
        )
    return raw


# ───────────────────────── 실행 ─────────────────────────


def run_analysis(episode_id: uuid.UUID) -> None:
    """호출 전에 episode_repo.claim_ai()로 ai_status=running 선점이 끝나 있어야 한다."""
    gen = job_control.start_ai(episode_id)
    try:
        _run(episode_id, gen)
    except job_control.Cancelled:
        log.info("ai analysis cancelled: %s", episode_id)
    except Exception as e:  # noqa: BLE001
        log.exception("ai analysis failed")
        with SessionLocal() as db:
            ep = episode_repo.get(db, episode_id)
            if ep and job_control.ai_alive(episode_id, gen):
                ep.ai_status = AiStatus.FAILED
                ep.error_stage = ErrorStage.AI
                ep.error_message = str(e) if isinstance(e, AiFailed) else f"AI 분석에 실패했어요. ({type(e).__name__})"
                ep.status_updated_at = utcnow()
                db.commit()


def _run(episode_id: uuid.UUID, gen: int) -> None:
    reload_analysis_settings()

    def check() -> None:
        if not job_control.ai_alive(episode_id, gen):
            raise job_control.Cancelled()

    with SessionLocal() as db:
        ep = episode_repo.get(db, episode_id)
        if not ep or ep.ai_status != AiStatus.RUNNING:
            return
        duration = ep.duration or 0.0
        segments = segment_repo.list_for_episode(db, episode_id)
        speakers = speaker_repo.list_for_episode(db, episode_id)
        items = ai_input.build(segments, speakers)
    if not items:
        raise AiFailed("분석할 문장이 없어요. 삭제한 문장을 복원한 뒤 다시 실행해 주세요.")

    total = duration or (items[-1].end - items[0].start)
    parts = ai_input.split_parts(items, LLM_MAX_CHARS)

    summary = _summary_mock(items) if settings.llm_provider == "mock" else _summary_openai(parts)
    titles = [t.strip() for t in summary.get("title_candidates", []) if t and t.strip()][:3]
    if not summary.get("summary") or len(titles) < 3:
        summary = _summary_mock(items) if settings.llm_provider == "mock" else _summary_openai(parts)
        titles = [t.strip() for t in summary.get("title_candidates", []) if t and t.strip()][:3]
        if not summary.get("summary") or not titles:
            raise AiFailed("요약을 만들지 못했어요.")

    check()
    c_lo, c_hi = chapter_service.target_range(total, len(items))
    chapters = None
    for _ in range(2):  # 1회 재요청
        chapters = chapter_service.validate(_chapters_raw(parts, c_lo, c_hi, total), items, c_lo, c_hi)
        if chapters is not None:
            break
    if chapters is None:
        raise AiFailed("챕터를 만들지 못했어요.")

    check()
    h_lo = highlight_service.min_count(total)
    h_hi = highlight_service.MAX_COUNT
    highlights = None
    for _ in range(2):
        highlights = highlight_service.validate(_highlights_raw(parts, h_lo, h_hi, total), items, h_lo)
        if highlights is not None:
            break
    if highlights is None:
        raise AiFailed("하이라이트를 만들지 못했어요.")

    with SessionLocal() as db:
        ep = episode_repo.get(db, episode_id)
        check()
        if not ep or ep.ai_status != AiStatus.RUNNING:
            return
        ai_repo.delete_for_episode(db, episode_id)
        db.flush()
        db.add(
            AiResult(
                episode_id=episode_id,
                summary=summary["summary"].strip(),
                keywords=[k.strip() for k in summary.get("keywords", []) if k and k.strip()][:8],
                title_candidates=titles,
                model="mock" if settings.llm_provider == "mock" else settings.OPENAI_LLM_MODEL,
            )
        )
        for i, c in enumerate(chapters):
            db.add(
                Chapter(
                    episode_id=episode_id,
                    start_segment_id=c.seg.segment.id,
                    start_time=c.seg.segment.start_time,  # Backend가 Segment에서 복사
                    title=c.title,
                    description=c.description or None,
                    seq=i,
                )
            )
        for i, h in enumerate(highlights):
            db.add(
                Highlight(
                    episode_id=episode_id,
                    start_segment_id=h.start.segment.id,
                    end_segment_id=h.end.segment.id,
                    start_time=h.start.segment.start_time,
                    end_time=h.end.segment.end_time,
                    title=h.title,
                    text=h.text,
                    seq=i,
                )
            )
        ep.ai_status = AiStatus.COMPLETED
        if ep.error_stage == ErrorStage.AI:
            ep.error_stage = None
            ep.error_message = None
        ep.status_updated_at = utcnow()
        db.commit()
