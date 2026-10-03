from app.services.integration_context import integration_value
from collections.abc import Iterable
from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import AppError
from app.models.action_item import ActionItem
from app.models.decision import Decision
from app.models.meeting import Meeting


class NotionService:
    base_url = "https://api.notion.com/v1"

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {integration_value('notion_api_key')}",
            "Notion-Version": settings.notion_api_version,
            "Content-Type": "application/json",
        }

    def status(self) -> dict[str, bool | str]:
        connected = bool(integration_value('notion_api_key') and integration_value('notion_database_id'))
        return {"connected": connected, "mode": "developer-token" if connected else "not-connected"}

    def _require_config(self) -> None:
        if not integration_value('notion_api_key') or not integration_value('notion_database_id'):
            raise AppError("NOTION_CONNECTION_ERROR", "Notion API key or database ID is not configured.", 400)

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        self._require_config()
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.request(method, f"{self.base_url}{path}", headers=self.headers, **kwargs)
        except httpx.RequestError as exc:
            raise AppError("NOTION_CONNECTION_ERROR", "Notion API에 연결하지 못했습니다.", 502) from exc

        if response.is_error:
            try:
                message = response.json().get("message")
            except ValueError:
                message = None
            raise AppError("NOTION_SYNC_ERROR", message or "Notion 요청에 실패했습니다.", 502)
        return response.json()

    async def connection_info(self) -> dict[str, Any]:
        database = await self._request("GET", f"/databases/{integration_value('notion_database_id')}")
        data_sources = database.get("data_sources", [])
        if not data_sources:
            raise AppError("NOTION_DATABASE_ERROR", "Notion 데이터베이스에 데이터 소스가 없습니다.", 422)
        return {
            "connected": True,
            "database_id": database["id"],
            "database_title": "".join(item.get("plain_text", "") for item in database.get("title", [])).strip(),
            "data_source_id": data_sources[0]["id"],
        }

    @staticmethod
    def _rich_text(text: str) -> list[dict[str, Any]]:
        return [{"type": "text", "text": {"content": text[:2000]}}]

    @classmethod
    def _paragraphs(cls, text: str) -> Iterable[dict[str, Any]]:
        normalized = text.strip() or "내용 없음"
        for start in range(0, len(normalized), 1900):
            yield {"object": "block", "type": "paragraph", "paragraph": {"rich_text": cls._rich_text(normalized[start:start + 1900])}}

    @classmethod
    def _heading(cls, text: str) -> dict[str, Any]:
        return {"object": "block", "type": "heading_2", "heading_2": {"rich_text": cls._rich_text(text)}}

    @classmethod
    def _bullet(cls, text: str) -> dict[str, Any]:
        return {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": cls._rich_text(text)}}

    async def sync_meeting(
        self,
        meeting: Meeting,
        project_name: str,
        decisions: list[Decision],
        action_items: list[ActionItem],
    ) -> dict[str, str | int]:
        info = await self.connection_info()
        properties: dict[str, Any] = {
            "Meeting Title": {"title": self._rich_text(meeting.title)},
            "Project": {"rich_text": self._rich_text(project_name)},
            "Meeting Date": {"date": {"start": meeting.meeting_date.isoformat()}},
            "Participants": {"rich_text": self._rich_text(", ".join(meeting.participants))},
        }
        children: list[dict[str, Any]] = [
            self._heading("회의 요약"),
            *self._paragraphs(meeting.summary or "요약이 아직 작성되지 않았습니다."),
            self._heading("핵심 쟁점"),
            *self._paragraphs(meeting.discussion or "주요 논의사항이 아직 작성되지 않았습니다."),
            self._heading("미결 사항"),
        ]
        children.extend(self._bullet(item) for item in meeting.undecided_topics)
        if not meeting.undecided_topics:
            children.extend(self._paragraphs("등록된 미결 사항이 없습니다."))
        children.append(self._heading("결정사항"))
        children.extend(self._bullet(f"{item.topic}: {item.value}") for item in decisions)
        if not decisions:
            children.extend(self._paragraphs("등록된 결정사항이 없습니다."))
        children.append(self._heading("후속 액션"))
        children.extend(
            self._bullet(
                f"{item.task} · 담당 {item.assignee or '미지정'} · 기한 {item.due_date or '미정'} · {getattr(item.status, 'value', item.status)}"
            )
            for item in action_items
        )
        if not action_items:
            children.extend(self._paragraphs("등록된 Action Item이 없습니다."))
        result = await self._request(
            "POST",
            "/pages",
            json={
                "parent": {"type": "data_source_id", "data_source_id": info["data_source_id"]},
                "properties": properties,
                "children": children[:100],
            },
        )
        return {
            "meeting_id": meeting.id,
            "status": "SYNCED",
            "notion_page_id": result["id"],
            "url": result.get("url", ""),
        }


notion_service = NotionService()
