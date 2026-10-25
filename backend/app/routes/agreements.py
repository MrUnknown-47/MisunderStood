from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import (
    AgreementModel,
    AnalysisModel,
    SessionModel,
)
from backend.app.schemas import (
    AgreementConfirmPayload,
    AgreementRead,
    BridgeTestResponse,
)

router = APIRouter(prefix="/sessions", tags=["Agreements & Bridge Test"])


@router.get(
    "/{session_id}/agreement",
    response_model=AgreementRead,
    status_code=status.HTTP_200_OK,
)
def get_or_compile_agreement(
    session_id: str,
    db: Session = Depends(get_db),
) -> AgreementModel:
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )

    agreement = (
        db.query(AgreementModel).filter(AgreementModel.session_id == session_id).first()
    )

    items: list[str] = [f"Core Deliverable: {session.title}"]
    if session.description:
        items.append(f"Context / Goal: {session.description}")

    excluded_items: list[str] = []

    for iss in session.issues:
        if iss.resolution_status == "resolved":
            detail = f"Agreed: {iss.title}"
            if iss.resolution_notes:
                detail += f" ({iss.resolution_notes})"
            items.append(detail)
        elif iss.resolution_status == "dismissed":
            detail = f"Excluded / Out of Scope: {iss.title}"
            if iss.resolution_notes:
                detail += f" ({iss.resolution_notes})"
            excluded_items.append(detail)

    latest_analysis = (
        db.query(AnalysisModel)
        .filter(AnalysisModel.session_id == session_id)
        .order_by(AnalysisModel.created_at.desc())
        .first()
    )
    if latest_analysis and latest_analysis.complementary_perspectives:
        for comp in latest_analysis.complementary_perspectives:
            items.append(f"Complementary Alignment: {comp.get('title')}")

    if not agreement:
        agreement = AgreementModel(
            session_id=session.id,
            items=items,
            excluded_items=excluded_items,
            confirmed_by=[],
            is_fully_confirmed=False,
        )
        db.add(agreement)
    else:
        agreement.items = items
        agreement.excluded_items = excluded_items

    db.commit()
    db.refresh(agreement)
    return agreement


@router.post(
    "/{session_id}/agreement/confirm",
    response_model=AgreementRead,
    status_code=status.HTTP_200_OK,
)
def confirm_agreement(
    session_id: str,
    payload: AgreementConfirmPayload,
    db: Session = Depends(get_db),
) -> AgreementModel:
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )

    submitting_participants = [
        p for p in session.participants
        if p.interpretation and str(p.interpretation).strip()
    ]
    if not submitting_participants:
        submitting_participants = list(session.participants)

    matching_participant = None
    for p in submitting_participants:
        if payload.participant_id in (p.participant_id, p.id):
            matching_participant = p
            break

    if not matching_participant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Participant '{payload.participant_id}' has not submitted to session '{session_id}'.",
        )

    agreement = (
        db.query(AgreementModel).filter(AgreementModel.session_id == session_id).first()
    )
    if not agreement:
        agreement = get_or_compile_agreement(session_id=session_id, db=db)

    confirmed_list = list(agreement.confirmed_by or [])
    if payload.participant_id not in confirmed_list:
        confirmed_list.append(payload.participant_id)
        agreement.confirmed_by = confirmed_list

    agreement.is_fully_confirmed = bool(submitting_participants) and all(
        any(pid in confirmed_list for pid in (p.participant_id, p.id))
        for p in submitting_participants
    )

    db.commit()
    db.refresh(agreement)
    return agreement


@router.get(
    "/{session_id}/bridge-test",
    response_model=BridgeTestResponse,
    status_code=status.HTTP_200_OK,
)
def get_bridge_test_metrics(
    session_id: str,
    db: Session = Depends(get_db),
) -> BridgeTestResponse:
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )

    total_issues = len(session.issues)
    resolved_count = sum(
        1 for iss in session.issues if iss.resolution_status == "resolved"
    )
    dismissed_count = sum(
        1 for iss in session.issues if iss.resolution_status == "dismissed"
    )
    open_count = sum(
        1 for iss in session.issues if iss.resolution_status == "open"
    )

    if total_issues > 0:
        resolution_percentage = round(
            ((resolved_count + dismissed_count) / total_issues) * 100.0, 1
        )
    else:
        resolution_percentage = 100.0

    agreement = (
        db.query(AgreementModel).filter(AgreementModel.session_id == session_id).first()
    )
    is_fully_confirmed = agreement.is_fully_confirmed if agreement else False
    confirmed_participants = agreement.confirmed_by if agreement else []

    if open_count == 0 and is_fully_confirmed:
        bridge_status = "bridged"
    elif resolved_count > 0 or dismissed_count > 0 or confirmed_participants:
        bridge_status = "in_progress"
    else:
        bridge_status = "unresolved"

    return BridgeTestResponse(
        session_id=session.id,
        initial_issues_count=total_issues,
        resolved_count=resolved_count,
        dismissed_count=dismissed_count,
        open_count=open_count,
        resolution_percentage=resolution_percentage,
        is_fully_confirmed=is_fully_confirmed,
        confirmed_participants=confirmed_participants,
        total_participants=len(session.participants),
        bridge_status=bridge_status,
    )
