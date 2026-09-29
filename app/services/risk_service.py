from datetime import date, datetime

from app.models.action_item import ActionItem
from app.models.enums import ActionStatus, Priority, RiskLevel


class RiskService:
    def score(self, item: ActionItem, today: date | None = None) -> tuple[int, RiskLevel]:
        today = today or date.today()
        score = 0

        if item.due_date and item.due_date < today and item.status not in {ActionStatus.done, ActionStatus.cancelled}:
            score += 40
        if item.priority == Priority.high:
            score += 20
        if item.status_changed_at and (datetime.utcnow() - item.status_changed_at).days >= 3:
            score += 20

        score = min(score, 100)
        if score <= 30:
            return score, RiskLevel.low
        if score <= 60:
            return score, RiskLevel.medium
        return score, RiskLevel.high


risk_service = RiskService()

