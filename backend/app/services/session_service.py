import secrets
import string
import uuid
from typing import Tuple, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models import SessionModel, ParticipantModel, InterpretationModel
from app.dependencies import generate_participant_token, hash_token
from app.schemas import SessionStatusResponse, ParticipantItem


def generate_join_code(length: int = 6) -> str:
    """Generate a clean, readable join code e.g. GAP42X or GAP-4821."""
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    random_str = "".join(secrets.choice(chars) for _ in range(length))
    return f"GAP-{random_str[:3]}{random_str[3:]}"


def create_session(
    db: Session,
    title: str,
    description: str,
    context: str | None,
    creator_name: str,
    min_participants: int = 2
) -> Tuple[SessionModel, ParticipantModel, str]:
    """Create a new task session and register the creator as the first participant."""
    # Ensure unique join code
    for _ in range(10):
        code = generate_join_code()
        exists = db.query(SessionModel).filter(SessionModel.join_code == code).first()
        if not exists:
            break
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate a unique session code. Please retry."
        )

    session = SessionModel(
        title=title.strip(),
        description=description.strip(),
        context=context.strip() if context else None,
        join_code=code,
        status="collecting_responses",
        min_participants=min_participants
    )
    db.add(session)
    db.flush()

    raw_token = generate_participant_token()
    token_h = hash_token(raw_token)

    creator = ParticipantModel(
        session_id=session.id,
        display_name=creator_name.strip(),
        role="creator",
        token_hash=token_h
    )
    db.add(creator)
    db.commit()
    db.refresh(session)
    db.refresh(creator)

    return session, creator, raw_token


def join_session(
    db: Session,
    join_code: str,
    display_name: str
) -> Tuple[SessionModel, ParticipantModel, str]:
    """Join an existing session by join code and create an authorized participant session."""
    code = join_code.strip().upper()
    session = db.query(SessionModel).filter(SessionModel.join_code == code).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with code '{code}' not found."
        )

    if session.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This session has already been completed."
        )

    raw_token = generate_participant_token()
    token_h = hash_token(raw_token)

    participant = ParticipantModel(
        session_id=session.id,
        display_name=display_name.strip(),
        role="participant",
        token_hash=token_h
    )
    db.add(participant)
    db.commit()
    db.refresh(participant)

    return session, participant, raw_token


def get_session_status(
    db: Session,
    session: SessionModel,
    current_participant: ParticipantModel
) -> SessionStatusResponse:
    """Retrieve session submission status without leaking response text."""
    participant_count = db.query(ParticipantModel).filter(ParticipantModel.session_id == session.id).count()
    submission_count = db.query(InterpretationModel).filter(InterpretationModel.session_id == session.id).count()
    
    user_submitted = db.query(InterpretationModel).filter(
        InterpretationModel.session_id == session.id,
        InterpretationModel.participant_id == current_participant.id
    ).first() is not None

    can_start = (submission_count >= session.min_participants) and (session.status == "collecting_responses")

    return SessionStatusResponse(
        session_id=session.id,
        status=session.status,
        participant_count=participant_count,
        submission_count=submission_count,
        min_participants=session.min_participants,
        user_has_submitted=user_submitted,
        can_start_analysis=can_start
    )


def get_session_participants(
    db: Session,
    session: SessionModel
) -> List[ParticipantItem]:
    """Return participant metadata list with submission status, strictly omitting text."""
    participants = db.query(ParticipantModel).filter(ParticipantModel.session_id == session.id).all()
    submitted_participant_ids = set(
        row[0] for row in db.query(InterpretationModel.participant_id).filter(
            InterpretationModel.session_id == session.id
        ).all()
    )

    items = []
    for p in participants:
        items.append(
            ParticipantItem(
                id=p.id,
                display_name=p.display_name,
                role=p.role,
                has_submitted=(p.id in submitted_participant_ids),
                joined_at=p.joined_at
            )
        )
    return items
