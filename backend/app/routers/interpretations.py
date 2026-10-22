import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import SessionModel, ParticipantModel
from app.dependencies import require_session_participant
from app.schemas import InterpretationCreateRequest, InterpretationResponse
from app.services import interpretation_service

router = APIRouter(prefix="/api/sessions", tags=["Interpretations"])


@router.post(
    "/{session_id}/interpretations",
    response_model=InterpretationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit an independent interpretation",
    description="Submits an individual's interpretation of the task. Only allowed during collecting_responses."
)
def submit_interpretation_endpoint(
    payload: InterpretationCreateRequest,
    session_data: tuple[SessionModel, ParticipantModel] = Depends(require_session_participant),
    db: Session = Depends(get_db)
):
    session, participant = session_data
    return interpretation_service.submit_interpretation(
        db=db,
        session=session,
        participant=participant,
        response_text=payload.response_text,
        assumptions=payload.assumptions,
        success_criteria=payload.success_criteria
    )
