import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import SessionModel, ParticipantModel
from app.dependencies import require_session_participant, get_current_participant
from app.schemas import (
    AgreementResponse,
    AgreementConfirmRequest,
    AgreementConfirmResponse
)
from app.services import agreement_service

router = APIRouter(tags=["Agreements"])


@router.post(
    "/api/sessions/{session_id}/agreement",
    response_model=AgreementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate and persist shared agreement",
    description="Generates a structured checklist of confirmed requirements, unresolved decisions, and suggestions."
)
def generate_agreement_endpoint(
    session_data: tuple[SessionModel, ParticipantModel] = Depends(require_session_participant),
    db: Session = Depends(get_db)
):
    session, _ = session_data
    return agreement_service.generate_agreement(db=db, session=session)


@router.post(
    "/api/agreements/{agreement_id}/confirm",
    response_model=AgreementConfirmResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm shared agreement",
    description="Records participant approval. Automatically marks session completed once all submitting participants confirm."
)
def confirm_agreement_endpoint(
    agreement_id: uuid.UUID,
    payload: AgreementConfirmRequest,
    participant: ParticipantModel = Depends(get_current_participant),
    db: Session = Depends(get_db)
):
    return agreement_service.confirm_agreement(
        db=db,
        agreement_id=agreement_id,
        participant=participant,
        confirmed=payload.confirmed,
        comment=payload.comment
    )
