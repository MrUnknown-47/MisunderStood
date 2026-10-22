import uuid
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models import SessionModel, ParticipantModel, InterpretationModel
from app.schemas import InterpretationResponse


def submit_interpretation(
    db: Session,
    session: SessionModel,
    participant: ParticipantModel,
    response_text: str,
    assumptions: Optional[List[str]] = None,
    success_criteria: Optional[List[str]] = None
) -> InterpretationResponse:
    """Submit an independent interpretation with strict state and privacy checks."""
    # 1. State check: only allowed during collecting_responses
    if session.status != "collecting_responses":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot submit interpretation: session is in '{session.status}' state."
        )

    # 2. Text validation
    clean_text = response_text.strip()
    if not clean_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT if hasattr(status, "HTTP_422_UNPROCESSABLE_CONTENT") else 422,
            detail="Interpretation text cannot be blank."
        )

    # 3. Duplicate submission check
    existing = db.query(InterpretationModel).filter(
        InterpretationModel.session_id == session.id,
        InterpretationModel.participant_id == participant.id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already submitted an interpretation for this session."
        )

    # 4. Save and commit
    interpretation = InterpretationModel(
        session_id=session.id,
        participant_id=participant.id,
        response_text=clean_text,
        assumptions=assumptions or [],
        success_criteria=success_criteria or []
    )
    db.add(interpretation)
    db.commit()
    db.refresh(interpretation)

    return InterpretationResponse(
        interpretation_id=interpretation.id,
        submitted=True,
        message="Your interpretation has been saved."
    )


def has_participant_submitted(db: Session, session_id: uuid.UUID, participant_id: uuid.UUID) -> bool:
    """Check whether a participant has submitted an interpretation."""
    return db.query(InterpretationModel).filter(
        InterpretationModel.session_id == session_id,
        InterpretationModel.participant_id == participant_id
    ).first() is not None
