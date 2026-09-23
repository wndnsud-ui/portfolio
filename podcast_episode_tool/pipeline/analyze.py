from __future__ import annotations

from itertools import groupby

from pydantic import BaseModel, Field

from .models import Candidate, Transcript


class CandidateList(BaseModel):
    candidates: list[Candidate] = Field(default_factory=list)


def transcript_text(transcript: Transcript) -> str:
    return "\n".join(f"[{format_seconds(s.start)}] {s.text}" for s in transcript.segments)


def format_seconds(value: float) -> str:
    total = int(value)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def text_between(transcript: Transcript, start: float, end: float) -> str:
    return "\n".join(s.text for s in transcript.segments if s.end > start and s.start < end).strip()


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
    if not api_key:
        return mock_candidates(transcript)
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    prompt = f"""
다음은 시간 표시가 있는 팟캐스트 회의 녹취록입니다.
실제 발화와 시간만 근거로 0~5개의 연속 구간 후보를 제안하세요.
내부 잡담보다 청취자 질문, 대화 전개, 출연자 호흡, 공개 검토 필요성을 우선하세요.
떨어진 구간을 자동 연결하지 마세요.

녹취록:
{transcript_text(transcript)}
"""
    response = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": "당신은 팟캐스트 에피소드 편집 후보를 엄격히 고르는 편집자입니다."},
            {"role": "user", "content": prompt},
        ],
        response_format=CandidateList,
    )
    parsed = response.choices[0].message.parsed
    candidates = parsed.candidates if parsed else []
    valid: list[Candidate] = []
    for idx, candidate in enumerate(candidates[:5], start=1):
        if candidate.end <= candidate.start:
            continue
        if transcript.duration and candidate.end > transcript.duration + 1:
            continue
        candidate.id = candidate.id or f"cand_{idx}"
        candidate.transcript = candidate.transcript or text_between(transcript, candidate.start, candidate.end)
        valid.append(candidate)
    return valid
