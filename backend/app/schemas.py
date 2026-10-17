"""Pydantic schemas for request validation and API responses.
"""

from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field
from backend.ai.schemas import (
    AnalysisStatus,
    ComplementaryPerspective,
    Evidence,
    Issue,
    IssueCounts,
    IssueType,
    PriorityLevel,
)


# ============================================================================
# Session Schemas
# ============================================================================


class SessionCreate(BaseModel):
    """Payload to create a new collaborative task session."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="The shared task or instruction given to the team",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Optional additional context or background instructions",
    )


class SessionRead(BaseModel):
    """Response representation of a task session."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    session_code: str
    title: str
    description: Optional[str] = None
    status: str
    participant_count: int = 0
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Participant Schemas
# ============================================================================


class ParticipantCreate(BaseModel):
    """Payload for submitting an independent task interpretation."""

    model_config = ConfigDict(str_strip_whitespace=True)

    participant_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique identifier or handle for the participant",
    )
    name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Optional friendly display name",
    )
    interpretation: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="The participant's independent interpretation of the task",
    )
    assumptions: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Optional unconfirmed assumptions made by the participant",
    )
    success_criteria: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Optional definition of done or success criteria",
    )


class ParticipantRead(BaseModel):
    """Response representation of a participant's submission."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    participant_id: str
    name: Optional[str] = None
    interpretation: str
    assumptions: Optional[str] = None
    success_criteria: Optional[str] = None
    submitted_at: datetime


# ============================================================================
# Issue Schemas
# ============================================================================


class IssueRead(BaseModel):
    """Persisted misunderstanding finding returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    analysis_id: str
    type: str
    title: str
    description: str
    evidence: list[dict[str, Any]]
    impact: str
    priority: str
    confidence: float
    clarification_question: str
    resolution_status: str  # "open", "resolved", "dismissed"
    resolution_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class IssueUpdateStatus(BaseModel):
    """Payload to update the resolution status of an issue."""

    model_config = ConfigDict(str_strip_whitespace=True)

    resolution_status: Literal["open", "resolved", "dismissed"] = Field(
        ...,
        description="New status for the issue: open, resolved, or dismissed",
    )
    resolution_notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional context or agreed resolution notes from the team",
    )


# ============================================================================
# Analysis Response Schema
# ============================================================================


class AnalysisResponse(BaseModel):
    """API response for POST /api/sessions/{session_id}/analyze."""

    model_config = ConfigDict(from_attributes=True)

    session_id: str
    analysis_id: Optional[str] = None
    status: AnalysisStatus
    summary: str
    issues: list[IssueRead] = Field(default_factory=list)
    complementary_perspectives: list[ComplementaryPerspective] = Field(
        default_factory=list
    )
    issue_counts: IssueCounts
    error_message: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Agreement & Bridge Test Schemas
# ============================================================================


class AgreementRead(BaseModel):
    """Shared confirmed agreement / checklist."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    items: list[str] = Field(default_factory=list)
    excluded_items: list[str] = Field(default_factory=list)
    confirmed_by: list[str] = Field(default_factory=list)
    is_fully_confirmed: bool = False
    created_at: datetime
    updated_at: datetime


class AgreementConfirmPayload(BaseModel):
    """Payload for participant confirmation of the shared agreement."""

    model_config = ConfigDict(str_strip_whitespace=True)

    participant_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="ID of the participant confirming the agreement",
    )


class BridgeTestResponse(BaseModel):
    """Before vs After comparison metrics measuring misunderstanding resolution."""

    session_id: str
    initial_issues_count: int
    resolved_count: int
    dismissed_count: int
    open_count: int
    resolution_percentage: float
    is_fully_confirmed: bool
    confirmed_participants: list[str]
    total_participants: int
    bridge_status: str  # "bridged", "in_progress", "unresolved"
    disclaimer: str = (
        "This metric reflects the resolution of identified differences among participants, "
        "not proof of universal understanding."
    )

