from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import IssueModel, SessionModel
from backend.app.schemas import IssueRead, IssueUpdateStatus

router = APIRouter(prefix="/sessions", tags=["Issues"])


@router.get(
    "/{session_id}/issues",
    response_model=list[IssueRead],
    status_code=status.HTTP_200_OK,
)
def get_session_issues(
    session_id: str,
    resolution_status: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> list[IssueRead]:
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )

    query = db.query(IssueModel).filter(IssueModel.session_id == session_id)
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
    db: Session = Depends(get_db),
) -> IssueRead:
    issue = (
        db.query(IssueModel)
        .filter(
            IssueModel.session_id == session_id,
            IssueModel.id == issue_id,
        )
        .first()
    )
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Issue '{issue_id}' not found in session '{session_id}'.",
        )

    issue.resolution_status = payload.resolution_status
    if payload.resolution_notes is not None:
        issue.resolution_notes = payload.resolution_notes

    db.commit()
    db.refresh(issue)
    return IssueRead.model_validate(issue)
