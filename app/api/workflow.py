from datetime import date, datetime
from datetime import timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
import re
from uuid import uuid4

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.deps import get_current_user
from app.api.meetings import get_meeting_or_404, to_detail
from app.api.projects import get_project_or_404
from app.core.config import settings
from app.core.exceptions import AppError
from app.db.session import get_db
from app.models.action_item import ActionItem
from app.models.decision import Decision
from app.models.meeting import Meeting
from app.models.project import Project
from app.models.user import User
from app.models.workflow import ActivityLog, CommentMention, FinalResult, MeetingReview, Notification, TaskAttachment, TaskComment, TaskProgress, TaskReview
from app.models.workflow import TranscriptionJob
from app.schemas.action_item import ActionItemRead
from app.services.permissions import is_project_manager, require_meeting_editor, require_project_manager, require_task_access, visible_projects, workspace_role
from app.services.workflow_service import activity, notify, project_users, transition
from app.services.risk_service import risk_service

router = APIRouter(tags=["Workflow"])


class Content(BaseModel):
    content: str = Field(default="", max_length=20000)


class ProgressContent(Content):
    progress_percent: int | None = Field(default=None, ge=0, le=100, strict=True)


class Speakers(BaseModel):
    speaker_names: dict[str, str]


def record(value):
    return jsonable_encoder({c.name: getattr(value, c.name) for c in value.__table__.columns if c.name != "storage_key"})


def get_task(db, tid, user):
    task = db.get(ActionItem, tid)
    if not task:
        raise AppError("TASK_NOT_FOUND", "Task not found.", 404)
    require_task_access(db, task, user.id)
    return task


def editable_meeting(db, mid, user):
    meeting = get_meeting_or_404(db, mid, user, lock=True)
    require_meeting_editor(db, meeting, user.id)
    if db.query(TranscriptionJob).filter_by(meeting_id=mid, status="ANALYZING").first():
        raise AppError("ANALYSIS_BUSY", "AI analysis is already running.", 409)
    if meeting.report_status in {"APPROVED", "PUBLISHED"} or (meeting.report_status == "MANAGER_REVIEW" and not is_project_manager(db, meeting.project, user.id)):
        raise AppError("REVIEW_LOCKED", "Return this meeting for changes before editing.", 409)
    return meeting


def mapped_transcript(meeting):
    text = meeting.transcript.content if meeting.transcript else ""
    if not meeting.speaker_names:
        return text
    pattern = "|".join(re.escape(k) for k in sorted(meeting.speaker_names, key=len, reverse=True))
    return re.sub(r"(?<!\w)(?:" + pattern + r")(?!\w)", lambda match: meeting.speaker_names[match.group()], text)


@router.get("/meetings/{meeting_id}/speakers")
def get_speakers(meeting_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    meeting = get_meeting_or_404(db, meeting_id, user)
    text = meeting.transcript.content if meeting.transcript else ""
    labels = set(re.findall(r"(?:Speaker\s+\d+|화자\s+\d+(?:\s*\(구간\s+\d+\))?)", text))
    return {"speaker_names": meeting.speaker_names, "labels": sorted(labels), "transcript": mapped_transcript(meeting)}


@router.patch("/meetings/{meeting_id}/speakers")
def set_speakers(meeting_id: int, payload: Speakers, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    meeting = editable_meeting(db, meeting_id, user)
    if any(not k.strip() or not v.strip() or len(k) > 120 or len(v) > 120 for k, v in payload.speaker_names.items()):
        raise AppError("INVALID_SPEAKER", "Speaker label and name are required.", 400)
    meeting.speaker_names = payload.speaker_names
    db.commit()
    return {"speaker_names": meeting.speaker_names, "transcript": mapped_transcript(meeting)}


def meeting_action(mid, name, payload, db, user):
    meeting = get_meeting_or_404(db, mid, user, lock=True)
    if name == "submit-review":
        require_meeting_editor(db, meeting, user.id)
        allowed, destination = {"AI_ANALYZED", "RECORDER_REVIEW", "CHANGES_REQUESTED"}, "MANAGER_REVIEW"
        recipients, event = project_users(db, meeting.project_id, True), "meeting_review_requested"
    else:
        require_project_manager(db, db.get(Project, meeting.project_id), user.id)
        if name == "approve":
            allowed, destination, event = {"MANAGER_REVIEW"}, "APPROVED", "meeting_approved"
        elif name in {"request-changes", "reject"}:
            if not payload.content.strip():
                raise AppError("REASON_REQUIRED", "A review reason is required.", 400)
            allowed, destination, event = {"MANAGER_REVIEW", "APPROVED"}, "CHANGES_REQUESTED", "meeting_changes_requested"
        else:
            allowed, destination, event = {"APPROVED"}, "PUBLISHED", "meeting_published"
        recipients = project_users(db, meeting.project_id) if destination == "PUBLISHED" else [meeting.recorder_id or meeting.user_id]
    previous = transition(db, meeting, "report_status", allowed, destination)
    meeting.analysis_status = "confirmed" if destination in {"APPROVED", "PUBLISHED"} else "draft"
    db.add(MeetingReview(meeting_id=mid, actor_id=user.id, action=name,
        previous_status=previous, new_status=destination, content=payload.content))
    activity(db, meeting.project_id, user.id, event, "meeting", mid, payload.content)
    notify(db, recipients, event, meeting.title, "meeting", mid, payload.content, user.id)
    db.commit()
    return to_detail(meeting)


def register_meeting_action(name):
    def endpoint(meeting_id: int, payload: Content = Content(), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
        return meeting_action(meeting_id, name, payload, db, user)
    endpoint.__name__ = "meeting_" + name.replace("-", "_")
    router.add_api_route("/meetings/{meeting_id}/" + name, endpoint, methods=["POST"])


for _name in ["submit-review", "approve", "request-changes", "reject", "publish"]:
    register_meeting_action(_name)


@router.get("/meetings/{meeting_id}/reviews")
def meeting_reviews(meeting_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_meeting_or_404(db, meeting_id, user)
    return [record(r) for r in db.query(MeetingReview).filter_by(meeting_id=meeting_id).order_by(MeetingReview.created_at).all()]


@router.get("/tasks", response_model=list[ActionItemRead])
def tasks(project_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(ActionItem).filter(ActionItem.project_id.in_(visible_projects(db, user.id)))
    if project_id:
        query = query.filter(ActionItem.project_id == project_id)
    return [t for t in query.order_by(ActionItem.created_at.desc()).all()
            if t.assignee_id == user.id or is_project_manager(db, db.get(Project, t.project_id), user.id)]


@router.get("/tasks/{task_id}")
def task_detail(task_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = get_task(db, task_id, user)
    result = record(task)
    result["can_manage"] = is_project_manager(db, db.get(Project, task.project_id), user.id)
    for key, model in [("progress", TaskProgress), ("comments", TaskComment), ("attachments", TaskAttachment), ("reviews", TaskReview)]:
        query = db.query(model).filter(model.task_id == task_id)
        if model == TaskComment:
            query = query.filter(TaskComment.deleted_at.is_(None))
        rows = []
        for value in query.order_by(model.created_at).all():
            item = record(value)
            uid = getattr(value, "user_id", getattr(value, "actor_id", getattr(value, "uploaded_by", None)))
            author = db.get(User, uid) if uid else None
            item["author"] = (author.nickname or author.email) if author else ""
            rows.append(item)
        result[key] = rows
    result["activity"] = [record(r) for r in db.query(ActivityLog).filter_by(target_type="task", target_id=task_id).order_by(ActivityLog.created_at).all()]
    return result


def task_action(tid, name, payload, db, user):
    task = get_task(db, tid, user)
    management = name in {"approve", "request-changes", "reject"}
    if management:
        require_project_manager(db, db.get(Project, task.project_id), user.id)
    elif task.assignee_id != user.id:
        raise AppError("FORBIDDEN", "Only the assignee can perform this action.", 403)
    transitions = {
        "accept": ({"ASSIGNED"}, "ACCEPTED", "task_accepted"),
        "start": ({"ACCEPTED", "BLOCKED", "CHANGES_REQUESTED"}, "IN_PROGRESS", "task_started"),
        "block": ({"IN_PROGRESS"}, "BLOCKED", "task_blocked"),
        "submit-review": ({"IN_PROGRESS"}, "READY_FOR_REVIEW", "task_review_requested"),
        "approve": ({"READY_FOR_REVIEW"}, "APPROVED", "task_approved"),
        "request-changes": ({"READY_FOR_REVIEW"}, "CHANGES_REQUESTED", "task_changes_requested"),
        "reject": ({"ASSIGNED", "ACCEPTED", "IN_PROGRESS", "BLOCKED", "READY_FOR_REVIEW", "CHANGES_REQUESTED"}, "CANCELLED", "task_cancelled"),
    }
    if name == "request-reassignment":
        if task.workflow_status in {None, "APPROVED", "CANCELLED"}:
            raise AppError("INVALID_TRANSITION", "This task cannot be reassigned.", 409)
        if not payload.content.strip():
            raise AppError("REASON_REQUIRED", "A reassignment reason is required.", 400)
        db.add(TaskReview(task_id=tid, actor_id=user.id, action=name, previous_status=task.workflow_status, new_status=task.workflow_status, content=payload.content))
        activity(db, task.project_id, user.id, "task_reassignment_requested", "task", tid, payload.content)
        notify(db, project_users(db, task.project_id, True), "task_reassignment_requested", task.task, "task", tid, payload.content, user.id)
        db.commit()
        return record(task)
    if name in {"submit-review", "request-changes", "reject", "block"} and not payload.content.strip():
        raise AppError("CONTENT_REQUIRED", "Result or reason is required.", 400)
    allowed, destination, event = transitions[name]
    previous = transition(db, task, "workflow_status", allowed, destination)
    task.status = "done" if destination == "APPROVED" else "cancelled" if destination == "CANCELLED" else "in_progress" if destination not in {"ASSIGNED", "ACCEPTED"} else "todo"
    task.status_changed_at = datetime.utcnow()
    task.completed_at = datetime.utcnow() if destination == "APPROVED" else None
    task.risk_score, task.risk_level = risk_service.score(task)
    db.add(TaskReview(task_id=tid, actor_id=user.id, action=name, previous_status=previous, new_status=destination, content=payload.content))
    activity(db, task.project_id, user.id, event, "task", tid, payload.content)
    notify(db, [task.assignee_id] if management else project_users(db, task.project_id, True), event, task.task, "task", tid, payload.content, user.id)
    if destination == "APPROVED":
        submitted = db.query(TaskReview).filter_by(task_id=tid, action="submit-review").order_by(TaskReview.id.desc()).first()
        db.add(FinalResult(task_id=tid, project_id=task.project_id, approved_by=user.id, title=task.task, content=submitted.content if submitted else payload.content, assignee_id=task.assignee_id))
        activity(db, task.project_id, user.id, "final_result_published", "task", tid)
    db.commit()
    return record(task)


def register_task_action(name):
    def endpoint(task_id: int, payload: Content = Content(), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
        return task_action(task_id, name, payload, db, user)
    endpoint.__name__ = "task_" + name.replace("-", "_")
    router.add_api_route("/tasks/{task_id}/" + name, endpoint, methods=["POST"])


for _name in ["accept", "start", "block", "request-reassignment", "submit-review", "approve", "request-changes", "reject"]:
    register_task_action(_name)


@router.get("/tasks/{task_id}/progress")
def task_progress(task_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return task_detail(task_id, db, user)["progress"]


@router.post("/tasks/{task_id}/progress", status_code=201)
def add_progress(task_id: int, payload: ProgressContent, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = get_task(db, task_id, user)
    if task.assignee_id != user.id or task.workflow_status not in {"ACCEPTED", "IN_PROGRESS", "BLOCKED", "CHANGES_REQUESTED"}:
        raise AppError("FORBIDDEN", "Only an active task assignee can add progress.", 403)
    if not payload.content.strip():
        raise AppError("CONTENT_REQUIRED", "Progress is required.", 400)
    progress = TaskProgress(task_id=task_id, user_id=user.id, content=payload.content.strip())
    if payload.progress_percent is not None:
        task.progress_percent = payload.progress_percent
    task.progress_content = payload.content.strip()
    task.progress_updated_at = datetime.utcnow()
    db.add(progress)
    activity(db, task.project_id, user.id, "task_progress_added", "task", task_id)
    db.commit()
    return record(progress)


def sync_mentions(db, comment, task, user):
    names = set(re.findall(r"@([^\s,;]+)", comment.content))
    for person in db.query(User).filter(User.id.in_(project_users(db, task.project_id))).all():
        if person.nickname in names or person.email in names:
            if not db.query(CommentMention).filter_by(comment_id=comment.id, mentioned_user_id=person.id).first():
                db.add(CommentMention(comment_id=comment.id, mentioned_user_id=person.id))
                notify(db, [person.id], "task_mention", task.task, "task", task.id, comment.content, user.id)


@router.get("/tasks/{task_id}/comments")
def comments(task_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return task_detail(task_id, db, user)["comments"]


@router.post("/tasks/{task_id}/comments", status_code=201)
def add_comment(task_id: int, payload: Content, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = get_task(db, task_id, user)
    if not payload.content.strip():
        raise AppError("CONTENT_REQUIRED", "Comment is required.", 400)
    comment = TaskComment(task_id=task_id, user_id=user.id, content=payload.content.strip())
    db.add(comment)
    db.flush()
    sync_mentions(db, comment, task, user)
    notify(db, [task.assignee_id, *project_users(db, task.project_id, True)], "task_comment", task.task, "task", task_id, comment.content, user.id)
    activity(db, task.project_id, user.id, "task_commented", "task", task_id)
    db.commit()
    return record(comment)


def own_comment(db, cid, user):
    comment = db.get(TaskComment, cid)
    if not comment or comment.deleted_at:
        raise AppError("COMMENT_NOT_FOUND", "Comment not found.", 404)
    get_task(db, comment.task_id, user)
    if comment.user_id != user.id:
        raise AppError("FORBIDDEN", "Only the author can change a comment.", 403)
    return comment


@router.patch("/task-comments/{comment_id}")
def edit_comment(comment_id: int, payload: Content, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    comment = own_comment(db, comment_id, user)
    if not payload.content.strip():
        raise AppError("CONTENT_REQUIRED", "Comment is required.", 400)
    comment.content = payload.content.strip()
    sync_mentions(db, comment, db.get(ActionItem, comment.task_id), user)
    db.commit()
    return record(comment)


@router.delete("/task-comments/{comment_id}", status_code=204)
def delete_comment(comment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    own_comment(db, comment_id, user).deleted_at = datetime.utcnow()
    db.commit()


@router.post("/tasks/{task_id}/attachments", status_code=201)
async def add_attachment(task_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_task(db, task_id, user)
    filename = Path((file.filename or "file").replace("\\", "/")).name
    extension = Path(filename).suffix.lower()
    if extension not in {".pdf", ".docx", ".xlsx", ".png", ".jpg", ".jpeg", ".txt", ".md"}:
        raise AppError("UNSUPPORTED_FILE", "Unsupported attachment type.", 415)
    data = await file.read(20 * 1024 * 1024 + 1)
    if not data or len(data) > 20 * 1024 * 1024:
        raise AppError("FILE_SIZE", "Attachment must be between 1 byte and 20 MB.", 413)
    root = Path(settings.attachment_dir)
    root.mkdir(parents=True, exist_ok=True)
    key = uuid4().hex + extension
    path = root / key
    path.write_bytes(data)
    attachment = TaskAttachment(task_id=task_id, uploaded_by=user.id, file_name=filename[:255], storage_key=key, file_type=extension, size=len(data))
    try:
        db.add(attachment)
        db.commit()
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return record(attachment)


@router.get("/task-attachments/{attachment_id}")
def download_attachment(attachment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    attachment = db.get(TaskAttachment, attachment_id)
    if not attachment:
        raise AppError("FILE_NOT_FOUND", "Attachment not found.", 404)
    get_task(db, attachment.task_id, user)
    path = Path(settings.attachment_dir) / attachment.storage_key
    if not path.is_file():
        raise AppError("FILE_NOT_FOUND", "Attachment file unavailable.", 404)
    return FileResponse(path, filename=attachment.file_name, media_type="application/octet-stream", headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@router.delete("/task-attachments/{attachment_id}", status_code=204)
def remove_attachment(attachment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    attachment = db.get(TaskAttachment, attachment_id)
    if not attachment:
        raise AppError("FILE_NOT_FOUND", "Attachment not found.", 404)
    task = get_task(db, attachment.task_id, user)
    if attachment.uploaded_by != user.id and not is_project_manager(db, task.project, user.id):
        raise AppError("FORBIDDEN", "Only uploader or project manager can delete files.", 403)
    key = attachment.storage_key
    db.delete(attachment)
    db.commit()
    (Path(settings.attachment_dir) / key).unlink(missing_ok=True)


@router.get("/notifications")
def notifications(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    today = datetime.now(ZoneInfo("Asia/Seoul")).date()
    example_ids = {p.id for p in db.query(Project).filter_by(user_id=user.id, is_example=True)}
    for task in tasks(None, db, user):
        if task.project_id in example_ids:
            continue
        if task.assignee_id == user.id and task.due_date and today <= task.due_date <= today + timedelta(days=1) and task.status not in {"done", "cancelled"}:
            key = f"task_due_soon:{task.id}:{user.id}:{task.due_date}"
            if not db.query(Notification).filter_by(dedup_key=key).first():
                try:
                    with db.begin_nested():
                        db.add(Notification(user_id=user.id, type="task_due_soon", title=task.task, message=f"마감일: {task.due_date}", target_type="task", target_id=task.id, dedup_key=key))
                        db.flush()
                except IntegrityError:
                    pass
    db.commit()
    return [record(n) for n in db.query(Notification).filter_by(user_id=user.id).order_by(Notification.created_at.desc()).limit(200).all()]


@router.patch("/notifications/{notification_id}/read")
def read_notification(notification_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.query(Notification).filter_by(id=notification_id, user_id=user.id).first()
    if not item:
        raise AppError("NOTIFICATION_NOT_FOUND", "Notification not found.", 404)
    item.is_read = True
    db.commit()
    return record(item)


@router.post("/notifications/read-all")
def read_all(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.query(Notification).filter_by(user_id=user.id, is_read=False).update({"is_read": True})
    db.commit()
    return {"status": "ok"}


@router.get("/projects/{project_id}/final-results")
def final_results(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_project_or_404(db, project_id, user)
    result = []
    for value in db.query(FinalResult).filter_by(project_id=project_id).order_by(FinalResult.created_at.desc()).all():
        row = record(value)
        approver = db.get(User, value.approved_by)
        assignee = db.get(User, value.assignee_id) if value.assignee_id else None
        row["approved_name"] = approver.nickname or approver.email
        row["assignee_name"] = (assignee.nickname or assignee.email) if assignee else "미지정"
        result.append(row)
    return result


@router.get("/projects/{project_id}/follow-up")
def follow_up(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_project_or_404(db, project_id, user)
    task_list = tasks(project_id, db, user)
    return {"unfinished": [record(t) for t in task_list if (t.workflow_status or t.status) not in {"APPROVED", "CANCELLED", "done", "cancelled"}], "final_results": final_results(project_id, db, user)[:20]}


@router.get("/workspaces/{workspace_id}/dashboard")
def dashboard(workspace_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    role = workspace_role(db, workspace_id, user.id)
    ids = [p.id for p in db.query(Project).filter(Project.workspace_id == workspace_id, Project.id.in_(visible_projects(db, user.id))).all()]
    items = [t for t in tasks(None, db, user) if t.project_id in ids]
    meetings = db.query(Meeting).filter(Meeting.project_id.in_(ids)).all()
    today = datetime.now(ZoneInfo("Asia/Seoul")).date()
    return {"role": role, "kpis": {
        "meeting_review": sum(m.report_status == "MANAGER_REVIEW" for m in meetings),
        "assigned": sum(t.workflow_status == "ASSIGNED" for t in items),
        "in_progress": sum(t.workflow_status == "IN_PROGRESS" for t in items),
        "review": sum(t.workflow_status == "READY_FOR_REVIEW" for t in items),
        "completed": sum(t.workflow_status == "APPROVED" for t in items),
        "changes": sum(t.workflow_status == "CHANGES_REQUESTED" for t in items),
        "due_today": sum(t.due_date == today for t in items),
        "overdue": sum(bool(t.due_date and t.due_date < today and t.status not in {"done", "cancelled"}) for t in items),
        "unconfirmed_decisions": db.query(Decision).filter(Decision.project_id.in_(ids), Decision.status != "confirmed").count(),
    }, "recorder_meetings": [record(m) for m in meetings if m.recorder_id == user.id],
        "review_meetings": [record(m) for m in meetings if m.report_status == "MANAGER_REVIEW"] if role != "MEMBER" else [],
        "tasks": [record(t) for t in items],
        "team_workload": [{"user_id": person.id, "name": person.nickname or person.email,
            "assigned": sum(t.assignee_id == person.id and t.workflow_status == "ASSIGNED" for t in items),
            "active": sum(t.assignee_id == person.id and t.workflow_status in {"ACCEPTED", "IN_PROGRESS", "BLOCKED", "CHANGES_REQUESTED"} for t in items),
            "review": sum(t.assignee_id == person.id and t.workflow_status == "READY_FOR_REVIEW" for t in items),
            "approved": sum(t.assignee_id == person.id and t.workflow_status == "APPROVED" for t in items)}
            for person in db.query(User).filter(User.id.in_({t.assignee_id for t in items if t.assignee_id})).all()] if role != "MEMBER" else [],
        "project_progress": [{"id": p.id, "name": p.name, "total": sum(t.project_id == p.id for t in items),
            "approved": sum(t.project_id == p.id and t.status == "done" for t in items)}
            for p in db.query(Project).filter(Project.id.in_(ids)).all()],
        "recent_decisions": [record(d) for d in db.query(Decision).filter(Decision.project_id.in_(ids), Decision.status == "confirmed").order_by(Decision.updated_at.desc()).limit(5).all()]}
