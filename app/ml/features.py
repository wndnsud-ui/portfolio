from app.models.action_item import ActionItem


def build_features(item: ActionItem) -> dict[str, int | str | None]:
    return {
        "priority": item.priority,
        "status": item.status,
        "risk_score": item.risk_score,
        "has_due_date": int(item.due_date is not None),
    }

