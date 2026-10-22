import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    String,
    Text,
    Integer,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    UniqueConstraint,
    Index
)
from sqlalchemy.orm import relationship
from app.database import Base, GUID, UniversalJSON


def utc_now():
    return datetime.now(timezone.utc)


class SessionModel(Base):
    __tablename__ = "sessions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    join_code = Column(String(32), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    context = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="collecting_responses", index=True)
    min_participants = Column(Integer, nullable=False, default=2)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    # Relationships
    participants = relationship("ParticipantModel", back_populates="session", cascade="all, delete-orphan")
    interpretations = relationship("InterpretationModel", back_populates="session", cascade="all, delete-orphan")
    analyses = relationship("AnalysisModel", back_populates="session", cascade="all, delete-orphan")
    issues = relationship("IssueModel", back_populates="session", cascade="all, delete-orphan")
    agreements = relationship("AgreementModel", back_populates="session", cascade="all, delete-orphan")


class ParticipantModel(Base):
    __tablename__ = "participants"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    session_id = Column(GUID(), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    role = Column(String(32), nullable=False, default="participant")  # "creator" | "participant"
    token_hash = Column(String(64), nullable=False, index=True)
    joined_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    session = relationship("SessionModel", back_populates="participants")
    interpretations = relationship("InterpretationModel", back_populates="participant", cascade="all, delete-orphan")
    confirmations = relationship("AgreementConfirmationModel", back_populates="participant", cascade="all, delete-orphan")


class InterpretationModel(Base):
    __tablename__ = "interpretations"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    session_id = Column(GUID(), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    participant_id = Column(GUID(), ForeignKey("participants.id", ondelete="CASCADE"), nullable=False, index=True)
    response_text = Column(Text, nullable=False)
    assumptions = Column(UniversalJSON(), nullable=True)
    success_criteria = Column(UniversalJSON(), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    session = relationship("SessionModel", back_populates="interpretations")
    participant = relationship("ParticipantModel", back_populates="interpretations")

    __table_args__ = (
        UniqueConstraint("session_id", "participant_id", name="uq_session_participant_interpretation"),
    )


class AnalysisModel(Base):
    __tablename__ = "analyses"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    session_id = Column(GUID(), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    model_name = Column(String(64), nullable=True)
    prompt_version = Column(String(32), nullable=True)
    status = Column(String(32), nullable=False, default="pending", index=True)  # pending | analyzing | completed | failed
    result_json = Column(UniversalJSON(), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    session = relationship("SessionModel", back_populates="analyses")
    issues = relationship("IssueModel", back_populates="analysis", cascade="all, delete-orphan")


class IssueModel(Base):
    __tablename__ = "issues"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    session_id = Column(GUID(), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    analysis_id = Column(GUID(), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(64), nullable=False, index=True)  # contradiction, assumption, omission, scope_difference, success_criteria_difference
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    evidence_json = Column(UniversalJSON(), nullable=False)  # list of evidence objects
    priority = Column(String(16), nullable=False, index=True)  # low, medium, high
    clarification_question = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="open", index=True)  # open, discussing, resolved, dismissed
    resolution_text = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    session = relationship("SessionModel", back_populates="issues")
    analysis = relationship("AnalysisModel", back_populates="issues")


class AgreementModel(Base):
    __tablename__ = "agreements"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    session_id = Column(GUID(), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    content_json = Column(UniversalJSON(), nullable=False)  # structured checklist
    status = Column(String(32), nullable=False, default="pending_confirmation", index=True)  # draft, pending_confirmation, confirmed
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    # Relationships
    session = relationship("SessionModel", back_populates="agreements")
    confirmations = relationship("AgreementConfirmationModel", back_populates="agreement", cascade="all, delete-orphan")


class AgreementConfirmationModel(Base):
    __tablename__ = "agreement_confirmations"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    agreement_id = Column(GUID(), ForeignKey("agreements.id", ondelete="CASCADE"), nullable=False, index=True)
    participant_id = Column(GUID(), ForeignKey("participants.id", ondelete="CASCADE"), nullable=False, index=True)
    confirmed = Column(Boolean, nullable=False, default=True)
    comment = Column(Text, nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    agreement = relationship("AgreementModel", back_populates="confirmations")
    participant = relationship("ParticipantModel", back_populates="confirmations")

    __table_args__ = (
        UniqueConstraint("agreement_id", "participant_id", name="uq_agreement_participant_confirmation"),
    )
