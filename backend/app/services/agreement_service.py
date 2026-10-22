import uuid
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models import (
    SessionModel,
    ParticipantModel,
    InterpretationModel,
    AnalysisModel,
    IssueModel,
    AgreementModel,
    AgreementConfirmationModel
)
from app.schemas import (
    AgreementResponse,
    AgreementContent,
    AgreementItem,
    AgreementConfirmResponse
)


def generate_agreement(
    db: Session,
    session: SessionModel
) -> AgreementResponse:
    """Generate and persist a structured shared agreement based on the task and resolutions."""
    if session.status not in ["reviewing_issues", "agreement_pending", "completed"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot generate agreement: session is in '{session.status}' state."
        )

    # 1. Gather resolved issues
    resolved_issues = db.query(IssueModel).filter(
        IssueModel.session_id == session.id,
        IssueModel.status == "resolved"
    ).all()

    # 2. Gather unresolved issues
    unresolved_issues = db.query(IssueModel).filter(
        IssueModel.session_id == session.id,
        IssueModel.status.in_(["open", "discussing"])
    ).all()

    # 3. Gather complementary perspectives from latest completed analysis
    latest_analysis = db.query(AnalysisModel).filter(
        AnalysisModel.session_id == session.id,
        AnalysisModel.status == "completed"
    ).order_by(AnalysisModel.created_at.desc()).first()

    complementary = []
    if latest_analysis and latest_analysis.result_json:
        complementary = latest_analysis.result_json.get("complementary_perspectives", [])

    # 4. Compile structured checklist
    confirmed_items = [
        AgreementItem(text=session.description, source="task_description")
    ]
    for iss in resolved_issues:
        confirmed_items.append(
            AgreementItem(
                text=iss.resolution_text or iss.title,
                source="resolved_issue"
            )
        )

    unresolved_items = [
        AgreementItem(
            text=f"{iss.title}: {iss.clarification_question}",
            source="unresolved_issue"
        )
        for iss in unresolved_issues
    ]

    optional_items = [
        AgreementItem(
            text=f"{item.get('title', '')}: {item.get('description', '')}",
            source="ai_suggestion"
        )
        for item in complementary
    ]

    content = AgreementContent(
        confirmed_requirements=confirmed_items,
        unresolved_decisions=unresolved_items,
        optional_suggestions=optional_items
    )

    # 5. Determine version
    current_max_version = db.query(AgreementModel).filter(
        AgreementModel.session_id == session.id
    ).count()
    new_version = current_max_version + 1

    agreement = AgreementModel(
        session_id=session.id,
        version=new_version,
        content_json=content.model_dump(mode="json"),
        status="pending_confirmation"
    )
    db.add(agreement)

    session.status = "agreement_pending"
    db.commit()
    db.refresh(agreement)
    db.refresh(session)

    return AgreementResponse(
        agreement_id=agreement.id,
        session_id=agreement.session_id,
        version=agreement.version,
        status=agreement.status,
        content=content,
        created_at=agreement.created_at
    )


def confirm_agreement(
    db: Session,
    agreement_id: uuid.UUID,
    participant: ParticipantModel,
    confirmed: bool = True,
    comment: Optional[str] = None
) -> AgreementConfirmResponse:
    """Record participant confirmation and advance session to completed when all have confirmed."""
    agreement = db.query(AgreementModel).filter(AgreementModel.id == agreement_id).first()
    if not agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agreement with ID '{agreement_id}' not found."
        )

    # Cross-session check
    if participant.session_id != agreement.session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you do not belong to the session for this agreement."
        )

    # Prevent duplicate confirmation
    existing = db.query(AgreementConfirmationModel).filter(
        AgreementConfirmationModel.agreement_id == agreement.id,
        AgreementConfirmationModel.participant_id == participant.id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already submitted a confirmation for this agreement."
        )

    # Save confirmation
    conf = AgreementConfirmationModel(
        agreement_id=agreement.id,
        participant_id=participant.id,
        confirmed=confirmed,
        comment=comment
    )
    db.add(conf)
    db.flush()

    # Determine required participants (all who submitted interpretations)
    submitting_participant_ids = set(
        row[0] for row in db.query(InterpretationModel.participant_id).filter(
            InterpretationModel.session_id == agreement.session_id
        ).all()
    )

    confirmed_participant_ids = set(
        row[0] for row in db.query(AgreementConfirmationModel.participant_id).filter(
            AgreementConfirmationModel.agreement_id == agreement.id,
            AgreementConfirmationModel.confirmed == True
        ).all()
    )

    # Check if all submitted participants have confirmed
    all_confirmed = bool(submitting_participant_ids) and submitting_participant_ids.issubset(confirmed_participant_ids)

    session = db.query(SessionModel).filter(SessionModel.id == agreement.session_id).first()
    if all_confirmed:
        agreement.status = "confirmed"
        if session:
            session.status = "completed"

    db.commit()
    db.refresh(conf)
    if session:
        db.refresh(session)

    return AgreementConfirmResponse(
        confirmation_id=conf.id,
        agreement_id=agreement.id,
        participant_id=participant.id,
        confirmed=conf.confirmed,
        all_participants_confirmed=all_confirmed,
        session_status=session.status if session else "agreement_pending"
    )
