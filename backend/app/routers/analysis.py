import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import SessionModel, ParticipantModel
from app.dependencies import require_session_participant
from app.schemas import AnalyzeResponse, IssuesListResponse
from app.services import analysis_service
from app.integrations.ai_client import get_ai_client, AIAnalysisProvider

router = APIRouter(prefix="/api/sessions", tags=["Analysis & Issues"])


@router.post(
    "/{session_id}/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger AI gap analysis",
    description="Extracts interpretations, sends them to the AI engine, validates output, and saves issues atomically."
)
async def trigger_analysis_endpoint(
    session_data: tuple[SessionModel, ParticipantModel] = Depends(require_session_participant),
    db: Session = Depends(get_db),
    ai_client: AIAnalysisProvider = Depends(get_ai_client)
):
    session, _ = session_data
    return await analysis_service.trigger_analysis(
        db=db,
        session=session,
        ai_client=ai_client
    )


@router.get(
    "/{session_id}/issues",
    response_model=IssuesListResponse,
    summary="Retrieve persisted findings and evidence",
    description="Returns identified issues and complementary perspectives with participant evidence citations."
)
def get_session_issues_endpoint(
    session_data: tuple[SessionModel, ParticipantModel] = Depends(require_session_participant),
    db: Session = Depends(get_db)
):
    session, current_participant = session_data
    return analysis_service.get_session_issues(
        db=db,
        session=session,
        current_participant=current_participant
    )
