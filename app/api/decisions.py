from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.meetings import get_meeting_or_404
from app.api.projects import get_project_or_404
from app.core.exceptions import AppError
from app.db.session import get_db
from app.models.decision import Decision, DecisionHistory
from app.schemas.decision import DecisionCreate, DecisionRead, DecisionUpdate

router = APIRouter(tags=["Decisions"])


def get_decision_or_404(db: Session, decision_id: int) -> Decision:
    decision = db.get(Decision, decision_id)
    if not decision:
        raise AppError("DECISION_NOT_FOUND", "Decision not found.", 404)
    return decision


@router.post("/decisions", response_model=DecisionRead)
async def create_decision(payload: DecisionCreate, db: Session = Depends(get_db)) -> Decision:
    get_project_or_404(db, payload.project_id)
    if payload.meeting_id:
        get_meeting_or_404(db, payload.meeting_id)
    decision = Decision(**payload.model_dump())
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return decision


@router.get("/projects/{project_id}/decisions", response_model=list[DecisionRead])
async def list_project_decisions(project_id: int, db: Session = Depends(get_db)) -> list[Decision]:
    get_project_or_404(db, project_id)
    return db.query(Decision).filter(Decision.project_id == project_id).order_by(Decision.updated_at.desc()).all()


@router.get("/decisions/{decision_id}", response_model=DecisionRead)
async def read_decision(decision_id: int, db: Session = Depends(get_db)) -> Decision:
    return get_decision_or_404(db, decision_id)


@router.patch("/decisions/{decision_id}", response_model=DecisionRead)
async def update_decision(decision_id: int, payload: DecisionUpdate, db: Session = Depends(get_db)) -> Decision:
    decision = get_decision_or_404(db, decision_id)
    data = payload.model_dump(exclude_unset=True)
    if "value" in data and data["value"] != decision.value:
        db.add(DecisionHistory(decision_id=decision.id, meeting_id=data.get("meeting_id", decision.meeting_id), previous_value=decision.value, new_value=data["value"]))
    for key, value in data.items():
        setattr(decision, key, value)
    db.commit()
    db.refresh(decision)
    return decision


@router.delete("/decisions/{decision_id}", status_code=204)
async def delete_decision(decision_id: int, db: Session = Depends(get_db)) -> None:
    decision = get_decision_or_404(db, decision_id)
    db.delete(decision)
    db.commit()
