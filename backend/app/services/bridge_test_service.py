import uuid
from typing import Optional
from sqlalchemy.orm import Session
from app.models import SessionModel, IssueModel, AgreementModel
from app.schemas import BridgeTestMetrics


def calculate_bridge_test(
    db: Session,
    session: SessionModel
) -> BridgeTestMetrics:
    """Calculate Bridge Test resolution metrics strictly from persisted records."""
    issues = db.query(IssueModel).filter(IssueModel.session_id == session.id).all()

    initial_issue_count = len(issues)
    resolved_count = sum(1 for iss in issues if iss.status == "resolved")
    unresolved_count = sum(1 for iss in issues if iss.status in ["open", "discussing"])
    dismissed_count = sum(1 for iss in issues if iss.status == "dismissed")

    # If N_0 == 0, resolution_rate is None (displayed as Not Applicable in UI)
    if initial_issue_count == 0:
        resolution_rate: Optional[float] = None
    else:
        resolution_rate = round((resolved_count / initial_issue_count) * 100.0, 1)

    latest_agreement = db.query(AgreementModel).filter(
        AgreementModel.session_id == session.id
    ).order_by(AgreementModel.version.desc()).first()

    agreement_status = latest_agreement.status if latest_agreement else "not_generated"

    return BridgeTestMetrics(
        initial_issue_count=initial_issue_count,
        resolved_issue_count=resolved_count,
        unresolved_issue_count=unresolved_count,
        dismissed_issue_count=dismissed_count,
        resolution_rate=resolution_rate,
        agreement_status=agreement_status
    )
