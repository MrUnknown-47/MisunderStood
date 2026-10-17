from typing import Any, Optional
from pydantic import ValidationError

from backend.ai.client import (
    AIClientError,
    LLMClient,
)
from backend.ai.prompts import build_system_prompt, build_user_prompt
from backend.ai.schemas import (
    AnalysisResult,
    AnalysisStatus,
    ComplementaryPerspective,
    Issue,
    IssueCounts,
    ParticipantInput,
    TaskInput,
)
from backend.ai.validator import (
    EvidenceValidator,
    deduplicate_issues,
    normalize_whitespace,
)


async def analyze_interpretations(
    task: dict,
    participants: list[dict],
    client: Optional[LLMClient] = None,
) -> dict[str, Any]:
    try:
        validated_task = TaskInput.model_validate(task)
    except ValidationError as exc:
        return AnalysisResult(
            status=AnalysisStatus.FAILED,
            summary="Invalid task input schema.",
            error_message=f"Task validation failed: {str(exc)}",
            metadata={"validation_error": "task"},
        ).model_dump(mode="json")

    if not isinstance(participants, list):
        return AnalysisResult(
            status=AnalysisStatus.FAILED,
            summary="Participants must be provided as a list.",
            error_message="Invalid participants parameter: expected list.",
            metadata={"validation_error": "participants_type"},
        ).model_dump(mode="json")

    validated_participants: list[ParticipantInput] = []
    for idx, p in enumerate(participants):
        try:
            validated_p = ParticipantInput.model_validate(p)
            validated_participants.append(validated_p)
        except ValidationError as exc:
            return AnalysisResult(
                status=AnalysisStatus.FAILED,
                summary=f"Invalid participant input at index {idx}.",
                error_message=f"Participant validation failed: {str(exc)}",
                metadata={"validation_error": "participant", "index": idx},
            ).model_dump(mode="json")

    count = len(validated_participants)
    if count == 0:
        return AnalysisResult(
            status=AnalysisStatus.INSUFFICIENT_DATA,
            summary="No participant interpretations submitted yet.",
            metadata={"participant_count": 0, "bypassed_llm": True},
        ).model_dump(mode="json")

    if count == 1:
        return AnalysisResult(
            status=AnalysisStatus.INSUFFICIENT_DATA,
            summary=(
                "Analysis requires interpretations from at least 2 participants "
                "to detect differences or alignment. Only 1 participant has submitted so far."
            ),
            metadata={"participant_count": 1, "bypassed_llm": True},
        ).model_dump(mode="json")

    first_text = normalize_whitespace(validated_participants[0].interpretation)
    all_identical = all(
        normalize_whitespace(p.interpretation) == first_text
        and normalize_whitespace(p.assumptions or "")
        == normalize_whitespace(validated_participants[0].assumptions or "")
        and normalize_whitespace(p.success_criteria or "")
        == normalize_whitespace(validated_participants[0].success_criteria or "")
        for p in validated_participants
    )

    if all_identical and len(first_text) > 0:
        # If participants provided completely identical text, report clean consensus
        # while noting unstated background assumptions may still exist
        return AnalysisResult(
            status=AnalysisStatus.COMPLETED,
            summary=(
                f"All {count} participants submitted identical interpretations. "
                "Stated requirements are fully aligned; however, unstated background "
                "assumptions may still warrant verbal confirmation."
            ),
            issues=[],
            complementary_perspectives=[],
            issue_counts=IssueCounts(total=0, by_type={}, by_priority={}),
            metadata={"participant_count": count, "identical_inputs": True},
        ).model_dump(mode="json")

    llm = client or LLMClient()
    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(validated_task, validated_participants)

    try:
        raw_output = await llm.generate_structured_json(
            system_prompt, user_prompt
        )
    except AIClientError as exc:
        return AnalysisResult(
            status=AnalysisStatus.FAILED,
            summary="AI provider failed to complete analysis.",
            error_message=str(exc),
            metadata={
                "provider": getattr(llm, "provider", "unknown"),
                "model": getattr(llm, "model", "unknown"),
                "error_type": type(exc).__name__,
            },
        ).model_dump(mode="json")
    except Exception as exc:
        return AnalysisResult(
            status=AnalysisStatus.FAILED,
            summary="Unexpected error during AI analysis.",
            error_message=f"Runtime error: {str(exc)}",
            metadata={
                "provider": getattr(llm, "provider", "unknown"),
                "model": getattr(llm, "model", "unknown"),
                "error_type": type(exc).__name__,
            },
        ).model_dump(mode="json")

    summary = raw_output.get("summary", "Analysis completed.")
    if not isinstance(summary, str) or not summary.strip():
        summary = "Analysis completed."

    candidate_issues: list[Issue] = []
    raw_issues = raw_output.get("issues", [])
    if isinstance(raw_issues, list):
        for raw_iss in raw_issues:
            if isinstance(raw_iss, dict):
                try:
                    candidate_issues.append(Issue.model_validate(raw_iss))
                except ValidationError:
                    continue

    candidate_complements: list[ComplementaryPerspective] = []
    raw_complements = raw_output.get("complementary_perspectives", [])
    if isinstance(raw_complements, list):
        for raw_comp in raw_complements:
            if isinstance(raw_comp, dict):
                try:
                    candidate_complements.append(
                        ComplementaryPerspective.model_validate(raw_comp)
                    )
                except ValidationError:
                    continue

    validator = EvidenceValidator(validated_participants)
    verified_issues, dropped_quotes_iss, issue_rejections = (
        validator.validate_issues(candidate_issues)
    )
    verified_issues, dedup_reasons = deduplicate_issues(verified_issues)
    issue_rejections.extend(dedup_reasons)

    verified_complements, dropped_quotes_comp, comp_rejections = (
        validator.validate_complementary_perspectives(candidate_complements)
    )

    total_dropped_quotes = dropped_quotes_iss + dropped_quotes_comp
    total_candidate_findings = len(candidate_issues) + len(candidate_complements)
    total_verified_findings = len(verified_issues) + len(verified_complements)

    # If the model proposed findings but every quote failed verification, do not falsely report consensus
    if total_candidate_findings > 0 and total_verified_findings == 0:
        return AnalysisResult(
            status=AnalysisStatus.FAILED,
            summary="Analysis findings could not be verified against participant submissions.",
            error_message=(
                f"Evidence verification failed: all {total_candidate_findings} candidate finding(s) "
                "were rejected due to unverified or fabricated quotations."
            ),
            issues=[],
            complementary_perspectives=[],
            issue_counts=IssueCounts(total=0, by_type={}, by_priority={}),
            metadata={
                "provider": getattr(llm, "provider", "unknown"),
                "model": getattr(llm, "model", "unknown"),
                "participant_count": count,
                "unverified_quotes_dropped": total_dropped_quotes,
                "rejected_issue_count": len(issue_rejections),
                "rejection_reasons": issue_rejections + comp_rejections,
            },
        ).model_dump(mode="json")

    by_type: dict[str, int] = {}
    by_priority: dict[str, int] = {}
    for iss in verified_issues:
        t_val = iss.type.value
        p_val = iss.priority.value
        by_type[t_val] = by_type.get(t_val, 0) + 1
        by_priority[p_val] = by_priority.get(p_val, 0) + 1

    counts = IssueCounts(
        total=len(verified_issues),
        by_type=by_type,
        by_priority=by_priority,
    )

    return AnalysisResult(
        status=AnalysisStatus.COMPLETED,
        summary=summary,
        issues=verified_issues,
        complementary_perspectives=verified_complements,
        issue_counts=counts,
        error_message=None,
        metadata={
            "provider": getattr(llm, "provider", "unknown"),
            "model": getattr(llm, "model", "unknown"),
            "participant_count": count,
            "unverified_quotes_dropped": total_dropped_quotes,
            "rejected_issue_count": len(issue_rejections),
            "deduplicated_issue_count": len(dedup_reasons),
            "rejection_reasons": issue_rejections,
        },
    ).model_dump(mode="json")
