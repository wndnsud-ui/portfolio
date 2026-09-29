from app.models.action_item import ActionItem
from app.services.ml_service import ml_service


def predict(item: ActionItem) -> tuple[float, str, str]:
    probability, level, version = ml_service.predict_delay_risk(item)
    return probability, level.value, version

