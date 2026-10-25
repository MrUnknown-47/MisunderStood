import json
import uuid
from typing import Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.dependencies import (
    generate_participant_token,
    hash_token,
    require_session_participant,
    get_optional_session_participant,
)
from backend.app.models import (
    AnalysisModel,
    ParticipantModel,
    SessionModel,
    generate_session_code,
)
from backend.app.schemas import (
    AnalysisResponse,
    InterpretationCreate,
    InterpretationResponse,
    IssueRead,
    ParticipantCreate,
    ParticipantItem,
    ParticipantRead,
    SessionCreate,
    SessionJoinRequest,
    SessionJoinResponse,
    SessionParticipantsResponse,
    SessionRead,
    SessionStatusResponse,
    MyInterpretationResponse,
)
from backend.app.services.analysis_service import execute_session_analysis

router = APIRouter(prefix="/sessions", tags=["Sessions"])


def _to_session_read(
    session: SessionModel,
    creator_id: Optional[str] = None,
    raw_token: Optional[str] = None,
) -> SessionRead:
    return SessionRead(
        id=session.id,
        session_code=session.session_code,
        join_code=session.join_code or session.session_code,
        title=session.title,
        description=session.description,
        context=session.context,
        status=session.status,
        min_participants=session.min_participants,
        participant_count=session.participant_count,
        creator_participant_id=creator_id,
        participant_token=raw_token,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.post("", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreate,
    db: Session = Depends(get_db),
) -> SessionRead:
    """Create a task session, assign a human-friendly join code, and issue creator credentials."""
    code = generate_session_code()
    # Check uniqueness
    for _ in range(5):
        exists = db.query(SessionModel).filter(
            (SessionModel.join_code == code) | (SessionModel.session_code == code)
        ).first()
        if not exists:
            break
        code = generate_session_code()

    session_status = "collecting_responses" if payload.creator_name else "collecting"

    session = SessionModel(
        title=payload.title,
        description=payload.description,
        context=payload.context,
        session_code=code,
        join_code=code,
        status=session_status,
        min_participants=payload.min_participants or 2,
    )
    db.add(session)
    db.flush()

    raw_token = generate_participant_token()
    token_h = hash_token(raw_token)

    creator_id = None
    if payload.creator_name:
        creator_name = payload.creator_name.strip()
        cid = str(uuid.uuid4())
        creator = ParticipantModel(
            id=cid,
            session_id=session.id,
            participant_id=cid,
            name=creator_name,
            display_name=creator_name,
            role="creator",
            token_hash=token_h,
        )
        db.add(creator)
        db.flush()
        creator_id = creator.id

    db.commit()
    db.refresh(session)

    return _to_session_read(session, creator_id=creator_id, raw_token=raw_token)


@router.post(
    "/join",
    response_model=SessionJoinResponse,
    status_code=status.HTTP_200_OK,
    summary="Join session via join code",
)
def join_session(
    payload: SessionJoinRequest,
    db: Session = Depends(get_db),
) -> SessionJoinResponse:
    """Join an active session using an alphanumeric join code and receive participant credentials."""
    code = payload.join_code.strip().upper()
    session = db.query(SessionModel).filter(
        (SessionModel.join_code == code) | (SessionModel.session_code == code)
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with code '{code}' not found.",
        )

    if session.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This session has already been completed.",
        )

    raw_token = generate_participant_token()
    token_h = hash_token(raw_token)

    part_id = payload.participant_id or str(uuid.uuid4())
    participant = ParticipantModel(
        id=part_id,
        session_id=session.id,
        participant_id=part_id,
        name=payload.display_name.strip(),
        display_name=payload.display_name.strip(),
        role="participant",
        token_hash=token_h,
    )
    db.add(participant)
    db.commit()
    db.refresh(participant)

    return SessionJoinResponse(
        participant_id=participant.id,
        session_id=session.id,
        display_name=participant.display_name,
        status=session.status,
        participant_token=raw_token,
    )


@router.get("/{session_id}", response_model=SessionRead)
def get_session(
    session_data: tuple[SessionModel, Optional[ParticipantModel]] = Depends(
        get_optional_session_participant
    ),
) -> SessionRead:
    """Retrieve session details. If Bearer token is provided, verify session boundary."""
    session, _ = session_data
    return _to_session_read(session)


@router.get(
    "/{session_id}/participants",
    response_model=SessionParticipantsResponse,
    summary="Retrieve session participants strictly omitting interpretation text",
)
def get_session_participants(
    session_data: tuple[SessionModel, ParticipantModel] = Depends(
        require_session_participant
    ),
    db: Session = Depends(get_db),
) -> SessionParticipantsResponse:
    """List session participants preserving privacy by strictly withholding interpretation content."""
    session, _ = session_data
    participants = (
        db.query(ParticipantModel)
        .filter(ParticipantModel.session_id == session.id)
        .order_by(ParticipantModel.joined_at)
        .all()
    )

    items = [
        ParticipantItem(
            id=p.id,
            display_name=p.effective_name,
            role=p.role,
            has_submitted=p.has_submitted,
            joined_at=p.joined_at,
        )
        for p in participants
    ]
    return SessionParticipantsResponse(session_id=session.id, participants=items)


@router.get(
    "/{session_id}/status",
    response_model=SessionStatusResponse,
    summary="Retrieve session submission and readiness status",
)
def get_session_status(
    session_data: tuple[SessionModel, ParticipantModel] = Depends(
        require_session_participant
    ),
    db: Session = Depends(get_db),
) -> SessionStatusResponse:
    """Return submission progress without disclosing individual responses."""
    session, current_participant = session_data

    total_participants = (
        db.query(ParticipantModel)
        .filter(ParticipantModel.session_id == session.id)
        .count()
    )
    submission_count = session.participant_count

    can_start = (
        submission_count >= session.min_participants
        and session.status in ["collecting", "collecting_responses"]
    )

    return SessionStatusResponse(
        session_id=session.id,
        status=session.status,
        participant_count=total_participants,
        submission_count=submission_count,
        min_participants=session.min_participants,
        user_has_submitted=current_participant.has_submitted,
        can_start_analysis=can_start,
        user_interpretation=current_participant.interpretation if current_participant.has_submitted else None,
        user_assumptions=current_participant.assumptions if current_participant.has_submitted else None,
        user_success_criteria=current_participant.success_criteria if current_participant.has_submitted else None,
    )


@router.get(
    "/{session_id}/interpretations/me",
    response_model=MyInterpretationResponse,
    summary="Retrieve the authenticated participant's own submitted interpretation",
)
def get_my_interpretation(
    session_data: tuple[SessionModel, ParticipantModel] = Depends(
        require_session_participant
    ),
) -> MyInterpretationResponse:
    """Retrieve only the authenticated caller's own submitted interpretation.

    Preserves blind submission privacy by never disclosing peer interpretations.
    """
    session, participant = session_data
    return MyInterpretationResponse(
        session_id=session.id,
        participant_id=participant.participant_id or participant.id,
        display_name=participant.effective_name,
        has_submitted=participant.has_submitted,
        interpretation=participant.interpretation if participant.has_submitted else None,
        assumptions=participant.assumptions if participant.has_submitted else None,
        success_criteria=participant.success_criteria if participant.has_submitted else None,
        submitted_at=participant.submitted_at,
    )


@router.post(
    "/{session_id}/interpretations",
    response_model=InterpretationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit independent interpretation",
)
def submit_interpretation(
    payload: InterpretationCreate,
    session_data: tuple[SessionModel, ParticipantModel] = Depends(
        require_session_participant
    ),
    db: Session = Depends(get_db),
) -> InterpretationResponse:
    """Submit participant interpretation with server-side duplicate prevention and validation."""
    session, participant = session_data

    if session.status not in ["collecting", "collecting_responses"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot submit interpretation: session is in '{session.status}' state.",
        )

    text_to_save = (payload.response_text or payload.interpretation or "").strip()
    if not text_to_save:
        status_422 = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)
        raise HTTPException(
            status_code=status_422,
            detail="Interpretation text cannot be blank.",
        )

    if participant.has_submitted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already submitted an interpretation for this session.",
        )

    participant.interpretation = text_to_save
    if payload.assumptions:
        participant.assumptions = (
            json.dumps(payload.assumptions)
            if isinstance(payload.assumptions, list)
            else str(payload.assumptions)
        )
    if payload.success_criteria:
        participant.success_criteria = (
            json.dumps(payload.success_criteria)
            if isinstance(payload.success_criteria, list)
            else str(payload.success_criteria)
        )
    participant.submitted_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(participant)

    return InterpretationResponse(
        interpretation_id=participant.id,
        submitted=True,
        message="Your interpretation has been saved.",
    )


@router.post(
    "/{session_id}/participants",
    response_model=ParticipantRead,
    status_code=status.HTTP_201_CREATED,
)
def submit_participant_interpretation_legacy(
    session_id: str,
    payload: ParticipantCreate,
    db: Session = Depends(get_db),
) -> ParticipantModel:
    """Direct participant submission endpoint supporting automated integration tests."""
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
        participant.display_name = payload.name
        participant.interpretation = payload.interpretation
        participant.assumptions = payload.assumptions
        participant.success_criteria = payload.success_criteria
        participant.submitted_at = datetime.now(timezone.utc)
    else:
        raw_token = generate_participant_token()
        token_h = hash_token(raw_token)
        participant = ParticipantModel(
            session_id=session.id,
            participant_id=payload.participant_id,
            name=payload.name,
            display_name=payload.name,
            interpretation=payload.interpretation,
            assumptions=payload.assumptions,
            success_criteria=payload.success_criteria,
            token_hash=token_h,
            submitted_at=datetime.now(timezone.utc),
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
