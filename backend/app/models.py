import secrets
import uuid
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from backend.app.database import Base


def generate_session_code() -> str:
    """Generate a clean, unambiguous join code prefixed with GAP- (e.g. GAP-7K9M2P)."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    code = "".join(secrets.choice(alphabet) for _ in range(6))
    return f"GAP-{code[:3]}{code[3:]}"


class SessionModel(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_code = Column(
        String(32),
        unique=True,
        index=True,
        nullable=False,
        default=generate_session_code,
    )
    join_code = Column(
        String(32),
        unique=True,
        index=True,
        nullable=False,
        default=generate_session_code,
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    context = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="collecting")
    min_participants = Column(Integer, nullable=False, default=2)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    participants = relationship(
        "ParticipantModel",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ParticipantModel.joined_at",
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

    @property
    def participant_count(self) -> int:
        """Count of participants who have submitted an interpretation."""
        return len([
            p for p in self.participants
            if p.interpretation and str(p.interpretation).strip()
        ])


class ParticipantModel(Base):
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
    display_name = Column(String(100), nullable=True)
    role = Column(String(32), nullable=False, default="participant")
    token_hash = Column(String(64), nullable=True, index=True)
    interpretation = Column(Text, nullable=True)
    assumptions = Column(Text, nullable=True)
    success_criteria = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    joined_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session = relationship("SessionModel", back_populates="participants")

    @property
    def effective_name(self) -> str:
        return self.display_name or self.name or self.participant_id or "Participant"

    @property
    def has_submitted(self) -> bool:
        return bool(self.interpretation and str(self.interpretation).strip())


class AnalysisModel(Base):
    __tablename__ = "analyses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(
        String(36),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(String(30), nullable=False)
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
    resolution_status = Column(String(30), nullable=False, default="open")
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
    __tablename__ = "agreements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(
        String(36),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    items = Column(JSON, nullable=False, default=list)
    excluded_items = Column(JSON, nullable=False, default=list)
    confirmed_by = Column(JSON, nullable=False, default=list)
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
