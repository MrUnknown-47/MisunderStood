import datetime
import logging
import uuid
from typing import List, Dict, Any, Tuple
from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.orm import Session
from app.models import SessionModel, ParticipantModel, InterpretationModel, AnalysisModel, IssueModel
from app.schemas import (
    AIAnalysisResult,
    AnalyzeResponse,
    IssueDetailResponse,
    IssuesListResponse,
    ComplementaryPerspective,
    IssueEvidence
)
from app.integrations.ai_client import AIAnalysisProvider
from app.config import get_settings

logger = logging.getLogger("misunderstood.analysis_service")
settings = get_settings()


async def trigger_analysis(
    db: Session,
    session: SessionModel,
    ai_client: AIAnalysisProvider
) -> AnalyzeResponse:
    """Run AI analysis pipeline with pre-commit, validation, and rollback safety."""
    # 1. State and submission check
    if session.status not in ["collecting_responses", "analyzing"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot trigger analysis: session is in '{session.status}' state."
        )

    interpretations = db.query(InterpretationModel).filter(
        InterpretationModel.session_id == session.id
    ).all()

    if len(interpretations) < session.min_participants:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot start analysis: at least {session.min_participants} interpretations "
                f"required, but only {len(interpretations)} submitted."
            )
        )

    # 2. Check for active concurrent analysis
    active_analysis = db.query(AnalysisModel).filter(
        AnalysisModel.session_id == session.id,
        AnalysisModel.status == "analyzing"
    ).first()
    if active_analysis:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An analysis is already currently in progress for this session."
        )

    # 3. Create analysis tracking record and update state
    analysis = AnalysisModel(
        session_id=session.id,
        model_name=settings.AI_MODEL,
        prompt_version="v1.0",
        status="analyzing"
    )
    session.status = "analyzing"
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    db.refresh(session)

    # 4. Prepare payload for AI client
    task_payload = {
        "title": session.title,
        "description": session.description,
        "context": session.context or ""
    }
    participants_payload = [
        {
            "participant_id": str(i.participant_id),
            "interpretation": i.response_text,
            "assumptions": i.assumptions or [],
            "success_criteria": i.success_criteria or []
        }
        for i in interpretations
    ]

    # Map participant IDs to raw text for evidence verification
    submitted_texts = {str(i.participant_id): i.response_text for i in interpretations}

    # 5. Invoke AI engine
    try:
        raw_result = await ai_client.analyze_interpretations(task_payload, participants_payload)
    except Exception as exc:
        logger.error(f"AI execution failed for session {session.id}: {exc}", exc_info=True)
        analysis.status = "failed"
        analysis.error_message = str(exc)
        session.status = "collecting_responses"  # reset to allow retry
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI analysis engine failed. Interpretations remain saved; please retry."
        )

    # 6. Validate AI output structure with Pydantic
    try:
        validated_result = AIAnalysisResult.model_validate(raw_result)
    except ValidationError as val_err:
        logger.error(f"AI response validation failed: {val_err}")
        analysis.status = "failed"
        analysis.error_message = f"Schema validation error: {val_err}"
        session.status = "collecting_responses"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI analysis produced malformed data structure."
        )

    # 7. Validate evidence quotes against actual participant submissions
    sanitized_issues = []
    for issue in validated_result.issues:
        valid_evidence = []
        for ev in issue.evidence:
            pid_str = str(ev.participant_id)
            if pid_str in submitted_texts:
                # Evidence links to an actual submitting participant
                valid_evidence.append(ev)
            else:
                logger.warning(f"Discarded evidence with unknown participant_id: {pid_str}")

        if valid_evidence:
            issue.evidence = valid_evidence
            sanitized_issues.append(issue)

    # 8. Persist analysis and individual issues atomically
    # Remove prior issues if this is an analysis retry
    db.query(IssueModel).filter(IssueModel.session_id == session.id).delete()

    analysis.status = "completed"
    analysis.result_json = validated_result.model_dump(mode="json")
    analysis.completed_at = datetime.datetime.now(datetime.timezone.utc)

    created_issues = []
    for issue in sanitized_issues:
        issue_record = IssueModel(
            session_id=session.id,
            analysis_id=analysis.id,
            type=issue.type,
            title=issue.title,
            description=issue.description,
            evidence_json=[ev.model_dump(mode="json") for ev in issue.evidence],
            priority=issue.priority,
            clarification_question=issue.clarification_question,
            status="open"
        )
        db.add(issue_record)
        created_issues.append(issue_record)

    session.status = "reviewing_issues"
    db.commit()
    db.refresh(analysis)

    return AnalyzeResponse(
        analysis_id=analysis.id,
        status="completed",
        issues_count=len(created_issues)
    )


def get_session_issues(
    db: Session,
    session: SessionModel,
    current_participant: ParticipantModel
) -> IssuesListResponse:
    """Retrieve issues and complementary perspectives with privacy gate protection."""
    # Privacy check: caller must have submitted if still in collecting_responses
    if session.status == "collecting_responses":
        user_submitted = db.query(InterpretationModel).filter(
            InterpretationModel.session_id == session.id,
            InterpretationModel.participant_id == current_participant.id
        ).first() is not None

        if not user_submitted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot view issues until you submit your own interpretation."
            )

    issues = db.query(IssueModel).filter(IssueModel.session_id == session.id).all()

    # Extract complementary perspectives from latest completed analysis
    latest_analysis = db.query(AnalysisModel).filter(
        AnalysisModel.session_id == session.id,
        AnalysisModel.status == "completed"
    ).order_by(AnalysisModel.created_at.desc()).first()

    complementary = []
    if latest_analysis and latest_analysis.result_json:
        raw_comp = latest_analysis.result_json.get("complementary_perspectives", [])
        for item in raw_comp:
            try:
                complementary.append(ComplementaryPerspective.model_validate(item))
            except Exception:
                pass

    issue_items = []
    for iss in issues:
        evidence_items = []
        if isinstance(iss.evidence_json, list):
            for ev in iss.evidence_json:
                try:
                    evidence_items.append(IssueEvidence.model_validate(ev))
                except Exception:
                    pass

        issue_items.append(
            IssueDetailResponse(
                id=iss.id,
                session_id=iss.session_id,
                analysis_id=iss.analysis_id,
                type=iss.type,
                title=iss.title,
                description=iss.description,
                evidence=evidence_items,
                priority=iss.priority,
                clarification_question=iss.clarification_question,
                status=iss.status,
                resolution_text=iss.resolution_text,
                created_at=iss.created_at,
                resolved_at=iss.resolved_at
            )
        )

    return IssuesListResponse(
        session_id=session.id,
        issues=issue_items,
        complementary_perspectives=complementary
    )
