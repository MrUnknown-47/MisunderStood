import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import SessionModel, ParticipantModel
from app.dependencies import require_session_participant
from app.schemas import (
    SessionCreateRequest,
    SessionCreateResponse,
    SessionJoinRequest,
    SessionJoinResponse,
    SessionDetailResponse,
    SessionParticipantsResponse,
    SessionStatusResponse
)
from app.services import session_service

router = APIRouter(prefix="/api/sessions", tags=["Sessions & Participants"])


@router.post(
    "",
    response_model=SessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task session",
    description="Creates a task session, generates a unique join code, and issues a creator credential."
)
def create_session_endpoint(
    payload: SessionCreateRequest,
    db: Session = Depends(get_db)
):
    session, creator, raw_token = session_service.create_session(
        db=db,
        title=payload.title,
        description=payload.description,
        context=payload.context,
        creator_name=payload.creator_name or "Session Creator",
        min_participants=payload.min_participants or 2
    )

    return SessionCreateResponse(
        id=session.id,
        join_code=session.join_code,
        status=session.status,
        creator_participant_id=creator.id,
        participant_token=raw_token
    )


@router.post(
    "/join",
    response_model=SessionJoinResponse,
    status_code=status.HTTP_200_OK,
    summary="Join a session via code",
    description="Allows a participant to join using a human-readable join code and receive an authorization credential."
)
def join_session_endpoint(
    payload: SessionJoinRequest,
    db: Session = Depends(get_db)
):
    session, participant, raw_token = session_service.join_session(
        db=db,
        join_code=payload.join_code,
        display_name=payload.display_name
    )

    return SessionJoinResponse(
        participant_id=participant.id,
        session_id=session.id,
        status=session.status,
        participant_token=raw_token
    )


@router.get(
    "/{session_id}",
    response_model=SessionDetailResponse,
    summary="Retrieve session details",
    description="Retrieves session metadata. Requires session participant authorization."
)
def get_session_details(
    session_data: tuple[SessionModel, ParticipantModel] = Depends(require_session_participant)
):
    session, _ = session_data
    return session


@router.get(
    "/{session_id}/participants",
    response_model=SessionParticipantsResponse,
    summary="Retrieve session participants",
    description="Lists participants and whether they have submitted their response. Preserves privacy by hiding text."
)
def get_session_participants_endpoint(
    session_data: tuple[SessionModel, ParticipantModel] = Depends(require_session_participant),
    db: Session = Depends(get_db)
):
    session, _ = session_data
    items = session_service.get_session_participants(db, session)
    return SessionParticipantsResponse(session_id=session.id, participants=items)


@router.get(
    "/{session_id}/status",
    response_model=SessionStatusResponse,
    summary="Retrieve session, submission, and analysis status",
    description="Returns aggregate submission progress and readiness for AI analysis without exposing individual responses."
)
def get_session_status_endpoint(
    session_data: tuple[SessionModel, ParticipantModel] = Depends(require_session_participant),
    db: Session = Depends(get_db)
):
    session, current_participant = session_data
    return session_service.get_session_status(db, session, current_participant)
