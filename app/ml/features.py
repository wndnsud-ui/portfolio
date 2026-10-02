from datetime import date, datetime
from typing import TypedDict

from app.models.action_item import ActionItem


class ActionItemFeatures(TypedDict):
    days_until_due: int | None
    priority: str
    task_age_days: int
    days_without_status_change: int
    project_duration_days: int
    open_task_count: int
    assignee_open_task_count: int
    previous_delay_rate: float
    meeting_frequency_30d: float
    decision_change_count: int


def build_features(
    item: ActionItem,
    *,
    as_of: date | None = None,
    project_duration_days: int = 0,
    open_task_count: int = 0,
    assignee_open_task_count: int = 0,
    previous_delay_rate: float = 0.0,
    meeting_frequency_30d: float = 0.0,
    decision_change_count: int = 0,
) -> ActionItemFeatures:
    reference = as_of or date.today()
    created_date = item.created_at.date() if item.created_at else reference
    status_changed = item.status_changed_at or item.created_at or datetime.combine(reference, datetime.min.time())
    return {
        "days_until_due": (item.due_date - reference).days if item.due_date else None,
        "priority": getattr(item.priority, "value", str(item.priority)),
        "task_age_days": max((reference - created_date).days, 0),
        "days_without_status_change": max((reference - status_changed.date()).days, 0),
        "project_duration_days": max(project_duration_days, 0),
        "open_task_count": max(open_task_count, 0),
        "assignee_open_task_count": max(assignee_open_task_count, 0),
        "previous_delay_rate": min(max(previous_delay_rate, 0.0), 1.0),
        "meeting_frequency_30d": max(meeting_frequency_30d, 0.0),
        "decision_change_count": max(decision_change_count, 0),
    }
