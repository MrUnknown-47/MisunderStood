from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.dependencies import hash_token
from backend.app.models import IssueModel, ParticipantModel, SessionModel
from backend.app.schemas import IssueRead, IssueUpdateStatus

router = APIRouter(prefix="/sessions", tags=["Issues"])


@router.get(
    "/{session_id}/issues",
    response_model=list[IssueRead],
    status_code=status.HTTP_200_OK,
    summary="Retrieve session issues with server-side privacy gate enforcement",
)
def get_session_issues(
    session_id: str,
    resolution_status: Optional[str] = Query(default=None),
    authorization: Optional[str] = Header(None, description="Optional bearer token for participant verification"),
    db: Session = Depends(get_db),
) -> list[IssueRead]:
    """Retrieve identified issues. Strictly enforces privacy gate during collecting state."""
    session = db.query(SessionModel).filter(
        (SessionModel.id == session_id)
        | (SessionModel.join_code == session_id.upper())
        | (SessionModel.session_code == session_id.upper())
    ).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )

    # Server-side Privacy Gate: In collecting phase, viewing issues requires having submitted
    if session.status in ["collecting", "collecting_responses"]:
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot view issues until you submit your own interpretation.",
            )

        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization format. Expected 'Bearer <token>'.",
            )

        token_h = hash_token(parts[1])
        participant = db.query(ParticipantModel).filter(ParticipantModel.token_hash == token_h).first()
        if not participant:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired participant token.",
            )

        if str(participant.session_id) != str(session.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: you do not belong to this session.",
            )

        if not participant.has_submitted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot view issues until you submit your own interpretation.",
            )

    # If authorization is provided in any other state, enforce cross-session protection
    elif authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token_h = hash_token(parts[1])
            participant = db.query(ParticipantModel).filter(ParticipantModel.token_hash == token_h).first()
            if participant and str(participant.session_id) != str(session.id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access forbidden: you do not belong to this session.",
                )

    query = db.query(IssueModel).filter(IssueModel.session_id == session.id)
    if resolution_status:
        query = query.filter(IssueModel.resolution_status == resolution_status.lower())

    issues = query.order_by(IssueModel.created_at).all()
    return [IssueRead.model_validate(iss) for iss in issues]


@router.patch(
    "/{session_id}/issues/{issue_id}",
    response_model=IssueRead,
    status_code=status.HTTP_200_OK,
)
def update_issue_status(
    session_id: str,
    issue_id: str,
    payload: IssueUpdateStatus,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> IssueRead:
    session = db.query(SessionModel).filter(
        (SessionModel.id == session_id)
        | (SessionModel.join_code == session_id.upper())
        | (SessionModel.session_code == session_id.upper())
    ).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )

    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token_h = hash_token(parts[1])
            participant = db.query(ParticipantModel).filter(ParticipantModel.token_hash == token_h).first()
            if participant and str(participant.session_id) != str(session.id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access forbidden: you do not belong to this session.",
                )

    issue = (
        db.query(IssueModel)
        .filter(
            IssueModel.session_id == session.id,
            IssueModel.id == issue_id,
        )
        .first()
    )
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Issue '{issue_id}' not found in session '{session.id}'.",
        )

    issue.resolution_status = payload.resolution_status
    if payload.resolution_notes is not None:
        issue.resolution_notes = payload.resolution_notes

    db.commit()
    db.refresh(issue)
    return IssueRead.model_validate(issue)
