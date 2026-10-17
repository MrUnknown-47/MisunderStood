import hashlib
import secrets
import uuid
from typing import Optional
from fastapi import Depends, HTTPException, Header, Path, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ParticipantModel, SessionModel


def generate_participant_token() -> str:
    """Generate a high-entropy bearer token for participant authentication."""
    return f"mst_sec_{secrets.token_urlsafe(32)}"


def hash_token(token: str) -> str:
    """Hash a raw bearer token using SHA-256."""
    return hashlib.sha256(token.strip().encode("utf-8")).hexdigest()


def get_current_participant(
    authorization: Optional[str] = Header(None, description="Bearer token issued upon session creation or join"),
    db: Session = Depends(get_db)
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
    session_id: uuid.UUID = Path(..., description="Target session UUID"),
    participant: ParticipantModel = Depends(get_current_participant),
    db: Session = Depends(get_db)
) -> tuple[SessionModel, ParticipantModel]:
    """Ensure caller is authenticated and belongs to the requested session."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found."
        )

    if participant.session_id != session.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you do not belong to this session."
        )

    return session, participant
