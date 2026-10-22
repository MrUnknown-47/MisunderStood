import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import SessionModel, ParticipantModel
from app.dependencies import require_session_participant
from app.schemas import BridgeTestMetrics
from app.services import bridge_test_service

router = APIRouter(prefix="/api/sessions", tags=["Bridge Test"])


@router.get(
    "/{session_id}/bridge-test",
    response_model=BridgeTestMetrics,
    summary="Calculate Bridge Test metrics",
    description="Calculates initial, resolved, unresolved, and dismissed issue counts, resolution percentage, and agreement state."
)
def get_bridge_test_endpoint(
    session_data: tuple[SessionModel, ParticipantModel] = Depends(require_session_participant),
    db: Session = Depends(get_db)
):
    session, _ = session_data
    return bridge_test_service.calculate_bridge_test(db=db, session=session)
