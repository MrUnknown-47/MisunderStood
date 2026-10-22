import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ParticipantModel
from app.dependencies import get_current_participant
from app.schemas import IssueUpdateRequest, IssueUpdateResponse
from app.services import issue_service

router = APIRouter(prefix="/api/issues", tags=["Issue Resolution"])


@router.patch(
    "/{issue_id}",
    response_model=IssueUpdateResponse,
    summary="Update issue status and record resolution",
    description="Updates the state of an identified issue (open, discussing, resolved, dismissed) and records resolution notes."
)
def patch_issue_endpoint(
    issue_id: uuid.UUID,
    payload: IssueUpdateRequest,
    participant: ParticipantModel = Depends(get_current_participant),
    db: Session = Depends(get_db)
):
    return issue_service.update_issue(
        db=db,
        issue_id=issue_id,
        participant=participant,
        new_status=payload.status,
        resolution_text=payload.resolution_text
    )
