"""Integration tests for MISUNDERSTOOD backend API, lifecycle, and AI persistence.

Completely offline test suite using mocked AI responses.
Zero network access or live API credentials required.
"""

from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models import AnalysisModel, IssueModel, SessionModel


# ============================================================================
# Test Database & Client Fixtures
# ============================================================================


@pytest.fixture
def db_session():
    """Create an isolated in-memory SQLite database for each test function."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    """FastAPI TestClient with overridden get_db dependency."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


# ============================================================================
# Mock Data Fixtures
# ============================================================================

MOCK_SUCCESSFUL_AI_RESULT = {
    "status": "completed",
    "summary": "Participants agree on core authentication, but disagree on whether phone login is in scope.",
    "issues": [
        {
            "type": "scope_difference",
            "title": "Scope of Authentication Functionality",
            "description": "Participant A expects email only; Participant B expects phone login.",
            "evidence": [
                {
                    "participant_id": "participant-a",
                    "quote": "Finish email and password login.",
                    "source_field": "interpretation",
                },
                {
                    "participant_id": "participant-b",
                    "quote": "Finish email or phone login",
                    "source_field": "interpretation",
                },
            ],
            "impact": "Auth scope divergence.",
            "priority": "high",
            "confidence": 0.95,
            "clarification_question": "Should phone login be supported in addition to email login?",
        }
    ],
    "complementary_perspectives": [
        {
            "title": "Security Considerations",
            "description": "Both participants prioritize secure credentials.",
            "evidence": [
                {
                    "participant_id": "participant-a",
                    "quote": "password login",
                    "source_field": "interpretation",
                }
            ],
        }
    ],
    "issue_counts": {
        "total": 1,
        "by_type": {"scope_difference": 1},
        "by_priority": {"high": 1},
    },
    "error_message": None,
    "metadata": {
        "provider": "mock-provider",
        "model": "mock-model",
        "participant_count": 2,
        "unverified_quotes_dropped": 0,
        "rejected_issue_count": 0,
        "deduplicated_issue_count": 0,
    },
}


# ============================================================================
# Test Cases
# ============================================================================


class TestBackendIntegration:
    """End-to-end integration tests for session lifecycle, AI execution, and persistence."""

    def test_health_check(self, client):
        """Verify API health check endpoint."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app"] == "MISUNDERSTOOD"

    def test_create_and_get_session(self, client):
        """Verify creating a session and retrieving it by ID."""
        create_res = client.post(
            "/api/sessions",
            json={
                "title": "Prepare the application for launch",
                "description": "Essential auth functionality for launch release.",
            },
        )
        assert create_res.status_code == 201
        session_data = create_res.json()
        assert "id" in session_data
        assert "session_code" in session_data
        assert session_data["title"] == "Prepare the application for launch"
        assert session_data["status"] == "collecting"
        assert session_data["participant_count"] == 0

        session_id = session_data["id"]
        get_res = client.get(f"/api/sessions/{session_id}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == session_id

    def test_get_session_not_found(self, client):
        """Verify 404 response for non-existent session ID."""
        response = client.get("/api/sessions/non-existent-uuid-12345")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_submit_participant_interpretations(self, client):
        """Verify adding participants and updating their responses."""
        # 1. Create session
        session_res = client.post(
            "/api/sessions",
            json={"title": "Prepare launch"},
        )
        session_id = session_res.json()["id"]

        # 2. Add Participant A
        p1_res = client.post(
            f"/api/sessions/{session_id}/participants",
            json={
                "participant_id": "participant-a",
                "name": "Alice",
                "interpretation": "Finish email and password login.",
                "assumptions": "Postgres database will be used.",
            },
        )
        assert p1_res.status_code == 201
        assert p1_res.json()["participant_id"] == "participant-a"

        # 3. Add Participant B
        p2_res = client.post(
            f"/api/sessions/{session_id}/participants",
            json={
                "participant_id": "participant-b",
                "name": "Bob",
                "interpretation": "Finish email or phone login, registration, and password recovery.",
            },
        )
        assert p2_res.status_code == 201

        # 4. Verify participant count updated on session
        session_get = client.get(f"/api/sessions/{session_id}")
        assert session_get.json()["participant_count"] == 2

        # 5. Verify update to existing participant
        p1_update = client.post(
            f"/api/sessions/{session_id}/participants",
            json={
                "participant_id": "participant-a",
                "name": "Alice M.",
                "interpretation": "Finish email and password login with MFA.",
            },
        )
        assert p1_update.status_code == 201
        assert p1_update.json()["name"] == "Alice M."
        # Count should still be 2
        assert client.get(f"/api/sessions/{session_id}").json()["participant_count"] == 2

    def test_premature_analysis_rejected_with_insufficient_participants(self, client):
        """Verify analysis is rejected if fewer than 2 participants have submitted."""
        session_res = client.post(
            "/api/sessions",
            json={"title": "Prepare launch"},
        )
        session_id = session_res.json()["id"]

        # Attempt with 0 participants
        res_zero = client.post(f"/api/sessions/{session_id}/analyze")
        assert res_zero.status_code == 400
        assert "at least 2 participant submissions" in res_zero.json()["detail"].lower()

        # Add 1 participant and attempt again
        client.post(
            f"/api/sessions/{session_id}/participants",
            json={
                "participant_id": "participant-a",
                "interpretation": "Finish email login.",
            },
        )
        res_one = client.post(f"/api/sessions/{session_id}/analyze")
        assert res_one.status_code == 400
        assert "at least 2 participant submissions" in res_one.json()["detail"].lower()

    @patch("backend.app.services.analysis_service.analyze_interpretations", new_callable=AsyncMock)
    def test_successful_analysis_and_persistence(self, mock_ai, client, db_session):
        """Verify successful analysis run, DB persistence, and exact response structure."""
        mock_ai.return_value = MOCK_SUCCESSFUL_AI_RESULT

        # 1. Create session and add 2 participants
        session_res = client.post(
            "/api/sessions",
            json={"title": "Prepare launch", "description": "Auth launch scope."},
        )
        session_id = session_res.json()["id"]

        client.post(
            f"/api/sessions/{session_id}/participants",
            json={
                "participant_id": "participant-a",
                "interpretation": "Finish email and password login.",
                "assumptions": "Postgres DB.",
            },
        )
        client.post(
            f"/api/sessions/{session_id}/participants",
            json={
                "participant_id": "participant-b",
                "interpretation": "Finish email or phone login.",
            },
        )

        # 2. Trigger analysis
        analyze_res = client.post(f"/api/sessions/{session_id}/analyze")
        assert analyze_res.status_code == 200
        data = analyze_res.json()

        assert data["status"] == "completed"
        assert data["session_id"] == session_id
        assert data["analysis_id"] is not None
        assert len(data["issues"]) == 1
        assert data["issues"][0]["title"] == "Scope of Authentication Functionality"
        assert data["issues"][0]["resolution_status"] == "open"
        assert data["issues"][0]["evidence"][0]["participant_id"] == "participant-a"

        # 3. Verify mock received exact inputs built strictly from persisted records
        mock_ai.assert_called_once()
        call_kwargs = mock_ai.call_args.kwargs
        assert call_kwargs["task"]["title"] == "Prepare launch"
        assert call_kwargs["task"]["description"] == "Auth launch scope."
        assert len(call_kwargs["participants"]) == 2
        assert call_kwargs["participants"][0]["participant_id"] == "participant-a"
        assert call_kwargs["participants"][0]["interpretation"] == "Finish email and password login."
        assert call_kwargs["participants"][0]["assumptions"] == "Postgres DB."

        # 4. Verify DB records
        db_session.expire_all()
        session_record = db_session.query(SessionModel).filter_by(id=session_id).first()
        assert session_record.status == "completed"

        analysis_record = db_session.query(AnalysisModel).filter_by(session_id=session_id).first()
        assert analysis_record is not None
        assert analysis_record.status == "completed"

        issue_record = db_session.query(IssueModel).filter_by(session_id=session_id).first()
        assert issue_record is not None
        assert issue_record.title == "Scope of Authentication Functionality"
        assert issue_record.resolution_status == "open"

    @patch("backend.app.services.analysis_service.analyze_interpretations", new_callable=AsyncMock)
    def test_get_and_patch_issues_endpoints(self, mock_ai, client):
        """Verify retrieving issues and updating resolution status."""
        mock_ai.return_value = MOCK_SUCCESSFUL_AI_RESULT

        # Setup session and run analysis
        s_res = client.post("/api/sessions", json={"title": "Prepare launch"})
        s_id = s_res.json()["id"]
        client.post(f"/api/sessions/{s_id}/participants", json={"participant_id": "p1", "interpretation": "Login"})
        client.post(f"/api/sessions/{s_id}/participants", json={"participant_id": "p2", "interpretation": "Login & recovery"})
        client.post(f"/api/sessions/{s_id}/analyze")

        # 1. GET /api/sessions/{session_id}/issues
        issues_res = client.get(f"/api/sessions/{s_id}/issues")
        assert issues_res.status_code == 200
        issues = issues_res.json()
        assert len(issues) == 1
        issue_id = issues[0]["id"]
        assert issues[0]["resolution_status"] == "open"

        # 2. PATCH /api/sessions/{session_id}/issues/{issue_id} -> resolve issue
        patch_res = client.patch(
            f"/api/sessions/{s_id}/issues/{issue_id}",
            json={
                "resolution_status": "resolved",
                "resolution_notes": "Team agreed to defer phone login to Milestone 2.",
            },
        )
        assert patch_res.status_code == 200
        updated = patch_res.json()
        assert updated["resolution_status"] == "resolved"
        assert updated["resolution_notes"] == "Team agreed to defer phone login to Milestone 2."

        # 3. GET /api/sessions/{session_id}/issues?resolution_status=resolved
        filtered_res = client.get(f"/api/sessions/{s_id}/issues?resolution_status=resolved")
        assert len(filtered_res.json()) == 1

        filtered_open = client.get(f"/api/sessions/{s_id}/issues?resolution_status=open")
        assert len(filtered_open.json()) == 0

    @patch("backend.app.services.analysis_service.analyze_interpretations", new_callable=AsyncMock)
    def test_repeated_analysis_preserves_resolution_and_avoids_duplicate_issues(self, mock_ai, client, db_session):
        """Verify re-running analysis preserves human resolution ('resolved') and does not create duplicate issues."""
        mock_ai.return_value = MOCK_SUCCESSFUL_AI_RESULT

        # 1. Setup session and run initial analysis
        s_res = client.post("/api/sessions", json={"title": "Prepare launch"})
        s_id = s_res.json()["id"]
        client.post(f"/api/sessions/{s_id}/participants", json={"participant_id": "p1", "interpretation": "Login"})
        client.post(f"/api/sessions/{s_id}/participants", json={"participant_id": "p2", "interpretation": "Login & recovery"})
        client.post(f"/api/sessions/{s_id}/analyze")

        # 2. Mark issue as "resolved"
        issues = client.get(f"/api/sessions/{s_id}/issues").json()
        issue_id = issues[0]["id"]
        client.patch(
            f"/api/sessions/{s_id}/issues/{issue_id}",
            json={
                "resolution_status": "resolved",
                "resolution_notes": "Agreed by team in standup.",
            },
        )

        # 3. Re-run analysis (simulate a second participant adding text or re-analysis trigger)
        rerun_res = client.post(f"/api/sessions/{s_id}/analyze")
        assert rerun_res.status_code == 200

        # 4. Verify no duplicate issues were created
        db_session.expire_all()
        db_issues = db_session.query(IssueModel).filter_by(session_id=s_id).all()
        assert len(db_issues) == 1, "Re-running analysis must not create duplicate issues"

        # 5. Verify the human resolution status was preserved
        assert db_issues[0].resolution_status == "resolved"
        assert db_issues[0].resolution_notes == "Agreed by team in standup."

    def test_concurrent_analysis_rejected_with_conflict(self, client, db_session):
        """Verify concurrent requests return 409 Conflict when session status is analyzing."""
        # 1. Create session with 2 participants
        s_res = client.post("/api/sessions", json={"title": "Prepare launch"})
        s_id = s_res.json()["id"]
        client.post(f"/api/sessions/{s_id}/participants", json={"participant_id": "p1", "interpretation": "Login"})
        client.post(f"/api/sessions/{s_id}/participants", json={"participant_id": "p2", "interpretation": "Login"})

        # 2. Manually transition session to "analyzing" state to simulate ongoing background run
        session_record = db_session.query(SessionModel).filter_by(id=s_id).first()
        session_record.status = "analyzing"
        db_session.commit()

        # 3. Attempt concurrent analysis
        conflict_res = client.post(f"/api/sessions/{s_id}/analyze")
        assert conflict_res.status_code == 409
        assert "already in progress" in conflict_res.json()["detail"].lower()

    @patch("backend.app.services.analysis_service.analyze_interpretations", new_callable=AsyncMock)
    def test_provider_failure_sets_failed_status_and_returns_502(self, mock_ai, client, db_session):
        """Verify provider failure returns HTTP 502, sets session to failed, and never masks as consensus."""
        mock_ai.return_value = {
            "status": "failed",
            "summary": "AI provider failed to complete analysis.",
            "error_message": "Gemini quota or credit limit reached (HTTP 429).",
            "issues": [],
            "complementary_perspectives": [],
            "issue_counts": {"total": 0, "by_type": {}, "by_priority": {}},
            "metadata": {"provider": "gemini"},
        }

        # 1. Setup session with 2 participants
        s_res = client.post("/api/sessions", json={"title": "Prepare launch"})
        s_id = s_res.json()["id"]
        client.post(f"/api/sessions/{s_id}/participants", json={"participant_id": "p1", "interpretation": "Login"})
        client.post(f"/api/sessions/{s_id}/participants", json={"participant_id": "p2", "interpretation": "Login"})

        # 2. Trigger analysis
        fail_res = client.post(f"/api/sessions/{s_id}/analyze")
        assert fail_res.status_code == 502
        assert "quota or credit limit reached" in fail_res.json()["detail"]

        # 3. Verify session status is failed, NOT completed or consensus
        db_session.expire_all()
        session_record = db_session.query(SessionModel).filter_by(id=s_id).first()
        assert session_record.status == "failed"

        # 4. Verify failed analysis record was persisted
        failed_analysis = db_session.query(AnalysisModel).filter_by(session_id=s_id).first()
        assert failed_analysis is not None
        assert failed_analysis.status == "failed"
        assert "quota" in failed_analysis.error_message

    def test_secrets_and_api_keys_never_leaked_in_responses(self, client):
        """Verify API error messages and health checks never leak API key tokens."""
        res_404 = client.get("/api/sessions/unknown-id")
        err_text = res_404.text
        assert "sk-" not in err_text
        assert "AQ." not in err_text

        res_health = client.get("/api/health")
        health_text = res_health.text
        assert "sk-" not in health_text
        assert "AQ." not in health_text

    @patch("backend.app.services.analysis_service.analyze_interpretations", new_callable=AsyncMock)
    def test_agreement_compilation_and_confirmation_workflow(self, mock_ai, client):
        """Verify full agreement compilation and multi-party confirmation workflow."""
        mock_ai.return_value = MOCK_SUCCESSFUL_AI_RESULT

        # 1. Setup session and analyze
        s_res = client.post("/api/sessions", json={"title": "Launch App", "description": "Finish auth"})
        s_id = s_res.json()["id"]
        client.post(f"/api/sessions/{s_id}/participants", json={"participant_id": "p1", "interpretation": "Login"})
        client.post(f"/api/sessions/{s_id}/participants", json={"participant_id": "p2", "interpretation": "Login & recovery"})
        client.post(f"/api/sessions/{s_id}/analyze")

        # Resolve issue
        issues = client.get(f"/api/sessions/{s_id}/issues").json()
        iss_id = issues[0]["id"]
        client.patch(
            f"/api/sessions/{s_id}/issues/{iss_id}",
            json={"resolution_status": "resolved", "resolution_notes": "Email login only for v1."},
        )

        # 2. Get agreement
        ag_res = client.get(f"/api/sessions/{s_id}/agreement")
        assert ag_res.status_code == 200
        ag_data = ag_res.json()
        assert any("Launch App" in item for item in ag_data["items"])
        assert any("Scope of Authentication Functionality" in item for item in ag_data["items"])
        assert ag_data["is_fully_confirmed"] is False

        # 3. Participant 1 confirms
        conf1 = client.post(
            f"/api/sessions/{s_id}/agreement/confirm",
            json={"participant_id": "p1"},
        )
        assert conf1.status_code == 200
        assert conf1.json()["confirmed_by"] == ["p1"]
        assert conf1.json()["is_fully_confirmed"] is False

        # 4. Participant 2 confirms -> becomes fully confirmed
        conf2 = client.post(
            f"/api/sessions/{s_id}/agreement/confirm",
            json={"participant_id": "p2"},
        )
        assert conf2.status_code == 200
        assert set(conf2.json()["confirmed_by"]) == {"p1", "p2"}
        assert conf2.json()["is_fully_confirmed"] is True

    @patch("backend.app.services.analysis_service.analyze_interpretations", new_callable=AsyncMock)
    def test_bridge_test_metrics_calculation(self, mock_ai, client):
        """Verify before vs after Bridge Test metrics calculation."""
        mock_ai.return_value = MOCK_SUCCESSFUL_AI_RESULT

        s_res = client.post("/api/sessions", json={"title": "Launch App"})
        s_id = s_res.json()["id"]
        client.post(f"/api/sessions/{s_id}/participants", json={"participant_id": "p1", "interpretation": "Login"})
        client.post(f"/api/sessions/{s_id}/participants", json={"participant_id": "p2", "interpretation": "Login & recovery"})
        client.post(f"/api/sessions/{s_id}/analyze")

        # Before resolving: 1 initial, 0 resolved, 1 open -> unresolved
        bt1 = client.get(f"/api/sessions/{s_id}/bridge-test").json()
        assert bt1["initial_issues_count"] == 1
        assert bt1["resolved_count"] == 0
        assert bt1["open_count"] == 1
        assert bt1["resolution_percentage"] == 0.0
        assert bt1["bridge_status"] == "unresolved"
        assert "disclaimer" in bt1

        # Resolve issue
        issues = client.get(f"/api/sessions/{s_id}/issues").json()
        client.patch(
            f"/api/sessions/{s_id}/issues/{issues[0]['id']}",
            json={"resolution_status": "resolved", "resolution_notes": "Agreed."},
        )

        # Confirm agreement by both participants
        client.post(f"/api/sessions/{s_id}/agreement/confirm", json={"participant_id": "p1"})
        client.post(f"/api/sessions/{s_id}/agreement/confirm", json={"participant_id": "p2"})

        # After resolving and confirming: 1 initial, 1 resolved, 0 open -> bridged
        bt2 = client.get(f"/api/sessions/{s_id}/bridge-test").json()
        assert bt2["initial_issues_count"] == 1
        assert bt2["resolved_count"] == 1
        assert bt2["open_count"] == 0
        assert bt2["resolution_percentage"] == 100.0
        assert bt2["is_fully_confirmed"] is True
        assert bt2["bridge_status"] == "bridged"

    @patch("backend.app.services.analysis_service.analyze_interpretations", new_callable=AsyncMock)
    def test_dismissed_issues_appear_in_excluded_items_and_bridge_metrics(self, mock_ai, client):
        """Verify dismissed issues are categorized as out-of-scope and counted in Bridge Test."""
        mock_ai.return_value = MOCK_SUCCESSFUL_AI_RESULT

        s_res = client.post("/api/sessions", json={"title": "Launch App"})
        s_id = s_res.json()["id"]
        client.post(f"/api/sessions/{s_id}/participants", json={"participant_id": "p1", "interpretation": "Login"})
        client.post(f"/api/sessions/{s_id}/participants", json={"participant_id": "p2", "interpretation": "Login & recovery"})
        client.post(f"/api/sessions/{s_id}/analyze")

        issues = client.get(f"/api/sessions/{s_id}/issues").json()
        client.patch(
            f"/api/sessions/{s_id}/issues/{issues[0]['id']}",
            json={"resolution_status": "dismissed", "resolution_notes": "Not applicable to this phase."},
        )

        ag = client.get(f"/api/sessions/{s_id}/agreement").json()
        assert len(ag["excluded_items"]) == 1
        assert "Excluded / Out of Scope: Scope of Authentication Functionality" in ag["excluded_items"][0]

        bt = client.get(f"/api/sessions/{s_id}/bridge-test").json()
        assert bt["dismissed_count"] == 1
        assert bt["open_count"] == 0
        assert bt["resolution_percentage"] == 100.0

    @patch("backend.app.services.analysis_service.analyze_interpretations", new_callable=AsyncMock)
    def test_browser_refresh_simulation_after_persistence(self, mock_ai, client):
        """Verify browser reload recovers persisted session, issues, agreement, and metrics."""
        mock_ai.return_value = MOCK_SUCCESSFUL_AI_RESULT

        # 1. Complete flow
        s_res = client.post("/api/sessions", json={"title": "Launch App", "description": "Goal"})
        s_id = s_res.json()["id"]
        client.post(f"/api/sessions/{s_id}/participants", json={"participant_id": "p1", "interpretation": "Login"})
        client.post(f"/api/sessions/{s_id}/participants", json={"participant_id": "p2", "interpretation": "Login & recovery"})
        client.post(f"/api/sessions/{s_id}/analyze")

        issues = client.get(f"/api/sessions/{s_id}/issues").json()
        client.patch(
            f"/api/sessions/{s_id}/issues/{issues[0]['id']}",
            json={"resolution_status": "resolved", "resolution_notes": "Done."},
        )
        client.post(f"/api/sessions/{s_id}/agreement/confirm", json={"participant_id": "p1"})
        client.post(f"/api/sessions/{s_id}/agreement/confirm", json={"participant_id": "p2"})

        # 2. Simulate browser refresh by querying fresh GET endpoints
        session_fresh = client.get(f"/api/sessions/{s_id}").json()
        assert session_fresh["status"] == "completed"
        assert session_fresh["participant_count"] == 2

        issues_fresh = client.get(f"/api/sessions/{s_id}/issues").json()
        assert len(issues_fresh) == 1
        assert issues_fresh[0]["resolution_status"] == "resolved"

        agreement_fresh = client.get(f"/api/sessions/{s_id}/agreement").json()
        assert agreement_fresh["is_fully_confirmed"] is True

        bridge_fresh = client.get(f"/api/sessions/{s_id}/bridge-test").json()
        assert bridge_fresh["bridge_status"] == "bridged"
        assert bridge_fresh["resolution_percentage"] == 100.0

    @patch("backend.app.services.analysis_service.analyze_interpretations", new_callable=AsyncMock)
    def test_resolved_issue_disappearing_from_later_analysis_is_preserved(self, mock_ai, client, db_session):
        """Verify an issue resolved by the team is NOT deleted if a later re-analysis drops it."""
        # Run 1: Returns a scope difference issue
        mock_ai.return_value = MOCK_SUCCESSFUL_AI_RESULT
        s_res = client.post("/api/sessions", json={"title": "Launch App"})
        s_id = s_res.json()["id"]
        client.post(f"/api/sessions/{s_id}/participants", json={"participant_id": "p1", "interpretation": "Login"})
        client.post(f"/api/sessions/{s_id}/participants", json={"participant_id": "p2", "interpretation": "Login & recovery"})
        client.post(f"/api/sessions/{s_id}/analyze")

        issues = client.get(f"/api/sessions/{s_id}/issues").json()
        client.patch(
            f"/api/sessions/{s_id}/issues/{issues[0]['id']}",
            json={"resolution_status": "resolved", "resolution_notes": "Team decided to keep recovery."},
        )

        # Run 2: Model returns 0 issues (the issue disappeared from AI output)
        mock_ai.return_value = {
            "status": "completed",
            "summary": "No issues detected in updated run.",
            "issues": [],
            "complementary_perspectives": [],
            "issue_counts": {"total": 0, "by_type": {}, "by_priority": {}},
            "metadata": {"model": "mock"},
        }
        client.post(f"/api/sessions/{s_id}/analyze")

        # The previously resolved issue must STILL exist in the database!
        db_session.expire_all()
        db_issues = db_session.query(IssueModel).filter_by(session_id=s_id).all()
        assert len(db_issues) == 1
        assert db_issues[0].resolution_status == "resolved"
        assert db_issues[0].resolution_notes == "Team decided to keep recovery."

    @patch("backend.app.services.analysis_service.analyze_interpretations", new_callable=AsyncMock)
    def test_clean_consensus_zero_issues_flow(self, mock_ai, client):
        """Verify workflow when participants are in complete agreement (0 issues detected)."""
        mock_ai.return_value = {
            "status": "completed",
            "summary": "Full consensus observed across both participants.",
            "issues": [],
            "complementary_perspectives": [
                {
                    "title": "Aligned Deliverables",
                    "description": "Both participants expect email login.",
                    "evidence": [{"participant_id": "p1", "quote": "Login", "source_field": "interpretation"}],
                }
            ],
            "issue_counts": {"total": 0, "by_type": {}, "by_priority": {}},
            "metadata": {"model": "mock"},
        }

        s_res = client.post("/api/sessions", json={"title": "Launch App"})
        s_id = s_res.json()["id"]
        client.post(f"/api/sessions/{s_id}/participants", json={"participant_id": "p1", "interpretation": "Login"})
        client.post(f"/api/sessions/{s_id}/participants", json={"participant_id": "p2", "interpretation": "Login"})
        res = client.post(f"/api/sessions/{s_id}/analyze")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "completed"
        assert len(data["issues"]) == 0

        # Bridge test metrics
        bt = client.get(f"/api/sessions/{s_id}/bridge-test").json()
        assert bt["initial_issues_count"] == 0
        assert bt["open_count"] == 0
        assert bt["resolution_percentage"] == 100.0


