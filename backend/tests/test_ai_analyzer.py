"""Automated unit and integration tests for MISUNDERSTOOD AI module.

Verifies:
- Required test scenarios A through E
- Evidence integrity & zero-hallucination guard
- Failure states vs valid consensus
- Deterministic short-circuits (0, 1, and identical participants)
- Provider errors, timeouts, and malformed JSON recovery
All unit tests run completely offline without network calls or API credits.
"""

from unittest.mock import AsyncMock, patch
import pytest

from backend.ai.analyzer import analyze_interpretations
from backend.ai.client import (
    AIAuthError,
    AIMalformedJSONError,
    AIProviderError,
    AIProviderTimeoutError,
    LLMClient,
    extract_json_from_text,
)
from backend.ai.schemas import (
    AnalysisStatus,
    Evidence,
    Issue,
    IssueType,
    ParticipantInput,
    PriorityLevel,
    SourceField,
)
from backend.ai.validator import EvidenceValidator, normalize_whitespace
from backend.tests.mock_data import (
    SCENARIO_A_MOCK_RESPONSE,
    SCENARIO_A_PARTICIPANTS,
    SCENARIO_A_TASK,
    SCENARIO_B_MOCK_RESPONSE,
    SCENARIO_B_PARTICIPANTS,
    SCENARIO_B_TASK,
    SCENARIO_C_MOCK_RESPONSE,
    SCENARIO_C_PARTICIPANTS,
    SCENARIO_C_TASK,
    SCENARIO_D_MOCK_RESPONSE,
    SCENARIO_D_PARTICIPANTS,
    SCENARIO_D_TASK,
    SCENARIO_E_MOCK_RESPONSE,
    SCENARIO_E_PARTICIPANTS,
    SCENARIO_E_TASK,
)


# ============================================================================
# Helpers: Mock LLM Client
# ============================================================================


def make_mock_client(return_data=None, raise_exc=None):
    """Create an LLMClient with mocked generate_structured_json."""
    client = LLMClient(api_key="mock-key-12345", model="mock-model")
    mock_func = AsyncMock()
    if raise_exc:
        mock_func.side_effect = raise_exc
    else:
        mock_func.return_value = return_data or {}
    client.generate_structured_json = mock_func
    return client


# ============================================================================
# Evidence Validator Unit Tests (Isolated from Prompt/LLM)
# ============================================================================


class TestEvidenceValidator:
    """Test deterministic quote verification without any LLM dependencies."""

    def test_exact_quote_match(self):
        p1 = ParticipantInput(
            participant_id="user-1",
            interpretation="We need to build password reset and email signup.",
        )
        validator = EvidenceValidator([p1])

        ev = Evidence(participant_id="user-1", quote="password reset")
        verified = validator.verify_quote(ev)

        assert verified is not None
        assert verified.quote == "password reset"
        assert verified.source_field == SourceField.INTERPRETATION

    def test_whitespace_normalization_match(self):
        p1 = ParticipantInput(
            participant_id="user-1",
            interpretation="We need\n\t  to build   password reset.",
        )
        validator = EvidenceValidator([p1])

        ev = Evidence(
            participant_id="user-1", quote="to build password reset."
        )
        verified = validator.verify_quote(ev)

        assert verified is not None
        assert verified.quote == "to build password reset."

    def test_fabricated_quote_rejected(self):
        p1 = ParticipantInput(
            participant_id="user-1",
            interpretation="We need to build password reset and email signup.",
        )
        validator = EvidenceValidator([p1])

        # Fabricated quote never stated by user-1
        ev = Evidence(
            participant_id="user-1", quote="Integrate Google OAuth SSO"
        )
        verified = validator.verify_quote(ev)

        assert verified is None

    def test_unknown_participant_id_rejected(self):
        p1 = ParticipantInput(
            participant_id="user-1", interpretation="Some text"
        )
        validator = EvidenceValidator([p1])

        ev = Evidence(participant_id="user-unknown", quote="Some text")
        verified = validator.verify_quote(ev)

        assert verified is None

    def test_contradiction_rejected_if_single_participant_cited(self):
        p1 = ParticipantInput(participant_id="p-1", interpretation="Feature X")
        p2 = ParticipantInput(
            participant_id="p-2", interpretation="Opposite of Feature X"
        )
        validator = EvidenceValidator([p1, p2])

        single_party_contradiction = Issue(
            type=IssueType.CONTRADICTION,
            title="Conflict on Feature X",
            description="They disagree on Feature X",
            evidence=[Evidence(participant_id="p-1", quote="Feature X")],
            impact="Build discrepancy",
            priority=PriorityLevel.HIGH,
            confidence=0.9,
            clarification_question="Should we build Feature X?",
        )

        verified, dropped_quotes, reasons = validator.validate_issues(
            [single_party_contradiction]
        )
        assert len(verified) == 0
        assert "requires evidence from at least 2 distinct participants" in (
            reasons[0]
        )

    def test_contradiction_accepted_when_both_participants_cited(self):
        p1 = ParticipantInput(participant_id="p-1", interpretation="Feature X")
        p2 = ParticipantInput(
            participant_id="p-2", interpretation="Opposite of Feature X"
        )
        validator = EvidenceValidator([p1, p2])

        valid_contradiction = Issue(
            type=IssueType.CONTRADICTION,
            title="Conflict on Feature X",
            description="They disagree on Feature X",
            evidence=[
                Evidence(participant_id="p-1", quote="Feature X"),
                Evidence(
                    participant_id="p-2", quote="Opposite of Feature X"
                ),
            ],
            impact="Build discrepancy",
            priority=PriorityLevel.HIGH,
            confidence=0.9,
            clarification_question="Should we build Feature X?",
        )

        verified, dropped_quotes, reasons = validator.validate_issues(
            [valid_contradiction]
        )
        assert len(verified) == 1
        assert len(reasons) == 0


# ============================================================================
# Required Scenarios A through E
# ============================================================================


class TestRequiredScenarios:
    """Tests the 5 core project scenarios required by the specification."""

    @pytest.mark.asyncio
    async def test_scenario_a_scope_difference(self):
        """Test A: Clear scope difference between email login vs phone+recovery."""
        mock_client = make_mock_client(return_data=SCENARIO_A_MOCK_RESPONSE)

        result = await analyze_interpretations(
            SCENARIO_A_TASK, SCENARIO_A_PARTICIPANTS, client=mock_client
        )

        assert result["status"] == AnalysisStatus.COMPLETED
        assert result["issue_counts"]["total"] == 1
        assert (
            result["issue_counts"]["by_type"][IssueType.SCOPE_DIFFERENCE.value]
            == 1
        )

        issue = result["issues"][0]
        assert issue["type"] == IssueType.SCOPE_DIFFERENCE.value
        assert len(issue["evidence"]) == 2

        # Verify evidence citations map to both participants
        evidence_pids = {ev["participant_id"] for ev in issue["evidence"]}
        assert evidence_pids == {"participant-a", "participant-b"}

        # Verify neutral clarification question
        assert "Should phone login" in issue["clarification_question"]

    @pytest.mark.asyncio
    async def test_scenario_b_complementary_requirements(self):
        """Test B: Mobile responsiveness and accessibility are complementary, not conflicts."""
        mock_client = make_mock_client(return_data=SCENARIO_B_MOCK_RESPONSE)

        result = await analyze_interpretations(
            SCENARIO_B_TASK, SCENARIO_B_PARTICIPANTS, client=mock_client
        )

        assert result["status"] == AnalysisStatus.COMPLETED
        # No conflicting issues manufactured
        assert len(result["issues"]) == 0
        assert result["issue_counts"]["total"] == 0

        # Identified as complementary perspective
        assert len(result["complementary_perspectives"]) == 1
        comp = result["complementary_perspectives"][0]
        assert "responsiveness" in comp["title"].lower()
        assert len(comp["evidence"]) == 2

    @pytest.mark.asyncio
    async def test_scenario_c_unconfirmed_requirement(self):
        """Test C: Password recovery is an unconfirmed scope item (omission), not proven disagreement."""
        mock_client = make_mock_client(return_data=SCENARIO_C_MOCK_RESPONSE)

        result = await analyze_interpretations(
            SCENARIO_C_TASK, SCENARIO_C_PARTICIPANTS, client=mock_client
        )

        assert result["status"] == AnalysisStatus.COMPLETED
        assert len(result["issues"]) == 1

        issue = result["issues"][0]
        assert issue["type"] == IssueType.OMISSION.value
        assert "password recovery" in issue["evidence"][0]["quote"].lower()
        # Does not accuse participant of being wrong
        assert "unconfirmed" in issue["description"].lower()

    @pytest.mark.asyncio
    async def test_scenario_d_similar_interpretations(self):
        """Test D: Semantically similar interpretations produce no manufactured conflicts."""
        mock_client = make_mock_client(return_data=SCENARIO_D_MOCK_RESPONSE)

        result = await analyze_interpretations(
            SCENARIO_D_TASK, SCENARIO_D_PARTICIPANTS, client=mock_client
        )

        assert result["status"] == AnalysisStatus.COMPLETED
        assert len(result["issues"]) == 0
        assert result["issue_counts"]["total"] == 0

    @pytest.mark.asyncio
    async def test_scenario_e_insufficient_evidence(self):
        """Test E: Vague responses ('make it good') do not manufacture fake assumptions or omissions,

        and ask for clarification in the summary.
        """
        mock_client = make_mock_client(return_data=SCENARIO_E_MOCK_RESPONSE)

        result = await analyze_interpretations(
            SCENARIO_E_TASK, SCENARIO_E_PARTICIPANTS, client=mock_client
        )

        assert result["status"] == AnalysisStatus.COMPLETED
        # No unsupported assumptions, omissions, or contradictions manufactured
        assert len(result["issues"]) == 0
        assert result["issue_counts"]["total"] == 0
        assert (
            "vague" in result["summary"].lower()
            or "insufficient" in result["summary"].lower()
        )
        # System explicitly asks for clarification to resolve ambiguity
        assert (
            "clarification" in result["summary"].lower()
            or "?" in result["summary"]
        )


# ============================================================================
# Edge Cases, Short-Circuits & Failure Modes
# ============================================================================


class TestEdgeCasesAndFailureModes:
    """Test boundary conditions, input guards, short-circuits, and provider failures."""

    @pytest.mark.asyncio
    async def test_zero_participants_returns_insufficient_data(self):
        """Zero participants must return insufficient_data and never call the LLM."""
        mock_client = make_mock_client()

        result = await analyze_interpretations(
            {"title": "Task 1"}, [], client=mock_client
        )

        assert result["status"] == AnalysisStatus.INSUFFICIENT_DATA
        assert result["metadata"]["bypassed_llm"] is True
        mock_client.generate_structured_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_one_participant_returns_insufficient_data(self):
        """A single participant cannot establish alignment; bypasses LLM call."""
        mock_client = make_mock_client()
        single_p = [
            {"participant_id": "p-1", "interpretation": "Only one person"}
        ]

        result = await analyze_interpretations(
            {"title": "Task 1"}, single_p, client=mock_client
        )

        assert result["status"] == AnalysisStatus.INSUFFICIENT_DATA
        assert result["metadata"]["participant_count"] == 1
        assert result["metadata"]["bypassed_llm"] is True
        mock_client.generate_structured_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_identical_interpretations_bypasses_or_reports_clean_consensus(
        self,
    ):
        """Identical texts must produce zero issues and note alignment."""
        mock_client = make_mock_client()
        identical_participants = [
            {
                "participant_id": "p-1",
                "interpretation": "Deploy to production by 5 PM.",
            },
            {
                "participant_id": "p-2",
                "interpretation": "Deploy to production by 5 PM.",
            },
        ]

        result = await analyze_interpretations(
            {"title": "Deployment"},
            identical_participants,
            client=mock_client,
        )

        assert result["status"] == AnalysisStatus.COMPLETED
        assert len(result["issues"]) == 0
        assert result["metadata"].get("identical_inputs") is True
        assert "identical" in result["summary"].lower()
        mock_client.generate_structured_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_all_findings_rejected_fails_safely_without_false_consensus(self):
        """When the LLM proposes multiple findings but EVERY finding is rejected by evidence

        validation, the system MUST return status=FAILED and never falsely report consensus.
        """
        all_fabricated_response = {
            "summary": "Detected multiple critical conflicts between participants.",
            "issues": [
                {
                    "type": "contradiction",
                    "title": "Database architecture contradiction",
                    "description": "Participants disagree on PostgreSQL vs MongoDB.",
                    "evidence": [
                        {
                            "participant_id": "participant-a",
                            "quote": "Must use MongoDB NoSQL cluster.",  # Fabricated
                        },
                        {
                            "participant_id": "participant-b",
                            "quote": "Must use PostgreSQL relational DB.",  # Fabricated
                        },
                    ],
                    "impact": "Architecture mismatch",
                    "priority": "critical",
                    "confidence": 0.95,
                    "clarification_question": "Which database engine should be used?",
                },
                {
                    "type": "assumption",
                    "title": "OAuth provider assumption",
                    "description": "Participant assumed Google OAuth SSO.",
                    "evidence": [
                        {
                            "participant_id": "participant-a",
                            "quote": "Require Google Workspace OAuth2 login.",  # Fabricated
                        }
                    ],
                    "impact": "Auth failure",
                    "priority": "high",
                    "confidence": 0.9,
                    "clarification_question": "Is Google OAuth required?",
                },
            ],
            "complementary_perspectives": [],
        }

        mock_client = make_mock_client(return_data=all_fabricated_response)

        result = await analyze_interpretations(
            SCENARIO_A_TASK, SCENARIO_A_PARTICIPANTS, client=mock_client
        )

        # Must NOT return COMPLETED with 0 issues (which would communicate false consensus)
        assert result["status"] == AnalysisStatus.FAILED
        assert "evidence verification failed" in result["error_message"].lower()
        assert result["metadata"]["rejected_issue_count"] == 2
        assert result["metadata"]["unverified_quotes_dropped"] == 3
        assert len(result["issues"]) == 0

    @pytest.mark.asyncio
    async def test_partially_fabricated_findings_retains_valid_and_drops_invalid(self):
        """When some findings have authentic evidence and others have fabricated quotes,

        the valid findings are retained and invalid findings are dropped.
        """
        partially_fabricated_response = {
            "summary": "Detected scope difference and an unverified assumption.",
            "issues": [
                # Finding 1: Valid quotes from Scenario A participants
                {
                    "type": "scope_difference",
                    "title": "Discrepancy in login methods",
                    "description": "Participant A expects email only; B expects email or phone.",
                    "evidence": [
                        {
                            "participant_id": "participant-a",
                            "quote": "Finish email and password login.",
                        },
                        {
                            "participant_id": "participant-b",
                            "quote": "Finish email or phone login",
                        },
                    ],
                    "impact": "Scope mismatch",
                    "priority": "high",
                    "confidence": 0.9,
                    "clarification_question": "Should phone login be supported?",
                },
                # Finding 2: Fabricated quote
                {
                    "type": "assumption",
                    "title": "Unverified cloud provider",
                    "description": "Participant assumed AWS deployment.",
                    "evidence": [
                        {
                            "participant_id": "participant-a",
                            "quote": "Deploy exclusively to AWS us-east-1.",  # Fabricated
                        }
                    ],
                    "impact": "Infra mismatch",
                    "priority": "medium",
                    "confidence": 0.8,
                    "clarification_question": "Which cloud provider should we use?",
                },
            ],
            "complementary_perspectives": [],
        }

        mock_client = make_mock_client(return_data=partially_fabricated_response)

        result = await analyze_interpretations(
            SCENARIO_A_TASK, SCENARIO_A_PARTICIPANTS, client=mock_client
        )

        # Retains the 1 verified issue
        assert result["status"] == AnalysisStatus.COMPLETED
        assert len(result["issues"]) == 1
        assert result["issues"][0]["type"] == IssueType.SCOPE_DIFFERENCE.value
        # Drops the 1 invalid issue
        assert result["metadata"]["rejected_issue_count"] == 1
        assert result["metadata"]["unverified_quotes_dropped"] == 1

    @pytest.mark.asyncio
    async def test_provider_timeout_returns_failed_status(self):
        """Provider timeout returns status=failed and never masks as successful consensus."""
        mock_client = make_mock_client(
            raise_exc=AIProviderTimeoutError("Request timed out.")
        )

        result = await analyze_interpretations(
            SCENARIO_A_TASK, SCENARIO_A_PARTICIPANTS, client=mock_client
        )

        assert result["status"] == AnalysisStatus.FAILED
        assert result["error_message"] == "Request timed out."
        assert len(result["issues"]) == 0

    @pytest.mark.asyncio
    async def test_provider_500_error_returns_failed_status(self):
        """Provider 500 error returns status=failed."""
        mock_client = make_mock_client(
            raise_exc=AIProviderError("HTTP 500 Internal Error", status_code=500)
        )

        result = await analyze_interpretations(
            SCENARIO_A_TASK, SCENARIO_A_PARTICIPANTS, client=mock_client
        )

        assert result["status"] == AnalysisStatus.FAILED
        assert "HTTP 500" in result["error_message"]
        assert len(result["issues"]) == 0

    @pytest.mark.asyncio
    async def test_malformed_json_returns_failed_status(self):
        """Model returning unparseable garbage returns status=failed."""
        mock_client = make_mock_client(
            raise_exc=AIMalformedJSONError("Failed to extract valid JSON.")
        )

        result = await analyze_interpretations(
            SCENARIO_A_TASK, SCENARIO_A_PARTICIPANTS, client=mock_client
        )

        assert result["status"] == AnalysisStatus.FAILED
        assert "Failed to extract valid JSON" in result["error_message"]
        assert len(result["issues"]) == 0

    @pytest.mark.asyncio
    async def test_input_validation_failure_on_missing_fields(self):
        """Missing task title triggers input validation failure."""
        mock_client = make_mock_client()

        # Task missing required 'title'
        result = await analyze_interpretations(
            {}, SCENARIO_A_PARTICIPANTS, client=mock_client
        )

        assert result["status"] == AnalysisStatus.FAILED
        assert "validation failed" in result["error_message"].lower()

    @pytest.mark.asyncio
    async def test_input_validation_failure_on_invalid_participants_type(self):
        """Non-list participants parameter triggers input validation failure."""
        mock_client = make_mock_client()

        result = await analyze_interpretations(
            {"title": "Valid"}, "not-a-list", client=mock_client
        )

        assert result["status"] == AnalysisStatus.FAILED
        assert "expected list" in result["error_message"].lower()


# ============================================================================
# Client JSON Parser Unit Tests
# ============================================================================


class TestClientJSONParser:
    """Test robustness of the LLM output JSON extractor."""

    def test_extract_from_clean_json(self):
        raw = '{"summary": "All good", "issues": []}'
        assert extract_json_from_text(raw) == {
            "summary": "All good",
            "issues": [],
        }

    def test_extract_from_markdown_fences(self):
        raw = 'Here is the result:\n```json\n{"summary": "Test", "issues": []}\n```\n'
        assert extract_json_from_text(raw) == {
            "summary": "Test",
            "issues": [],
        }

    def test_extract_from_commentary_with_braces(self):
        raw = 'Based on analysis: {"summary": "Analysis", "count": 2}. Let me know if you need more.'
        assert extract_json_from_text(raw) == {
            "summary": "Analysis",
            "count": 2,
        }

    def test_unparseable_raises_malformed_json_error(self):
        with pytest.raises(AIMalformedJSONError):
            extract_json_from_text("Sorry, I cannot answer this request.")


# ============================================================================
# Deduplication & Overlapping Findings Tests (Task 1)
# ============================================================================


class TestIssueDeduplication:
    """Tests deduplication and retention of distinct vs redundant findings."""

    @pytest.mark.asyncio
    async def test_distinct_findings_sharing_evidence_both_retained(self):
        """When findings share participant quotes but require distinct clarification

        decisions, both findings must be retained.
        """
        response_data = {
            "summary": "Detected distinct scope differences.",
            "issues": [
                {
                    "type": "scope_difference",
                    "title": "Login methods differ",
                    "description": "Participant A expects email only; B expects email or phone.",
                    "evidence": [
                        {
                            "participant_id": "participant-a",
                            "quote": "Finish email and password login.",
                        },
                        {
                            "participant_id": "participant-b",
                            "quote": (
                                "Finish email or phone login, registration, and"
                                " password recovery."
                            ),
                        },
                    ],
                    "impact": "Auth scope divergence",
                    "priority": "high",
                    "confidence": 0.9,
                    "clarification_question": (
                        "Should phone login be supported in addition to email"
                        " login?"
                    ),
                },
                {
                    "type": "scope_difference",
                    "title": (
                        "Registration and password recovery have different"
                        " expected scope"
                    ),
                    "description": (
                        "Participant B expects registration and recovery; A does"
                        " not mention them."
                    ),
                    "evidence": [
                        {
                            "participant_id": "participant-a",
                            "quote": "Finish email and password login.",
                        },
                        {
                            "participant_id": "participant-b",
                            "quote": (
                                "Finish email or phone login, registration, and"
                                " password recovery."
                            ),
                        },
                    ],
                    "impact": "Account lifecycle scope divergence",
                    "priority": "medium",
                    "confidence": 0.85,
                    "clarification_question": (
                        "Should user registration and password recovery be part"
                        " of the launch release?"
                    ),
                },
            ],
            "complementary_perspectives": [],
        }

        mock_client = make_mock_client(return_data=response_data)
        result = await analyze_interpretations(
            SCENARIO_A_TASK, SCENARIO_A_PARTICIPANTS, client=mock_client
        )

        assert result["status"] == AnalysisStatus.COMPLETED
        # Both distinct decisions must be retained
        assert len(result["issues"]) == 2
        titles = {iss["title"] for iss in result["issues"]}
        assert "Login methods differ" in titles
        assert (
            "Registration and password recovery have different expected scope"
            in titles
        )

    @pytest.mark.asyncio
    async def test_overlapping_restatements_are_deduplicated(self):
        """When a finding merely restates another or serves as a generic umbrella,

        it must be deduplicated so the user is not shown redundant issues.
        """
        response_data = {
            "summary": "Detected overlapping differences.",
            "issues": [
                # Primary specific issue
                {
                    "type": "scope_difference",
                    "title": "Login methods differ",
                    "description": (
                        "Participant A expects email only; B expects email or"
                        " phone."
                    ),
                    "evidence": [
                        {
                            "participant_id": "participant-a",
                            "quote": "Finish email and password login.",
                        },
                        {
                            "participant_id": "participant-b",
                            "quote": "Finish email or phone login",
                        },
                    ],
                    "impact": "Auth mismatch",
                    "priority": "high",
                    "confidence": 0.9,
                    "clarification_question": (
                        "Should phone login be supported in addition to email"
                        " login?"
                    ),
                },
                # Duplicate restatement of primary issue
                {
                    "type": "scope_difference",
                    "title": "Conflicting login options",
                    "description": "Different login methods were specified.",
                    "evidence": [
                        {
                            "participant_id": "participant-a",
                            "quote": "Finish email and password login.",
                        },
                        {
                            "participant_id": "participant-b",
                            "quote": "Finish email or phone login",
                        },
                    ],
                    "impact": "Auth mismatch",
                    "priority": "high",
                    "confidence": 0.85,
                    "clarification_question": (
                        "Should phone login be included alongside email login?"
                    ),
                },
                # Generic umbrella issue subsumed by specific issues
                {
                    "type": "scope_difference",
                    "title": "Authentication features differ overall",
                    "description": "General differences in auth features.",
                    "evidence": [
                        {
                            "participant_id": "participant-a",
                            "quote": "Finish email and password login.",
                        },
                        {
                            "participant_id": "participant-b",
                            "quote": "Finish email or phone login",
                        },
                    ],
                    "impact": "Auth mismatch",
                    "priority": "high",
                    "confidence": 0.8,
                    "clarification_question": (
                        "What authentication features should be included for"
                        " the launch?"
                    ),
                },
            ],
            "complementary_perspectives": [],
        }

        mock_client = make_mock_client(return_data=response_data)
        result = await analyze_interpretations(
            SCENARIO_A_TASK, SCENARIO_A_PARTICIPANTS, client=mock_client
        )

        assert result["status"] == AnalysisStatus.COMPLETED
        # The 2 redundant restatements must be pruned; only 1 distinct issue kept
        assert len(result["issues"]) == 1
        assert result["issues"][0]["title"] == "Login methods differ"
        assert result["metadata"]["deduplicated_issue_count"] == 2


# ============================================================================
# Priority Calibration Tests (Task 2)
# ============================================================================


class TestPriorityCalibration:
    """Tests that priority assignments appropriately reflect severity and uncertainty."""

    @pytest.mark.asyncio
    async def test_unconfirmed_secondary_feature_is_medium_priority(self):
        """Unconfirmed secondary items should be medium priority, not escalated to critical."""
        mock_client = make_mock_client(return_data=SCENARIO_C_MOCK_RESPONSE)
        result = await analyze_interpretations(
            SCENARIO_C_TASK, SCENARIO_C_PARTICIPANTS, client=mock_client
        )

        assert result["status"] == AnalysisStatus.COMPLETED
        assert len(result["issues"]) == 1
        issue = result["issues"][0]
        assert issue["priority"] == PriorityLevel.MEDIUM.value
        assert issue["priority"] != PriorityLevel.CRITICAL.value

    @pytest.mark.asyncio
    async def test_architectural_contradiction_is_critical_priority(self):
        """Direct architectural contradictions that produce breaking implementations are critical."""
        contradiction_response = {
            "summary": (
                "Critical contradiction in session management architecture."
            ),
            "issues": [
                {
                    "type": "contradiction",
                    "title": "Incompatible session persistence architecture",
                    "description": (
                        "Participant A requires immediate logout on window"
                        " close; Participant B requires permanent login across"
                        " sessions."
                    ),
                    "evidence": [
                        {
                            "participant_id": "participant-a",
                            "quote": (
                                "Log out immediately when browser closes."
                            ),
                        },
                        {
                            "participant_id": "participant-b",
                            "quote": (
                                "Remain logged in permanently across sessions."
                            ),
                        },
                    ],
                    "impact": "Mutually exclusive token lifecycle designs.",
                    "priority": "critical",
                    "confidence": 0.95,
                    "clarification_question": (
                        "Should user authentication tokens expire upon browser"
                        " close or persist permanently?"
                    ),
                }
            ],
            "complementary_perspectives": [],
        }

        participants = [
            {
                "participant_id": "participant-a",
                "interpretation": "Log out immediately when browser closes.",
            },
            {
                "participant_id": "participant-b",
                "interpretation": (
                    "Remain logged in permanently across sessions."
                ),
            },
        ]

        mock_client = make_mock_client(return_data=contradiction_response)
        result = await analyze_interpretations(
            {"title": "Session management"}, participants, client=mock_client
        )

        assert result["status"] == AnalysisStatus.COMPLETED
        assert len(result["issues"]) == 1
        assert result["issues"][0]["priority"] == PriorityLevel.CRITICAL.value


# ============================================================================
# Provider Configuration & Fallback Tests (Task 3)
# ============================================================================


class TestProviderConfigurationAndFallback:
    """Tests provider selection, fallback chains, and explicit provider isolation."""

    def test_provider_selection_gemini(self, monkeypatch):
        monkeypatch.setenv("AI_PROVIDER", "gemini")
        monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
        client = LLMClient()
        assert client.provider == "gemini"
        assert client.model == "gemini-2.5-flash"
        assert client.is_auto is False

    def test_provider_selection_openrouter(self, monkeypatch):
        monkeypatch.setenv("AI_PROVIDER", "openrouter")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-or-key")
        client = LLMClient()
        assert client.provider == "openrouter"
        assert client.model == "google/gemini-2.5-flash"
        assert client.is_auto is False

    def test_provider_selection_openai(self, monkeypatch):
        monkeypatch.setenv("AI_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "test-oa-key")
        client = LLMClient()
        assert client.provider == "openai"
        assert client.model == "gpt-4o-mini"
        assert client.is_auto is False

    def test_auto_provider_preference_order(self, monkeypatch):
        # 1. When all keys exist, auto selects gemini
        monkeypatch.setenv("AI_PROVIDER", "auto")
        monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-or-key")
        monkeypatch.setenv("OPENAI_API_KEY", "test-oa-key")
        client = LLMClient()
        assert client.provider == "gemini"
        assert client.is_auto is True

        # 2. When gemini key is missing, auto selects openrouter
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        client2 = LLMClient()
        assert client2.provider == "openrouter"

        # 3. When only openai key is present, auto selects openai
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        client3 = LLMClient()
        assert client3.provider == "openai"

    @pytest.mark.asyncio
    async def test_explicit_provider_does_not_switch_on_failure(self, monkeypatch):
        """When AI_PROVIDER is explicitly 'gemini', failure must raise immediately

        and NEVER silently switch to OpenRouter.
        """
        monkeypatch.setenv("AI_PROVIDER", "gemini")
        monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-or-key")

        client = LLMClient(provider="gemini")
        with patch.object(
            client,
            "_call_gemini_direct",
            side_effect=AIProviderError("Gemini internal error"),
        ):
            with pytest.raises(AIProviderError) as exc_info:
                await client.generate_structured_json("system", "user")

            assert "Gemini internal error" in str(exc_info.value)
            # Verify provider remained gemini and did not switch to openrouter
            assert client.provider == "gemini"

    @pytest.mark.asyncio
    async def test_auto_mode_falls_back_when_primary_fails(self, monkeypatch):
        """In auto mode, if Gemini fails, client gracefully falls back to OpenRouter."""
        monkeypatch.setenv("AI_PROVIDER", "auto")
        monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-or-key")

        client = LLMClient(provider="auto")

        async def mock_gemini(*args):
            raise AIProviderError("Gemini service unavailable")

        async def mock_openrouter(*args):
            return {"status": "ok", "provider": "openrouter"}

        with patch.object(
            client, "_call_gemini_direct", side_effect=mock_gemini
        ):
            with patch.object(
                client, "_call_openrouter_direct", side_effect=mock_openrouter
            ):
                result = await client.generate_structured_json(
                    "system", "user"
                )

                assert result == {"status": "ok", "provider": "openrouter"}
                # Verify provider updated to the fallback provider that succeeded
                assert client.provider == "openrouter"

    def test_credentials_never_exposed_in_auth_error(self, monkeypatch):
        """AIAuthError messages must never print raw API keys."""
        client = LLMClient(provider="none", api_key="")
        import asyncio

        with pytest.raises(AIAuthError) as exc_info:
            asyncio.run(client.generate_structured_json("system", "user"))

        err_msg = str(exc_info.value)
        assert "sk-" not in err_msg
        assert "AQ." not in err_msg

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "primary_error",
        [
            AIAuthError("Gemini authentication failed: invalid API key."),
            AIProviderError("Gemini quota or credit limit reached.", status_code=429),
            AIProviderError("Transient rate limit exceeded (HTTP 429)", status_code=429),
            AIProviderTimeoutError("Gemini request timed out after 30.0s."),
            AIProviderError("Transient provider error (HTTP 500)", status_code=500),
            AIMalformedJSONError("Failed to extract valid JSON object from model response."),
        ],
        ids=["auth_error", "quota_exhausted", "rate_limit", "timeout", "server_500", "malformed_json"],
    )
    async def test_auto_mode_falls_back_on_eligible_errors(self, monkeypatch, primary_error):
        """Verify auto mode gracefully cascades on all 6 classified eligible fallback errors."""
        monkeypatch.setenv("AI_PROVIDER", "auto")
        monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-or-key")

        client = LLMClient(provider="auto")

        async def mock_gemini(*args):
            raise primary_error

        async def mock_openrouter(*args):
            return {"status": "ok", "provider": "openrouter"}

        with patch.object(client, "_call_gemini_direct", side_effect=mock_gemini):
            with patch.object(client, "_call_openrouter_direct", side_effect=mock_openrouter):
                result = await client.generate_structured_json("system", "user")
                assert result == {"status": "ok", "provider": "openrouter"}
                assert client.provider == "openrouter"


# ============================================================================
# Focused Deduplication Verification Tests (Cases A through E)
# ============================================================================


class TestDeduplicationVerification:
    """Verifies Cases A through E from the Task 1 specification."""

    @pytest.mark.asyncio
    async def test_case_a_differently_worded_phone_login_deduplicated(self):
        """Case A: Two differently worded questions about phone login are deduplicated."""
        participants = [
            {"participant_id": "p1", "interpretation": "Finish email and password login."},
            {"participant_id": "p2", "interpretation": "Finish email or phone login for launch."},
        ]
        task = {"title": "Auth setup"}

        response_data = {
            "summary": "Comparing auth methods.",
            "issues": [
                {
                    "type": "scope_difference",
                    "title": "Phone login scope",
                    "description": "Participant 2 expects phone login in launch.",
                    "evidence": [
                        {"participant_id": "p1", "quote": "Finish email and password login."},
                        {"participant_id": "p2", "quote": "Finish email or phone login for launch."},
                    ],
                    "impact": "Auth scope divergence.",
                    "priority": "high",
                    "confidence": 0.9,
                    "clarification_question": "Should phone login be supported in addition to email login?",
                },
                {
                    "type": "scope_difference",
                    "title": "Phone authentication requirement",
                    "description": "Different expectations on phone authentication.",
                    "evidence": [
                        {"participant_id": "p1", "quote": "Finish email and password login."},
                        {"participant_id": "p2", "quote": "Finish email or phone login for launch."},
                    ],
                    "impact": "Auth scope divergence.",
                    "priority": "high",
                    "confidence": 0.85,
                    "clarification_question": "Is phone authentication required for launch?",
                },
            ],
            "complementary_perspectives": [],
        }

        mock_client = make_mock_client(return_data=response_data)
        result = await analyze_interpretations(task, participants, client=mock_client)

        assert result["status"] == AnalysisStatus.COMPLETED
        # Must be deduplicated down to 1 distinct issue
        assert len(result["issues"]) == 1
        assert result["issues"][0]["title"] == "Phone login scope"
        assert result["metadata"]["deduplicated_issue_count"] == 1

    @pytest.mark.asyncio
    async def test_case_b_phone_login_and_password_recovery_remain_separate(self):
        """Case B: Phone login and password recovery remain separate decisions."""
        participants = [
            {"participant_id": "p1", "interpretation": "Finish email and password login."},
            {"participant_id": "p2", "interpretation": "Finish email or phone login, and password recovery."},
        ]
        task = {"title": "Auth setup"}

        response_data = {
            "summary": "Two distinct scope questions identified.",
            "issues": [
                {
                    "type": "scope_difference",
                    "title": "Phone login scope",
                    "description": "Participant 2 expects phone login.",
                    "evidence": [
                        {"participant_id": "p1", "quote": "Finish email and password login."},
                        {"participant_id": "p2", "quote": "Finish email or phone login"},
                    ],
                    "impact": "Auth scope divergence.",
                    "priority": "high",
                    "confidence": 0.9,
                    "clarification_question": "Should phone login be supported in addition to email login?",
                },
                {
                    "type": "scope_difference",
                    "title": "Password recovery scope",
                    "description": "Participant 2 expects password recovery.",
                    "evidence": [
                        {"participant_id": "p1", "quote": "Finish email and password login."},
                        {"participant_id": "p2", "quote": "and password recovery."},
                    ],
                    "impact": "Secondary feature scope divergence.",
                    "priority": "medium",
                    "confidence": 0.85,
                    "clarification_question": "Should password recovery be included in the launch milestone?",
                },
            ],
            "complementary_perspectives": [],
        }

        mock_client = make_mock_client(return_data=response_data)
        result = await analyze_interpretations(task, participants, client=mock_client)

        assert result["status"] == AnalysisStatus.COMPLETED
        assert len(result["issues"]) == 2
        titles = {i["title"] for i in result["issues"]}
        assert "Phone login scope" in titles
        assert "Password recovery scope" in titles
        assert result["metadata"]["deduplicated_issue_count"] == 0

    @pytest.mark.asyncio
    async def test_case_c_registration_and_password_recovery_remain_separate(self):
        """Case C: Registration and password recovery remain separate decisions when they require independent scope decisions."""
        participants = [
            {"participant_id": "p1", "interpretation": "Complete email login."},
            {"participant_id": "p2", "interpretation": "Complete email login, user registration, and password recovery."},
        ]
        task = {"title": "Auth setup"}

        response_data = {
            "summary": "Registration and password recovery analyzed.",
            "issues": [
                {
                    "type": "scope_difference",
                    "title": "User registration scope",
                    "description": "Participant 2 expects self-service registration.",
                    "evidence": [
                        {"participant_id": "p1", "quote": "Complete email login."},
                        {"participant_id": "p2", "quote": "user registration"},
                    ],
                    "impact": "Onboarding scope divergence.",
                    "priority": "medium",
                    "confidence": 0.85,
                    "clarification_question": "Should user registration be part of the launch release?",
                },
                {
                    "type": "scope_difference",
                    "title": "Password recovery scope",
                    "description": "Participant 2 expects password recovery.",
                    "evidence": [
                        {"participant_id": "p1", "quote": "Complete email login."},
                        {"participant_id": "p2", "quote": "password recovery."},
                    ],
                    "impact": "Account recovery scope divergence.",
                    "priority": "medium",
                    "confidence": 0.85,
                    "clarification_question": "Should password recovery be included in the launch milestone?",
                },
            ],
            "complementary_perspectives": [],
        }

        mock_client = make_mock_client(return_data=response_data)
        result = await analyze_interpretations(task, participants, client=mock_client)

        assert result["status"] == AnalysisStatus.COMPLETED
        assert len(result["issues"]) == 2
        titles = {i["title"] for i in result["issues"]}
        assert "User registration scope" in titles
        assert "Password recovery scope" in titles
        assert result["metadata"]["deduplicated_issue_count"] == 0

    @pytest.mark.asyncio
    async def test_case_d_generic_umbrella_does_not_hide_specific_findings(self):
        """Case D: A generic umbrella issue does not hide more specific findings (regardless of order)."""
        participants = [
            {"participant_id": "p1", "interpretation": "Finish email and password login."},
            {"participant_id": "p2", "interpretation": "Finish email or phone login, and password recovery."},
        ]
        task = {"title": "Auth setup"}

        umbrella_issue = {
            "type": "scope_difference",
            "title": "Authentication features differ overall",
            "description": "General differences in auth features.",
            "evidence": [
                {"participant_id": "p1", "quote": "Finish email and password login."},
                {"participant_id": "p2", "quote": "Finish email or phone login"},
            ],
            "impact": "Auth mismatch",
            "priority": "high",
            "confidence": 0.8,
            "clarification_question": "What authentication features should be included for the launch?",
        }
        phone_issue = {
            "type": "scope_difference",
            "title": "Phone login scope",
            "description": "Participant 2 expects phone login.",
            "evidence": [
                {"participant_id": "p1", "quote": "Finish email and password login."},
                {"participant_id": "p2", "quote": "Finish email or phone login"},
            ],
            "impact": "Auth scope divergence.",
            "priority": "high",
            "confidence": 0.9,
            "clarification_question": "Should phone login be supported in addition to email login?",
        }
        pw_issue = {
            "type": "scope_difference",
            "title": "Password recovery scope",
            "description": "Participant 2 expects password recovery.",
            "evidence": [
                {"participant_id": "p1", "quote": "Finish email and password login."},
                {"participant_id": "p2", "quote": "and password recovery."},
            ],
            "impact": "Recovery divergence.",
            "priority": "medium",
            "confidence": 0.85,
            "clarification_question": "Should password recovery be included in the launch milestone?",
        }

        # Subtest 1: Umbrella placed FIRST
        response_umbrella_first = {
            "summary": "Umbrella first test.",
            "issues": [umbrella_issue, phone_issue, pw_issue],
            "complementary_perspectives": [],
        }
        client1 = make_mock_client(return_data=response_umbrella_first)
        result1 = await analyze_interpretations(task, participants, client=client1)
        assert result1["status"] == AnalysisStatus.COMPLETED
        assert len(result1["issues"]) == 2
        titles1 = [i["title"] for i in result1["issues"]]
        assert "Phone login scope" in titles1
        assert "Password recovery scope" in titles1
        assert "Authentication features differ overall" not in titles1

        # Subtest 2: Umbrella placed LAST
        response_umbrella_last = {
            "summary": "Umbrella last test.",
            "issues": [phone_issue, pw_issue, umbrella_issue],
            "complementary_perspectives": [],
        }
        client2 = make_mock_client(return_data=response_umbrella_last)
        result2 = await analyze_interpretations(task, participants, client=client2)
        assert result2["status"] == AnalysisStatus.COMPLETED
        assert len(result2["issues"]) == 2
        titles2 = [i["title"] for i in result2["issues"]]
        assert "Phone login scope" in titles2
        assert "Password recovery scope" in titles2
        assert "Authentication features differ overall" not in titles2

    @pytest.mark.asyncio
    async def test_case_e_shared_evidence_retained_for_different_decisions(self):
        """Case E: Findings with shared evidence are retained when they represent genuinely different decisions."""
        participants = [
            {"participant_id": "p1", "interpretation": "Finish email and password login."},
            {"participant_id": "p2", "interpretation": "Finish email or phone login, registration, and password recovery."},
        ]
        task = {"title": "Auth setup"}

        # All 3 issues cite the exact same excerpt from Participant 2
        shared_quote = "Finish email or phone login, registration, and password recovery."
        response_data = {
            "summary": "Three distinct decisions sharing one participant response.",
            "issues": [
                {
                    "type": "scope_difference",
                    "title": "Phone login scope",
                    "description": "Login methods differ.",
                    "evidence": [
                        {"participant_id": "p1", "quote": "Finish email and password login."},
                        {"participant_id": "p2", "quote": shared_quote},
                    ],
                    "impact": "Auth divergence.",
                    "priority": "high",
                    "confidence": 0.9,
                    "clarification_question": "Should phone login be supported in addition to email login?",
                },
                {
                    "type": "scope_difference",
                    "title": "User registration scope",
                    "description": "Registration expected by p2 only.",
                    "evidence": [
                        {"participant_id": "p1", "quote": "Finish email and password login."},
                        {"participant_id": "p2", "quote": shared_quote},
                    ],
                    "impact": "Onboarding divergence.",
                    "priority": "medium",
                    "confidence": 0.85,
                    "clarification_question": "Should user registration be part of the launch release?",
                },
                {
                    "type": "scope_difference",
                    "title": "Password recovery scope",
                    "description": "Recovery expected by p2 only.",
                    "evidence": [
                        {"participant_id": "p1", "quote": "Finish email and password login."},
                        {"participant_id": "p2", "quote": shared_quote},
                    ],
                    "impact": "Account recovery divergence.",
                    "priority": "medium",
                    "confidence": 0.85,
                    "clarification_question": "Should password recovery be included in the launch milestone?",
                },
            ],
            "complementary_perspectives": [],
        }

        mock_client = make_mock_client(return_data=response_data)
        result = await analyze_interpretations(task, participants, client=mock_client)

        assert result["status"] == AnalysisStatus.COMPLETED
        # All 3 must be retained because they address distinct decisions
        assert len(result["issues"]) == 3
        titles = {i["title"] for i in result["issues"]}
        assert "Phone login scope" in titles
        assert "User registration scope" in titles
        assert "Password recovery scope" in titles
        assert result["metadata"]["deduplicated_issue_count"] == 0


