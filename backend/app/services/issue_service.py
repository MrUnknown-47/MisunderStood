import datetime
import uuid
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models import IssueModel, ParticipantModel
from app.schemas import IssueStatus, IssueUpdateResponse


def update_issue(
    db: Session,
    issue_id: uuid.UUID,
    participant: ParticipantModel,
    new_status: IssueStatus,
    resolution_text: Optional[str] = None
) -> IssueUpdateResponse:
    """Update issue status and record clarification or resolution details."""
    issue = db.query(IssueModel).filter(IssueModel.id == issue_id).first()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Issue with ID '{issue_id}' not found."
        )

    # Cross-session security check: caller must belong to the issue's session
    if participant.session_id != issue.session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you do not have permission to update issues in this session."
        )

    # Validate resolution text if marking as resolved
    if new_status == "resolved" and not resolution_text and not issue.resolution_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT if hasattr(status, "HTTP_422_UNPROCESSABLE_CONTENT") else 422,
            detail="Resolution text is required when marking an issue as resolved."
        )

    issue.status = new_status
    if resolution_text is not None:
        issue.resolution_text = resolution_text.strip()

    if new_status in ["resolved", "dismissed"]:
        issue.resolved_at = datetime.datetime.now(datetime.timezone.utc)
    else:
        issue.resolved_at = None

    db.commit()
    db.refresh(issue)

    return IssueUpdateResponse(
        id=issue.id,
        status=issue.status,
        resolution_text=issue.resolution_text
    )
