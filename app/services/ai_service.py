import json

import httpx

from app.core.config import settings
from app.core.exceptions import AppError
from app.schemas.analysis import DecisionCandidate
from app.schemas.meeting import MeetingDetail


DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "value": {"type": "string"},
                    "evidence": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["topic", "value", "evidence", "confidence"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["candidates"],
    "additionalProperties": False,
}

MEETING_SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "issues": {"type": "array", "items": {"type": "string"}},
        "decisions": {"type": "array", "items": {"type": "string"}},
        "open_questions": {"type": "array", "items": {"type": "string"}},
        "action_items": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "issues", "decisions", "open_questions", "action_items"],
    "additionalProperties": False,
}


class AIService:
    async def _structured_response(self, system: str, user: str, name: str, schema: dict) -> dict:
        if not settings.openai_api_key:
            raise AppError("OPENAI_API_KEY_MISSING", "OpenAI API key is not configured.", 503)
        payload = {
            "model": settings.decision_analysis_model,
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": system}]},
                {"role": "user", "content": [{"type": "input_text", "text": user}]},
            ],
            "text": {"format": {"type": "json_schema", "name": name, "strict": True, "schema": schema}},
        }
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    "https://api.openai.com/v1/responses",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                    json=payload,
                )
        except httpx.RequestError as exc:
            raise AppError("AI_ANALYSIS_ERROR", f"OpenAI connection failed: {exc}", 502) from exc
        if response.is_error:
            try:
                message = response.json().get("error", {}).get("message", "OpenAI analysis failed.")
            except ValueError:
                message = "OpenAI analysis failed."
            raise AppError("AI_ANALYSIS_ERROR", message, 502)
        body = response.json()
        output_text = next((content["text"] for item in body.get("output", []) if item.get("type") == "message" for content in item.get("content", []) if content.get("type") == "output_text"), None)
        if not output_text:
            raise AppError("AI_ANALYSIS_ERROR", "OpenAI returned no analysis result.", 502)
        try:
            return json.loads(output_text)
        except (json.JSONDecodeError, TypeError) as exc:
            raise AppError("AI_ANALYSIS_ERROR", "OpenAI returned an invalid analysis result.", 502) from exc

    async def summarize_meeting(self, transcript: str) -> dict:
        if not transcript.strip():
            raise AppError("TRANSCRIPT_REQUIRED", "회의 원문이 필요합니다.", 400)
        system = (
            "당신은 한국어 회의록 분석가입니다. 원문에 없는 내용을 추측하지 말고 쟁점 중심으로 정리하세요. "
            "summary는 회의 목적과 결론을 3~5문장으로, issues는 쟁점별로 '쟁점: 화자별 논의와 입장' 형식으로 작성하세요. "
            "원문에 화자 표기가 있으면 각 화자의 주장, 이견, 동의 여부를 구분하고 화자를 임의로 실명화하지 마세요. "
            "decisions에는 명시적으로 확정된 내용만, open_questions에는 미결 사항과 추가 확인 항목만, "
            "action_items에는 담당자와 기한이 원문에 있으면 포함한 실행 항목만 작성하세요. 해당 내용이 없으면 빈 배열을 반환하세요."
        )
        chunk_size = 12000
        chunks = [transcript[index:index + chunk_size] for index in range(0, len(transcript), chunk_size)]
        drafts = [await self._structured_response(system, chunk, "meeting_summary", MEETING_SUMMARY_SCHEMA) for chunk in chunks]
        if len(drafts) == 1:
            return drafts[0]
        return await self._structured_response(
            system + " 여러 구간의 중간 요약을 중복 없이 하나의 최종 회의 요약으로 통합하세요.",
            json.dumps(drafts, ensure_ascii=False),
            "meeting_summary",
            MEETING_SUMMARY_SCHEMA,
        )

    async def extract_decision_candidates(self, transcript: str) -> list[DecisionCandidate]:
        if not settings.openai_api_key:
            raise AppError("OPENAI_API_KEY_MISSING", "OpenAI API key is not configured.", 503)

        payload = {
            "model": settings.decision_analysis_model,
            "input": [
                {
                    "role": "system",
                    "content": [{
                        "type": "input_text",
                        "text": (
                            "당신은 한국어 회의록에서 결정사항 후보만 추출하는 분석가입니다. "
                            "명시적으로 합의, 승인, 확정, 선택, 약속된 내용만 추출하세요. "
                            "제안, 질문, 검토 예정, 단순 의견, 미해결 논의는 제외하세요. "
                            "topic은 짧은 결정 주제, value는 확정된 내용을 실행 가능한 문장으로, "
                            "evidence는 판단 근거가 된 원문 문장으로 작성하세요. "
                            "confidence는 결정의 명시성에 따라 0부터 1 사이로 매기세요. "
                            "결정사항이 없으면 candidates를 빈 배열로 반환하세요."
                        ),
                    }],
                },
                {"role": "user", "content": [{"type": "input_text", "text": transcript}]},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "decision_candidates",
                    "strict": True,
                    "schema": DECISION_SCHEMA,
                }
            },
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    "https://api.openai.com/v1/responses",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                    json=payload,
                )
        except httpx.RequestError as exc:
            raise AppError("AI_ANALYSIS_ERROR", f"OpenAI connection failed: {exc}", 502) from exc

        if response.is_error:
            try:
                message = response.json().get("error", {}).get("message", "OpenAI analysis failed.")
            except ValueError:
                message = "OpenAI analysis failed."
            raise AppError("AI_ANALYSIS_ERROR", message, 502)

        body = response.json()
        output_text = next(
            (
                content["text"]
                for item in body.get("output", [])
                if item.get("type") == "message"
                for content in item.get("content", [])
                if content.get("type") == "output_text"
            ),
            None,
        )
        if not output_text:
            raise AppError("AI_ANALYSIS_ERROR", "OpenAI returned no analysis result.", 502)

        try:
            result = json.loads(output_text)
            return [DecisionCandidate.model_validate(item) for item in result["candidates"]]
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise AppError("AI_ANALYSIS_ERROR", "OpenAI returned an invalid analysis result.", 502) from exc

    async def analyze_meeting(self, meeting: MeetingDetail) -> dict:
        candidates = await self.extract_decision_candidates(meeting.transcript or "")
        return {
            "meeting_id": meeting.id,
            "summary": meeting.summary,
            "discussion": meeting.discussion,
            "decision_candidates": [candidate.model_dump() for candidate in candidates],
        }


ai_service = AIService()
