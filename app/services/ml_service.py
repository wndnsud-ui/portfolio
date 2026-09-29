from app.models.action_item import ActionItem
from app.models.enums import RiskLevel
from app.services.risk_service import risk_service


class MLService:
    model_version = "rule-v1"

    def predict_delay_risk(self, item: ActionItem) -> tuple[float, RiskLevel, str]:
        score, level = risk_service.score(item)
        return score / 100, level, self.model_version


ml_service = MLService()

