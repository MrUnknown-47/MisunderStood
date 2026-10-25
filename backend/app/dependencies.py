import hashlib
import secrets
from typing import Optional
from fastapi import Depends, HTTPException, Header, Path, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import ParticipantModel, SessionModel


def generate_participant_token() -> str:
    """Generate a high-entropy bearer token for participant authentication."""
    return f"mst_sec_{secrets.token_urlsafe(32)}"


def hash_token(token: str) -> str:
    """Hash a raw bearer token using SHA-256."""
    return hashlib.sha256(token.strip().encode("utf-8")).hexdigest()


def get_current_participant(
    authorization: Optional[str] = Header(None, description="Bearer token issued upon session creation or join"),
    db: Session = Depends(get_db),
) -> ParticipantModel:
    """Authenticate participant using the Authorization Bearer header."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required (Bearer token)."
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization format. Expected 'Bearer <token>'."
        )

    raw_token = parts[1]
    token_h = hash_token(raw_token)

    participant = db.query(ParticipantModel).filter(ParticipantModel.token_hash == token_h).first()
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired participant token."
        )

    return participant


def require_session_participant(
    session_id: str = Path(..., description="Target session ID or join code"),
    authorization: Optional[str] = Header(None, description="Bearer token issued upon session creation or join"),
    db: Session = Depends(get_db),
) -> tuple[SessionModel, ParticipantModel]:
    """Ensure caller is authenticated with a valid token and belongs to the target session."""
    session = db.query(SessionModel).filter(
        (SessionModel.id == session_id)
        | (SessionModel.join_code == session_id.upper())
        | (SessionModel.session_code == session_id.upper())
    ).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found."
        )

    participant = get_current_participant(authorization=authorization, db=db)

    if str(participant.session_id) != str(session.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you do not belong to this session."
        )

    return session, participant


def get_optional_session_participant(
    session_id: str = Path(..., description="Target session ID or join code"),
    authorization: Optional[str] = Header(None, description="Optional bearer token"),
    db: Session = Depends(get_db),
) -> tuple[SessionModel, Optional[ParticipantModel]]:
    """Resolve session, and if an Authorization header is provided, strictly enforce valid token and session membership."""
    session = db.query(SessionModel).filter(
        (SessionModel.id == session_id)
        | (SessionModel.join_code == session_id.upper())
        | (SessionModel.session_code == session_id.upper())
    ).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found."
        )

    if not authorization:
        return session, None

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization format. Expected 'Bearer <token>'."
        )

    raw_token = parts[1]
    token_h = hash_token(raw_token)
    participant = db.query(ParticipantModel).filter(ParticipantModel.token_hash == token_h).first()
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired participant token."
        )

    if str(participant.session_id) != str(session.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you do not belong to this session."
        )

    return session, participant
