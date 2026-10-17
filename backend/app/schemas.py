from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field
from backend.ai.schemas import (
    AnalysisStatus,
    ComplementaryPerspective,
    IssueCounts,
)


class SessionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_code: str
    title: str
    description: Optional[str] = None
    status: str
    participant_count: int = 0
    created_at: datetime
    updated_at: datetime


class ParticipantCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    participant_id: str = Field(..., min_length=1, max_length=100)
    name: Optional[str] = Field(default=None, max_length=100)
    interpretation: str = Field(..., min_length=1, max_length=5000)
    assumptions: Optional[str] = Field(default=None, max_length=2000)
    success_criteria: Optional[str] = Field(default=None, max_length=2000)


class ParticipantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    participant_id: str
    name: Optional[str] = None
    interpretation: str
    assumptions: Optional[str] = None
    success_criteria: Optional[str] = None
    submitted_at: datetime


class IssueRead(BaseModel):
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
    resolution_status: str
    resolution_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class IssueUpdateStatus(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    resolution_status: Literal["open", "resolved", "dismissed"]
    resolution_notes: Optional[str] = Field(default=None, max_length=1000)


class AnalysisResponse(BaseModel):
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


class AgreementRead(BaseModel):
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
    model_config = ConfigDict(str_strip_whitespace=True)

    participant_id: str = Field(..., min_length=1, max_length=100)


class BridgeTestResponse(BaseModel):
    session_id: str
    initial_issues_count: int
    resolved_count: int
    dismissed_count: int
    open_count: int
    resolution_percentage: float
    is_fully_confirmed: bool
    confirmed_participants: list[str]
    total_participants: int
    bridge_status: str
    disclaimer: str = (
        "This metric reflects the resolution of identified differences among participants, "
        "not proof of universal understanding."
    )
