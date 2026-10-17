"""Analysis orchestration service connecting FastAPI sessions to the AI/ML module.
"""

from typing import Any, Callable, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.ai import analyze_interpretations
from backend.app.models import AnalysisModel, IssueModel, SessionModel
from backend.app.schemas import AnalysisResponse, IssueRead


async def execute_session_analysis(
    session_id: str,
    db: Session,
    ai_analyzer_fn: Optional[Callable] = None,
) -> AnalysisResponse:
    """Orchestrate AI task interpretation analysis for a persisted session.

    Enforces session lifecycle rules:
    1. Validates session existence.
    2. Prevents premature analysis (requires at least 2 participant submissions).
    3. Prevents duplicate concurrent analysis requests.
    4. Constructs inputs strictly from persisted records without inventing content.
    5. Dispatches to AI analysis component.
    6. Persists analysis snapshots and individual findings with idempotency.
    7. Preserves human resolution decisions ("resolved" / "dismissed") across re-analyses.
    """
    # 1. Fetch and validate session
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )

    # 2. Concurrency guard: prevent concurrent duplicate runs
    if session.status == "analyzing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Analysis is already in progress for this session.",
        )

    # 3. Lifecycle guard: verify required participant submissions
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

    # Set state to analyzing to lock concurrent requests
    session.status = "analyzing"
    db.commit()

    # 4. Construct AI input strictly from persisted records
    task_input: dict[str, Any] = {"title": session.title}
    if session.description and session.description.strip():
        task_input["description"] = session.description.strip()

    participants_input: list[dict[str, Any]] = []
    for p in valid_participants:
        p_dict: dict[str, Any] = {
            "participant_id": p.participant_id,
            "interpretation": p.interpretation.strip(),
        }
        if p.assumptions and p.assumptions.strip():
            p_dict["assumptions"] = p.assumptions.strip()
        if p.success_criteria and p.success_criteria.strip():
            p_dict["success_criteria"] = p.success_criteria.strip()
        participants_input.append(p_dict)

    # 5. Dispatch to AI module
    analyzer_callable = ai_analyzer_fn or analyze_interpretations
    try:
        raw_result = await analyzer_callable(
            task=task_input,
            participants=participants_input,
        )
    except Exception as exc:
        session.status = "failed"
        failed_analysis = AnalysisModel(
            session_id=session.id,
            status="failed",
            summary="Analysis failed due to unexpected runtime error.",
            error_message=f"Runtime error: {str(exc)}",
            issue_counts={},
            complementary_perspectives=[],
            metadata_info={"error_type": type(exc).__name__},
        )
        db.add(failed_analysis)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error executing AI analysis: {str(exc)}",
        ) from exc

    # 6. Handle AI Result Outcomes
    ai_status = raw_result.get("status")

    if ai_status == "failed":
        session.status = "failed"
        failed_analysis = AnalysisModel(
            session_id=session.id,
            status="failed",
            summary=raw_result.get("summary", "Analysis failed."),
            error_message=raw_result.get("error_message", "Unknown provider failure."),
            issue_counts=raw_result.get("issue_counts", {}),
            complementary_perspectives=raw_result.get("complementary_perspectives", []),
            metadata_info=raw_result.get("metadata", {}),
        )
        db.add(failed_analysis)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI analysis failed: {raw_result.get('error_message')}",
        )

    if ai_status == "insufficient_data":
        session.status = "insufficient_data"
        insuf_analysis = AnalysisModel(
            session_id=session.id,
            status="insufficient_data",
            summary=raw_result.get("summary", "Insufficient participant submissions."),
            error_message=None,
            issue_counts={},
            complementary_perspectives=[],
            metadata_info=raw_result.get("metadata", {}),
        )
        db.add(insuf_analysis)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=raw_result.get("summary", "Insufficient participant submissions."),
        )

    # 7. Persist Successful Analysis Run ("completed")
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
    db.flush()  # Generates analysis_record.id

    # 8. Re-run Policy: Update issues without losing team resolution decisions
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

        # Normalize evidence to plain dictionaries
        evidence_list = []
        for ev in raw_iss.get("evidence", []):
            if hasattr(ev, "model_dump"):
                evidence_list.append(ev.model_dump())
            elif isinstance(ev, dict):
                evidence_list.append(ev)

        if key in existing_by_key:
            # Existing issue: update AI findings, PRESERVE user resolution status & notes!
            existing_iss = existing_by_key[key]
            existing_iss.analysis_id = analysis_record.id
            existing_iss.description = raw_iss["description"]
            existing_iss.evidence = evidence_list
            existing_iss.impact = raw_iss["impact"]
            existing_iss.priority = iss_priority
            existing_iss.confidence = float(raw_iss["confidence"])
            existing_iss.clarification_question = raw_iss["clarification_question"]
            # resolution_status and resolution_notes are intentionally preserved!
        else:
            # Brand new issue: insert as "open"
            new_iss = IssueModel(
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
            db.add(new_iss)

    # Prune stale open issues no longer detected in the new analysis
    for key, existing_iss in existing_by_key.items():
        if key not in current_keys and existing_iss.resolution_status == "open":
            db.delete(existing_iss)

    # Update session status to completed
    session.status = "completed"
    db.commit()

    # 9. Assemble and return response
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
