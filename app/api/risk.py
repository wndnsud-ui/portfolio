from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.action_items import get_action_item_or_404
from app.api.projects import get_project_or_404
from app.db.session import get_db
from app.models.action_item import ActionItem, ActionItemPrediction
from app.models.enums import RiskLevel
from app.schemas.action_item import PredictionRead, RiskRead
from app.services.ml_service import ml_service
from app.services.risk_service import risk_service

router = APIRouter(tags=["Risk"])


@router.get("/action-items/{action_item_id}/risk", response_model=RiskRead)
async def read_action_item_risk(action_item_id: int, db: Session = Depends(get_db)) -> RiskRead:
    item = get_action_item_or_404(db, action_item_id)
    score, level = risk_service.score(item)
    return RiskRead(action_item_id=item.id, risk_score=score, risk_level=level)


@router.post("/action-items/{action_item_id}/predict-risk", response_model=PredictionRead)
async def predict_action_item_risk(action_item_id: int, db: Session = Depends(get_db)) -> PredictionRead:
    item = get_action_item_or_404(db, action_item_id)
    probability, level, version = ml_service.predict_delay_risk(item)
    db.add(
        ActionItemPrediction(
            action_item_id=item.id,
            delay_probability=round(probability * 100),
            risk_level=level,
            model_version=version,
        )
    )
    db.commit()
    return PredictionRead(action_item_id=item.id, delay_probability=probability, risk_level=level, model_version=version)


@router.get("/projects/{project_id}/risk-items", response_model=list[PredictionRead])
async def list_project_risk_items(project_id: int, db: Session = Depends(get_db)) -> list[PredictionRead]:
    get_project_or_404(db, project_id)
    items = db.query(ActionItem).filter(ActionItem.project_id == project_id, ActionItem.risk_level == RiskLevel.high).all()
    return [
        PredictionRead(
            action_item_id=item.id,
            delay_probability=item.risk_score / 100,
            risk_level=item.risk_level,
            model_version=ml_service.model_version,
        )
        for item in items
    ]

