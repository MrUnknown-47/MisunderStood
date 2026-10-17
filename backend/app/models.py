"""SQLAlchemy database models for MISUNDERSTOOD backend.
"""

import uuid
import secrets
from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Float,
    Boolean,
    func,
)
from sqlalchemy.orm import relationship
from backend.app.database import Base


def generate_session_code() -> str:
    """Generate a readable 6-character alphanumeric session code."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(6))


class SessionModel(Base):
    """Represents a collaborative task session."""

    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_code = Column(
        String(12),
        unique=True,
        index=True,
        nullable=False,
        default=generate_session_code,
    )
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        String(30),
        nullable=False,
        default="collecting",
        # Lifecycle states: "collecting", "analyzing", "completed", "failed", "insufficient_data"
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    participants = relationship(
        "ParticipantModel",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ParticipantModel.submitted_at",
    )
    analyses = relationship(
        "AnalysisModel",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="AnalysisModel.created_at.desc()",
    )
    issues = relationship(
        "IssueModel",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="IssueModel.created_at",
    )
    agreement = relationship(
        "AgreementModel",
        uselist=False,
        back_populates="session",
        cascade="all, delete-orphan",
    )


class ParticipantModel(Base):
    """Represents a participant's submitted interpretation for a session."""

    __tablename__ = "participants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(
        String(36),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    participant_id = Column(String(100), nullable=False)
    name = Column(String(100), nullable=True)
    interpretation = Column(Text, nullable=False)
    assumptions = Column(Text, nullable=True)
    success_criteria = Column(Text, nullable=True)
    submitted_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session = relationship("SessionModel", back_populates="participants")


class AnalysisModel(Base):
    """Persisted snapshot of an AI analysis run for a session."""

    __tablename__ = "analyses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(
        String(36),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(
        String(30), nullable=False
    )  # "completed", "failed", "insufficient_data"
    summary = Column(Text, nullable=False)
    error_message = Column(Text, nullable=True)
    issue_counts = Column(JSON, nullable=False, default=dict)
    complementary_perspectives = Column(JSON, nullable=False, default=list)
    metadata_info = Column(JSON, nullable=False, default=dict)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session = relationship("SessionModel", back_populates="analyses")
    issues = relationship(
        "IssueModel",
        back_populates="analysis",
        cascade="all, delete-orphan",
    )


class IssueModel(Base):
    """Persisted misunderstanding finding backed by participant evidence."""

    __tablename__ = "issues"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(
        String(36),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    analysis_id = Column(
        String(36),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    evidence = Column(JSON, nullable=False, default=list)
    impact = Column(Text, nullable=False)
    priority = Column(String(20), nullable=False)
    confidence = Column(Float, nullable=False)
    clarification_question = Column(Text, nullable=False)
    resolution_status = Column(
        String(30),
        nullable=False,
        default="open",
        # "open", "resolved", "dismissed"
    )
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    session = relationship("SessionModel", back_populates="issues")
    analysis = relationship("AnalysisModel", back_populates="issues")


class AgreementModel(Base):
    """Persisted shared agreement / checklist and participant confirmations."""

    __tablename__ = "agreements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(
        String(36),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    items = Column(JSON, nullable=False, default=list)  # list of agreed requirement strings
    excluded_items = Column(JSON, nullable=False, default=list)  # list of out-of-scope strings
    confirmed_by = Column(JSON, nullable=False, default=list)  # list of participant_ids
    is_fully_confirmed = Column(Boolean, default=False, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    session = relationship("SessionModel", back_populates="agreement")
