from datetime import datetime
from typing import Any, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, model_validator
from backend.ai.schemas import (
    AnalysisStatus,
    ComplementaryPerspective,
    IssueCounts,
)


class SessionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    context: Optional[str] = Field(default=None, max_length=2000)
    creator_name: Optional[str] = Field(default=None, max_length=100)
    min_participants: Optional[int] = Field(default=2, ge=2, le=20)


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_code: str
    join_code: str
    title: str
    description: Optional[str] = None
    context: Optional[str] = None
    status: str
    min_participants: int = 2
    participant_count: int = 0
    creator_participant_id: Optional[str] = None
    participant_token: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class SessionJoinRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    join_code: str = Field(..., min_length=3, max_length=32)
    display_name: str = Field(..., min_length=1, max_length=100)
    participant_id: Optional[str] = Field(default=None, max_length=100)


class SessionJoinResponse(BaseModel):
    participant_id: str
    session_id: str
    display_name: str
    status: str
    participant_token: str


class ParticipantItem(BaseModel):
    """Privacy-preserving participant item strictly omitting interpretation text."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    display_name: str
    role: str
    has_submitted: bool
    joined_at: datetime


class SessionParticipantsResponse(BaseModel):
    session_id: str
    participants: list[ParticipantItem]


class SessionStatusResponse(BaseModel):
    session_id: str
    status: str
    participant_count: int
    submission_count: int
    min_participants: int
    user_has_submitted: bool
    can_start_analysis: bool
    user_interpretation: Optional[str] = None
    user_assumptions: Optional[str] = None
    user_success_criteria: Optional[str] = None


class MyInterpretationResponse(BaseModel):
    session_id: str
    participant_id: str
    display_name: str
    has_submitted: bool
    interpretation: Optional[str] = None
    assumptions: Optional[str] = None
    success_criteria: Optional[str] = None
    submitted_at: Optional[datetime] = None


class InterpretationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    response_text: Optional[str] = Field(default=None, max_length=5000)
    interpretation: Optional[str] = Field(default=None, max_length=5000)
    assumptions: Optional[Union[str, list[str]]] = None
    success_criteria: Optional[Union[str, list[str]]] = None

    @model_validator(mode="after")
    def validate_text_present(self) -> "InterpretationCreate":
        text = self.response_text or self.interpretation
        if not text or not text.strip():
            raise ValueError("Interpretation text cannot be blank.")
        return self


class InterpretationResponse(BaseModel):
    interpretation_id: str
    submitted: bool
    message: str


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
    submitted_at: Optional[datetime] = None


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
