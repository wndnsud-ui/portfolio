from __future__ import annotations

from itertools import groupby
import re

from pydantic import BaseModel, Field

from .models import Candidate, Transcript


class CandidateList(BaseModel):
    candidates: list[Candidate] = Field(default_factory=list)


TIMECODE_RE = re.compile(r"\[(\d{1,2}:\d{2}(?::\d{2})?)\]")
SPEAKER_ONLY_RE = re.compile(r"^(?:참석자|화자|speaker)\s*\d+$", re.IGNORECASE)


def transcript_text(transcript: Transcript) -> str:
    return "\n".join(f"[{format_seconds(s.start)}] {s.text}" for s in transcript.segments)


def format_seconds(value: float) -> str:
    total = int(value)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def text_between(transcript: Transcript, start: float, end: float) -> str:
    return "\n".join(s.text for s in transcript.segments if s.end > start and s.start < end).strip()


def ensure_meaningful_transcript(transcript: Transcript) -> None:
    texts = [segment.text.strip() for segment in transcript.segments if segment.text.strip()]
    if not texts:
        raise ValueError("분석할 전사 내용이 없습니다. 원본 음성을 먼저 전사해 주세요.")
    meaningful = [text for text in texts if not SPEAKER_ONLY_RE.fullmatch(text)]
    if len(meaningful) < max(3, len(texts) // 10):
        raise ValueError(
            "전사문에 실제 발화가 없고 화자 이름만 있습니다. "
            "원본 오디오를 선택한 뒤 '음성 전사'를 다시 실행해 주세요."
        )


def normalize_candidate_times(candidate: Candidate, transcript: Transcript) -> tuple[float, float]:
    references = [parse_timecode(value) for value in TIMECODE_RE.findall(candidate.transcript)]
    references = [value for value in references if not transcript.duration or value <= transcript.duration]
    if references:
        start = min(references)
        last = max(references)
        matching = [segment for segment in transcript.segments if abs(segment.start - last) < 1]
        end = max(segment.end for segment in matching) if matching else last + 1
        return start, end
    return candidate.start, candidate.end


def speech_bounds(transcript: Transcript, start: float, end: float) -> tuple[float, float] | None:
    spoken = [segment for segment in transcript.segments if segment.end > start and segment.start < end]
    if not spoken:
        return None
    return spoken[0].start, spoken[-1].end


def has_excessive_silence(transcript: Transcript, start: float, end: float) -> bool:
    spoken = [segment for segment in transcript.segments if segment.end > start and segment.start < end]
    if not spoken:
        return True
    gaps = [max(0.0, right.start - left.end) for left, right in zip(spoken, spoken[1:])]
    silent_duration = sum(gaps)
    total_duration = max(1.0, end - start)
    return (max(gaps, default=0.0) >= 12.0) or (silent_duration / total_duration >= 0.4)


def parse_timecode(value: str) -> float:
    parts = [int(part) for part in value.split(":" )]
    if len(parts) == 2:
        return float(parts[0] * 60 + parts[1])
    return float(parts[0] * 3600 + parts[1] * 60 + parts[2])


def mock_candidates(transcript: Transcript) -> list[Candidate]:
    segments = transcript.segments[:]
    if not segments:
        return []
    buckets: list[list] = []
    for _, group in groupby(enumerate(segments), key=lambda item: item[0] // max(1, len(segments) // 3 or 1)):
        chunk = [item[1] for item in group]
        if chunk:
            buckets.append(chunk)
    candidates: list[Candidate] = []
    for idx, chunk in enumerate(buckets[:5], start=1):
        text = "\n".join(s.text for s in chunk).strip()
        if not text:
            continue
        title_seed = chunk[0].text[:28].strip()
        candidates.append(Candidate(
            id=f"cand_{idx}",
            title=title_seed or f"후보 {idx}",
            summary=(text[:240] + "...") if len(text) > 240 else text,
            listener_question="API 키가 없어 모의 후보로 생성되었습니다. 질문 문구를 검토해 주세요.",
            reason="시간 표시 전사문을 순서대로 나누어 승인 흐름 검증용 후보를 만들었습니다.",
            start=chunk[0].start,
            end=chunk[-1].end,
            transcript=text,
            usage_type="원본 클립" if chunk[-1].end - chunk[0].start >= 60 else "새 녹음 소재",
            review_notes="실제 AI 후보 분석은 OPENAI_API_KEY 설정 후 실행하세요.",
        ))
    return candidates


def analyze_candidates(transcript: Transcript, api_key: str | None, model: str) -> list[Candidate]:
    ensure_meaningful_transcript(transcript)
    if not api_key:
        return mock_candidates(transcript)
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    prompt = f"""
다음은 시간 표시가 있는 팟캐스트 회의 녹취록입니다.
실제 발화와 시간만 근거로 0~5개의 연속 구간 후보를 제안하세요.
내부 잡담보다 청취자 질문, 대화 전개, 출연자 호흡, 공개 검토 필요성을 우선하세요.
떨어진 구간을 자동 연결하지 마세요.
실제 발화가 없는 무음 구간은 후보로 만들지 마세요. 앞뒤 무음은 제외하고, 중간에 12초 이상의 긴 무음이 있는 범위도 선택하지 마세요.
start와 end는 반드시 녹음 시작점을 0으로 한 초 단위 숫자로 작성하세요. 예: [04:31]은 271초입니다.
transcript에는 선택한 모든 원문 줄을 [MM:SS] 시간 표시와 함께 그대로 포함하세요.

모든 후보의 title, summary, listener_question, reason, usage_type, review_notes는 반드시 자연스러운 한국어로 작성하세요.
title은 원문의 외국어 표현을 그대로 복사하지 말고 내용을 알아보기 쉬운 15~30자 한국어 제목으로 바꾸세요.
summary는 해당 구간에서 실제로 다룬 핵심 내용과 대화의 결론을 3~5문장으로 구체적으로 정리하세요.
listener_question은 청취자가 실제로 궁금해할 질문 한 문장으로 작성하세요.
reason은 이 구간을 에피소드 후보로 추천한 편집상 이유를 2~3문장으로 설명하세요.
review_notes는 공개 전에 확인할 민감 표현이나 사실 확인 사항을 적고, 없으면 "특이사항 없음"으로 작성하세요.

녹취록:
{transcript_text(transcript)}
"""
    response = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": "당신은 한국어 팟캐스트 에피소드 편집자입니다. 모든 편집 메타데이터를 자연스럽고 명확한 한국어로 작성합니다."},
            {"role": "user", "content": prompt},
        ],
        response_format=CandidateList,
    )
    parsed = response.choices[0].message.parsed
    candidates = parsed.candidates if parsed else []
    valid: list[Candidate] = []
    for idx, candidate in enumerate(candidates[:5], start=1):
        candidate.start, candidate.end = normalize_candidate_times(candidate, transcript)
        bounds = speech_bounds(transcript, candidate.start, candidate.end)
        if not bounds:
            continue
        candidate.start, candidate.end = bounds
        if candidate.end <= candidate.start:
            continue
        if transcript.duration and candidate.end > transcript.duration + 1:
            continue
        if has_excessive_silence(transcript, candidate.start, candidate.end):
            continue
        candidate.id = candidate.id or f"cand_{idx}"
        candidate.transcript = text_between(transcript, candidate.start, candidate.end)
        valid.append(candidate)
    return valid
