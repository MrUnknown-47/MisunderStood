from typing import Any, Callable, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.ai import analyze_interpretations
from backend.app.models import AnalysisModel, IssueModel, SessionModel
from backend.app.schemas import AnalysisResponse, IssueRead


def _record_analysis_failure(
    session: SessionModel,
    db: Session,
    status_str: str,
    summary: str,
    error_message: Optional[str] = None,
    metadata_info: Optional[dict[str, Any]] = None,
) -> None:
    session.status = status_str
    record = AnalysisModel(
        session_id=session.id,
        status=status_str,
        summary=summary,
        error_message=error_message,
        issue_counts={},
        complementary_perspectives=[],
        metadata_info=metadata_info or {},
    )
    db.add(record)
    db.commit()


async def execute_session_analysis(
    session_id: str,
    db: Session,
    ai_analyzer_fn: Optional[Callable] = None,
) -> AnalysisResponse:
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )

    # Concurrency guard: avoid duplicate concurrent analyses on the same session
    if session.status == "analyzing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Analysis is already in progress for this session.",
        )

    valid_participants = [
        p
        for p in session.participants
        if p.interpretation and p.interpretation.strip()
    ]
    if len(valid_participants) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "At least 2 participant submissions with non-empty interpretations "
                f"are required before analysis can be performed. Found: {len(valid_participants)}."
            ),
        )

    session.status = "analyzing"
    db.commit()

    # Build input strictly from persisted submissions without inventing fields
    task_payload: dict[str, Any] = {"title": session.title}
    if session.description and session.description.strip():
        task_payload["description"] = session.description.strip()

    participants_payload: list[dict[str, Any]] = []
    for p in valid_participants:
        entry: dict[str, Any] = {
            "participant_id": p.participant_id,
            "interpretation": p.interpretation.strip(),
        }
        if p.assumptions and p.assumptions.strip():
            entry["assumptions"] = p.assumptions.strip()
        if p.success_criteria and p.success_criteria.strip():
            entry["success_criteria"] = p.success_criteria.strip()
        participants_payload.append(entry)

    analyzer = ai_analyzer_fn or analyze_interpretations
    try:
        raw_result = await analyzer(
            task=task_payload,
            participants=participants_payload,
        )
    except Exception as exc:
        _record_analysis_failure(
            session=session,
            db=db,
            status_str="failed",
            summary="Analysis failed due to unexpected runtime error.",
            error_message=f"Runtime error: {str(exc)}",
            metadata_info={"error_type": type(exc).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error executing AI analysis: {str(exc)}",
        ) from exc

    ai_status = raw_result.get("status")

    if ai_status == "failed":
        _record_analysis_failure(
            session=session,
            db=db,
            status_str="failed",
            summary=raw_result.get("summary", "Analysis failed."),
            error_message=raw_result.get("error_message", "Unknown provider failure."),
            metadata_info=raw_result.get("metadata", {}),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI analysis failed: {raw_result.get('error_message')}",
        )

    if ai_status == "insufficient_data":
        _record_analysis_failure(
            session=session,
            db=db,
            status_str="insufficient_data",
            summary=raw_result.get("summary", "Insufficient participant submissions."),
            metadata_info=raw_result.get("metadata", {}),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=raw_result.get("summary", "Insufficient participant submissions."),
        )

    analysis_record = AnalysisModel(
        session_id=session.id,
        status="completed",
        summary=raw_result.get("summary", ""),
        error_message=None,
        issue_counts=raw_result.get("issue_counts", {}),
        complementary_perspectives=raw_result.get("complementary_perspectives", []),
        metadata_info=raw_result.get("metadata", {}),
    )
    db.add(analysis_record)
    db.flush()

    # Re-run Policy: Synchronize issues while preserving human resolution decisions
    existing_issues = (
        db.query(IssueModel).filter(IssueModel.session_id == session.id).all()
    )
    existing_by_key = {
        (iss.type.lower(), iss.title.lower().strip()): iss
        for iss in existing_issues
    }

    current_keys = set()
    for raw_iss in raw_result.get("issues", []):
        iss_type = (
            raw_iss["type"].value
            if hasattr(raw_iss["type"], "value")
            else str(raw_iss["type"])
        )
        iss_priority = (
            raw_iss["priority"].value
            if hasattr(raw_iss["priority"], "value")
            else str(raw_iss["priority"])
        )
        iss_title = raw_iss["title"].strip()
        key = (iss_type.lower(), iss_title.lower())
        current_keys.add(key)

        evidence_list = []
        for ev in raw_iss.get("evidence", []):
            if hasattr(ev, "model_dump"):
                evidence_list.append(ev.model_dump())
            elif isinstance(ev, dict):
                evidence_list.append(ev)

        if key in existing_by_key:
            # Refresh AI metadata but preserve human resolution_status and resolution_notes
            existing = existing_by_key[key]
            existing.analysis_id = analysis_record.id
            existing.description = raw_iss["description"]
            existing.evidence = evidence_list
            existing.impact = raw_iss["impact"]
            existing.priority = iss_priority
            existing.confidence = float(raw_iss["confidence"])
            existing.clarification_question = raw_iss["clarification_question"]
        else:
            new_issue = IssueModel(
                session_id=session.id,
                analysis_id=analysis_record.id,
                type=iss_type,
                title=iss_title,
                description=raw_iss["description"],
                evidence=evidence_list,
                impact=raw_iss["impact"],
                priority=iss_priority,
                confidence=float(raw_iss["confidence"]),
                clarification_question=raw_iss["clarification_question"],
                resolution_status="open",
                resolution_notes=None,
            )
            db.add(new_issue)

    # Prune stale open issues no longer detected in the refreshed analysis
    for key, existing in existing_by_key.items():
        if key not in current_keys and existing.resolution_status == "open":
            db.delete(existing)

    session.status = "completed"
    db.commit()

    all_current_issues = (
        db.query(IssueModel)
        .filter(IssueModel.session_id == session.id)
        .order_by(IssueModel.created_at)
        .all()
    )

    return AnalysisResponse(
        session_id=session.id,
        analysis_id=analysis_record.id,
        status="completed",
        summary=analysis_record.summary,
        issues=[IssueRead.model_validate(iss) for iss in all_current_issues],
        complementary_perspectives=raw_result.get("complementary_perspectives", []),
        issue_counts=raw_result.get("issue_counts", {}),
        error_message=None,
        metadata=raw_result.get("metadata", {}),
    )
