"""Pydantic v2 schemas for MISUNDERSTOOD AI analysis.

Defines input contracts, structured finding schemas, enums,
and the final AnalysisResult response structure.
"""

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class IssueType(str, Enum):
    """Supported types of misunderstanding issues."""

    CONTRADICTION = "contradiction"
    ASSUMPTION = "assumption"
    OMISSION = "omission"
    SCOPE_DIFFERENCE = "scope_difference"
    SUCCESS_CRITERIA_DIFFERENCE = "success_criteria_difference"


class PriorityLevel(str, Enum):
    """Priority levels for detected issues."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnalysisStatus(str, Enum):
    """Lifecycle / completion status of the analysis."""

    COMPLETED = "completed"
    INSUFFICIENT_DATA = "insufficient_data"
    FAILED = "failed"


class SourceField(str, Enum):
    """Which input field an evidence quote was sourced from."""

    INTERPRETATION = "interpretation"
    ASSUMPTIONS = "assumptions"
    SUCCESS_CRITERIA = "success_criteria"


# ============================================================================
# Input Models
# ============================================================================


class TaskInput(BaseModel):
    """Input representing the original task."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Title of the task or instruction",
    )
    description: Optional[str] = Field(
        default="",
        max_length=2000,
        description="Optional additional task context or constraints",
    )


class ParticipantInput(BaseModel):
    """Input representing a single participant's submitted interpretation."""

    model_config = ConfigDict(str_strip_whitespace=True)

    participant_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique identifier for the participant",
    )
    interpretation: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Participant's independent interpretation of the task",
    )
    assumptions: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Optional explicit assumptions made by the participant",
    )
    success_criteria: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Optional explicit definition of done or success criteria",
    )


# ============================================================================
# Evidence & Finding Models
# ============================================================================


class Evidence(BaseModel):
    """An exact, verified quotation extracted from a participant's input."""

    model_config = ConfigDict(str_strip_whitespace=True)

    participant_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="ID of the participant who provided this quote",
    )
    quote: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Exact verbatim excerpt from the participant's submitted text",
    )
    source_field: SourceField = Field(
        default=SourceField.INTERPRETATION,
        description="Which submitted field the quote was extracted from",
    )


class Issue(BaseModel):
    """A detected misunderstanding issue backed by verified participant evidence."""

    model_config = ConfigDict(str_strip_whitespace=True)

    type: IssueType = Field(..., description="Category of the misunderstanding issue")
    title: str = Field(
        ...,
        min_length=3,
        max_length=150,
        description="Short, neutral summary of the issue",
    )
    description: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="Detailed explanation of the difference without assigning blame",
    )
    evidence: list[Evidence] = Field(
        ...,
        min_length=1,
        description="Verifiable quotations from participant responses backing this finding",
    )
    impact: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Potential consequence if this difference remains unclarified",
    )
    priority: PriorityLevel = Field(
        ...,
        description="Tentative priority level based on potential impact",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Model confidence in this finding (0.0 to 1.0)",
    )
    clarification_question: str = Field(
        ...,
        min_length=5,
        max_length=300,
        description="Neutral, actionable question to help the team resolve the issue",
    )


class ComplementaryPerspective(BaseModel):
    """Perspectives from different participants that are compatible and not in conflict."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(
        ...,
        min_length=3,
        max_length=150,
        description="Short title describing the complementary perspectives",
    )
    description: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="Explanation of how these perspectives complement each other",
    )
    evidence: list[Evidence] = Field(
        ...,
        min_length=1,
        description="Quotes demonstrating the complementary viewpoints",
    )


# ============================================================================
# Result Summary & Counts
# ============================================================================


class IssueCounts(BaseModel):
    """Objective count metrics for detected issues."""

    total: int = 0
    by_type: dict[str, int] = Field(default_factory=dict)
    by_priority: dict[str, int] = Field(default_factory=dict)


class AnalysisResult(BaseModel):
    """Top-level structured output of the MISUNDERSTOOD analysis component."""

    model_config = ConfigDict(str_strip_whitespace=True)

    status: AnalysisStatus = Field(
        ...,
        description="Status of the analysis: completed, insufficient_data, or failed",
    )
    summary: str = Field(
        ...,
        max_length=1000,
        description="High-level synthesis of interpretations and alignment",
    )
    issues: list[Issue] = Field(
        default_factory=list,
        description="Verified misunderstanding issues identified across participants",
    )
    complementary_perspectives: list[ComplementaryPerspective] = Field(
        default_factory=list,
        description="Complementary viewpoints that can peacefully coexist",
    )
    issue_counts: IssueCounts = Field(
        default_factory=IssueCounts,
        description="Objective breakdown of issue counts by type and priority",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error details if status is failed",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Operational metadata such as model name, dropped quotes count, etc.",
    )
