import uuid
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict


# Enums and Types
SessionState = Literal[
    "collecting_responses",
    "analyzing",
    "reviewing_issues",
    "agreement_pending",
    "completed"
]

IssueType = Literal[
    "contradiction",
    "assumption",
    "omission",
    "scope_difference",
    "success_criteria_difference"
]

IssuePriority = Literal["low", "medium", "high"]

IssueStatus = Literal["open", "discussing", "resolved", "dismissed"]

AgreementStatus = Literal["draft", "pending_confirmation", "confirmed"]


# Generic Error Schema
class ErrorDetail(BaseModel):
    detail: str


# Health Schema
class HealthResponse(BaseModel):
    status: str
    database: str
    timestamp: datetime


# Session Schemas
class SessionCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Task title")
    description: str = Field(..., min_length=1, description="Original task or instruction")
    context: Optional[str] = Field(None, description="Optional background context, constraints, or goals")
    creator_name: Optional[str] = Field("Session Creator", min_length=1, max_length=100, description="Display name for creator")
    min_participants: Optional[int] = Field(2, ge=2, le=20, description="Minimum participants required before analysis")


class SessionCreateResponse(BaseModel):
    id: uuid.UUID
    join_code: str
    status: SessionState
    creator_participant_id: uuid.UUID
    participant_token: str


class SessionJoinRequest(BaseModel):
    join_code: str = Field(..., min_length=3, max_length=32, description="Case-insensitive session join code")
    display_name: str = Field(..., min_length=1, max_length=100, description="Participant display name")


class SessionJoinResponse(BaseModel):
    participant_id: uuid.UUID
    session_id: uuid.UUID
    status: SessionState
    participant_token: str


class SessionDetailResponse(BaseModel):
    id: uuid.UUID
    join_code: str
    title: str
    description: str
    context: Optional[str] = None
    status: SessionState
    min_participants: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ParticipantItem(BaseModel):
    id: uuid.UUID
    display_name: str
    role: str
    has_submitted: bool
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionParticipantsResponse(BaseModel):
    session_id: uuid.UUID
    participants: List[ParticipantItem]


class SessionStatusResponse(BaseModel):
    session_id: uuid.UUID
    status: SessionState
    participant_count: int
    submission_count: int
    min_participants: int
    user_has_submitted: bool
    can_start_analysis: bool


# Interpretation Schemas
class InterpretationCreateRequest(BaseModel):
    response_text: str = Field(..., min_length=1, description="Independent response explaining understanding of the task")
    assumptions: Optional[List[str]] = Field(default_factory=list, description="Optional list of explicit assumptions made")
    success_criteria: Optional[List[str]] = Field(default_factory=list, description="Optional list of completion criteria")


class InterpretationResponse(BaseModel):
    interpretation_id: uuid.UUID
    submitted: bool
    message: str


# AI and Issue Schemas
class IssueEvidence(BaseModel):
    participant_id: uuid.UUID
    quote: str


class CandidateIssue(BaseModel):
    type: IssueType
    title: str = Field(..., max_length=255)
    description: str
    evidence: List[IssueEvidence] = Field(..., min_length=1)
    priority: IssuePriority = "medium"
    clarification_question: str


class ComplementaryPerspective(BaseModel):
    title: str
    description: str
    evidence: Optional[List[IssueEvidence]] = Field(default_factory=list)


class AIAnalysisResult(BaseModel):
    summary: str
    issues: List[CandidateIssue]
    complementary_perspectives: Optional[List[ComplementaryPerspective]] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    analysis_id: uuid.UUID
    status: str
    issues_count: int


class IssueDetailResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    analysis_id: uuid.UUID
    type: IssueType
    title: str
    description: str
    evidence: List[IssueEvidence]
    priority: IssuePriority
    clarification_question: str
    status: IssueStatus
    resolution_text: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class IssuesListResponse(BaseModel):
    session_id: uuid.UUID
    issues: List[IssueDetailResponse]
    complementary_perspectives: List[ComplementaryPerspective]


class IssueUpdateRequest(BaseModel):
    status: IssueStatus
    resolution_text: Optional[str] = None


class IssueUpdateResponse(BaseModel):
    id: uuid.UUID
    status: IssueStatus
    resolution_text: Optional[str] = None


# Agreement Schemas
class AgreementItem(BaseModel):
    text: str
    source: str = "resolved_issue"  # "task_description" | "resolved_issue" | "ai_suggestion"


class AgreementContent(BaseModel):
    confirmed_requirements: List[AgreementItem] = Field(default_factory=list)
    unresolved_decisions: List[AgreementItem] = Field(default_factory=list)
    optional_suggestions: List[AgreementItem] = Field(default_factory=list)


class AgreementResponse(BaseModel):
    agreement_id: uuid.UUID
    session_id: uuid.UUID
    version: int
    status: AgreementStatus
    content: AgreementContent
    created_at: datetime


class AgreementConfirmRequest(BaseModel):
    confirmed: bool = True
    comment: Optional[str] = None


class AgreementConfirmResponse(BaseModel):
    confirmation_id: uuid.UUID
    agreement_id: uuid.UUID
    participant_id: uuid.UUID
    confirmed: bool
    all_participants_confirmed: bool
    session_status: SessionState


# Bridge Test Schemas
class BridgeTestMetrics(BaseModel):
    initial_issue_count: int
    resolved_issue_count: int
    unresolved_issue_count: int
    dismissed_issue_count: int
    resolution_rate: Optional[float] = None
    agreement_status: str
