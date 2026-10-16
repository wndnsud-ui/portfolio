"""OpenAI 호출 래퍼와 개발용 모의(mock) Provider.

OPENAI_API_KEY가 없으면(STT_PROVIDER/LLM_PROVIDER=auto) 모의 Provider가 동작해
키 없이도 업로드 → 분석 → 에디터 흐름 전체를 확인할 수 있다.
"""

import json
import random
from functools import lru_cache
from pathlib import Path

from app.core.config import settings


def _client():
    return _client_for(settings.OPENAI_API_KEY)


@lru_cache(maxsize=4)
def _client_for(api_key: str):
    from openai import OpenAI

    return OpenAI(api_key=api_key, max_retries=0, timeout=600)


# ───────────────────────── STT ─────────────────────────


def transcribe_chunk(path: Path, offset: float, length: float) -> dict:
    """청크 파일을 받아 diarized_json 형태의 dict를 반환한다. 시간은 청크 기준(0부터)."""
    if settings.stt_provider == "mock":
        return _mock_transcribe(offset, length)
    with path.open("rb") as f:
        res = _client().audio.transcriptions.create(
            model=settings.OPENAI_STT_MODEL,
            file=f,
            response_format="diarized_json",
            chunking_strategy="auto",
        )
    return res.model_dump() if hasattr(res, "model_dump") else json.loads(str(res))


_MOCK_LINES = [
    "모의 STT 결과입니다. OPENAI_API_KEY를 설정하면 실제 음성을 받아 적어요.",
    "안녕하세요. 오늘은 많은 분들이 궁금해하시는 재물운에 대해서 이야기해볼게요.",
    "재물운은 보통 어떤 걸 보나요? 단순히 돈의 많고 적음만을 보는 건가요?",
    "저는 먼저 일간과 재성을 봐요. 그리고 대운과 세운까지 함께 봐야 정확하게 판단할 수 있어요.",
    "맞아요. 재성이 있다고 무조건 재물운이 좋은 건 아니고, 그 재성이 어떻게 작용하는지가 더 중요하죠.",
    "그럼 재성이 강한데도 오히려 재물운이 안 좋은 경우도 있나요?",
    "네, 있어요. 재성이 너무 강하면 감당하지 못해서 금전적인 손실이 생길 수도 있어요.",
    "그래서 사주를 볼 때는 전체적인 균형을 봐야 하는 거군요.",
    "일간의 힘, 재성의 위치, 그리고 다른 십성과의 관계까지 종합적으로 봐야 해요.",
    "그러면 오늘은 그 세 가지를 하나씩 짚어볼까요?",
    "대운은 10년의 흐름, 세운은 1년의 흐름이라서 서로 다르게 해석해야 해요.",
    "실제 사례를 하나 들어볼게요. 이 분은 재성이 약하지만 대운에서 큰 기회가 들어오는 구조예요.",
    "결국 중요한 건 시기를 읽는 거네요. 언제 들어오고 언제 지켜야 하는지요.",
    "오늘 이야기 정리해보면, 재성의 유무보다 작용과 흐름을 함께 보는 게 핵심이에요.",
]


def _mock_timeline(total_hint: float) -> list[tuple[float, float, int, str]]:
    """전체 오디오 기준 가상 타임라인. 청크마다 같은 타임라인을 잘라 쓰므로 겹침 구간이 일치한다."""
    rnd = random.Random(42)
    out = []
    t = 0.5
    sp = 0
    i = 0
    while t < total_hint:
        dur = rnd.uniform(4.0, 11.0)
        text = _MOCK_LINES[i % len(_MOCK_LINES)] if i < len(_MOCK_LINES) else rnd.choice(_MOCK_LINES[1:])
        out.append((t, t + dur, sp, text))
        t += dur + rnd.uniform(0.3, 1.6)
        sp = (sp + rnd.choice([1, 1, 2])) % 3
        i += 1
    return out


def _mock_transcribe(offset: float, length: float) -> dict:
    timeline = _mock_timeline(offset + length + 30)
    # 청크마다 라벨 순서를 바꿔서 화자 통합 로직이 실제처럼 동작하게 한다.
    labels = ["A", "B", "C"]
    shift = int(offset // 1000) % 3
    segs = []
    for st, en, sp, text in timeline:
        if st < offset or st >= offset + length:
            continue
        segs.append(
            {
                "type": "transcript.text.segment",
                "id": f"seg_{len(segs)}",
                "start": round(st - offset, 2),
                "end": round(min(en, offset + length) - offset, 2),
                "speaker": labels[(sp + shift) % 3],
                "text": text,
            }
        )
    return {"text": " ".join(s["text"] for s in segs), "segments": segs}


# ───────────────────────── LLM ─────────────────────────


def structured_completion(system: str, user: str, schema_name: str, schema: dict) -> dict:
    """Structured Outputs(JSON Schema strict)로 JSON을 강제한다."""
    res = _client().chat.completions.create(
        model=settings.OPENAI_LLM_MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": schema_name, "strict": True, "schema": schema},
        },
    )
    msg = res.choices[0].message
    if getattr(msg, "refusal", None):
        raise RuntimeError(f"LLM refusal: {msg.refusal}")
    return json.loads(msg.content or "{}")
