from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.meetings import get_meeting_or_404
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.enums import NotionSyncStatus
from app.models.meeting import Meeting
from app.models.notion import NotionSyncLog
from app.models.project import Project
from app.models.user import User
from app.services.notion_service import notion_service

router = APIRouter(tags=["Notion"])


@router.get("/notion/status")
async def notion_status(current_user: User = Depends(get_current_user)) -> dict:
    return notion_service.status()


@router.post("/notion/connect")
async def notion_connect(current_user: User = Depends(get_current_user)) -> dict:
    return await notion_service.connection_info()


async def sync_one(meeting: Meeting, db: Session) -> dict:
    previous = (
        db.query(NotionSyncLog)
        .filter(NotionSyncLog.meeting_id == meeting.id, NotionSyncLog.status == NotionSyncStatus.synced)
        .order_by(NotionSyncLog.created_at.desc())
        .first()
    )
    if previous and previous.notion_page_id and meeting.notion_sync_status == NotionSyncStatus.synced:
        return {
            "meeting_id": meeting.id,
            "status": "ALREADY_SYNCED",
            "notion_page_id": previous.notion_page_id,
        }

    try:
        result = await notion_service.sync_meeting(
            meeting=meeting,
            project_name=meeting.project.name,
            decisions=list(meeting.decisions),
            action_items=list(meeting.action_items),
        )
        meeting.notion_sync_status = NotionSyncStatus.synced
        db.add(
            NotionSyncLog(
                meeting_id=meeting.id,
                status=NotionSyncStatus.synced,
                notion_page_id=str(result["notion_page_id"]),
            )
        )
        db.commit()
        return result
    except Exception as exc:
        db.rollback()
        meeting.notion_sync_status = NotionSyncStatus.error
        db.add(
            NotionSyncLog(
                meeting_id=meeting.id,
                status=NotionSyncStatus.error,
                error_message=str(exc)[:1000],
            )
        )
        db.commit()
        raise


@router.post("/meetings/{meeting_id}/notion-sync")
async def sync_meeting_to_notion(meeting_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    return await sync_one(get_meeting_or_404(db, meeting_id, current_user), db)


@router.post("/notion/sync-demo")
async def sync_demo_meetings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    demo_projects = {"DecisionFlow MVP", "2026 브랜드 웹사이트", "고객 운영 개선"}
    meetings = db.query(Meeting).join(Project).filter(Project.name.in_(demo_projects), Meeting.user_id == current_user.id).all()
    results = [await sync_one(meeting, db) for meeting in meetings]
    return {"synced": len(results), "results": results}


@router.get("/meetings/{meeting_id}/notion-sync-status")
async def meeting_notion_sync_status(meeting_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict[str, int | str | None]:
    meeting = get_meeting_or_404(db, meeting_id, current_user)
    latest = (
        db.query(NotionSyncLog)
        .filter(NotionSyncLog.meeting_id == meeting_id)
        .order_by(NotionSyncLog.created_at.desc())
        .first()
    )
    return {
        "meeting_id": meeting_id,
        "status": meeting.notion_sync_status,
        "notion_page_id": latest.notion_page_id if latest else None,
    }
