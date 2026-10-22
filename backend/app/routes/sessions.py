from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import AnalysisModel, ParticipantModel, SessionModel
from backend.app.schemas import (
    AnalysisResponse,
    IssueRead,
    ParticipantCreate,
    ParticipantRead,
    SessionCreate,
    SessionRead,
)
from backend.app.services.analysis_service import execute_session_analysis

router = APIRouter(prefix="/sessions", tags=["Sessions"])


def _to_session_read(session: SessionModel) -> SessionRead:
    return SessionRead(
        id=session.id,
        session_code=session.session_code,
        title=session.title,
        description=session.description,
        status=session.status,
        participant_count=len(session.participants),
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.post("", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreate,
    db: Session = Depends(get_db),
) -> SessionRead:
    session = SessionModel(
        title=payload.title,
        description=payload.description,
        status="collecting",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return _to_session_read(session)


@router.get("/{session_id}", response_model=SessionRead)
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
) -> SessionRead:
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )
    return _to_session_read(session)


@router.post(
    "/{session_id}/participants",
    response_model=ParticipantRead,
    status_code=status.HTTP_201_CREATED,
)
def submit_participant_interpretation(
    session_id: str,
    payload: ParticipantCreate,
    db: Session = Depends(get_db),
) -> ParticipantModel:
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )

    participant = (
        db.query(ParticipantModel)
        .filter(
            ParticipantModel.session_id == session_id,
            ParticipantModel.participant_id == payload.participant_id,
        )
        .first()
    )

    if participant:
        participant.name = payload.name
        participant.interpretation = payload.interpretation
        participant.assumptions = payload.assumptions
        participant.success_criteria = payload.success_criteria
    else:
        participant = ParticipantModel(
            session_id=session.id,
            participant_id=payload.participant_id,
            name=payload.name,
            interpretation=payload.interpretation,
            assumptions=payload.assumptions,
            success_criteria=payload.success_criteria,
        )
        db.add(participant)

    db.commit()
    db.refresh(participant)
    return participant


@router.post(
    "/{session_id}/analyze",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
)
async def trigger_analysis(
    session_id: str,
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    return await execute_session_analysis(session_id=session_id, db=db)


@router.get(
    "/{session_id}/analysis",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
)
def get_latest_analysis(
    session_id: str,
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )

    latest_analysis = (
        db.query(AnalysisModel)
        .filter(AnalysisModel.session_id == session_id)
        .order_by(AnalysisModel.created_at.desc())
        .first()
    )
    if not latest_analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No analysis has been performed yet for session '{session_id}'.",
        )

    issues = [IssueRead.model_validate(iss) for iss in session.issues]

    return AnalysisResponse(
        session_id=session.id,
        analysis_id=latest_analysis.id,
        status=latest_analysis.status,
        summary=latest_analysis.summary,
        issues=issues,
        complementary_perspectives=latest_analysis.complementary_perspectives or [],
        issue_counts=latest_analysis.issue_counts or {},
        error_message=latest_analysis.error_message,
        metadata=latest_analysis.metadata_info or {},
    )
