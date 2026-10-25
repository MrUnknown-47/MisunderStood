"""Phase 1 Backend Verification: Session Joining, Participant Identity, and Server-Side Privacy.

Completely offline test suite using mocked database and FastAPI test client.
Zero live LLM calls or network dependencies.
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app


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


class TestSessionJoiningAndIdentity:
    """Tests for join-code generation, token issuance, authentication, and cross-session security."""

    def test_create_session_issues_join_code_and_creator_credential(self, client):
        """Verify session creation issues a human-friendly GAP- code and creator bearer token."""
        payload = {
            "title": "Launch Mobile App",
            "description": "Essential auth functionality for mobile release.",
            "creator_name": "Project Lead",
            "min_participants": 2,
        }
        res = client.post("/api/sessions", json=payload)
        assert res.status_code == status.HTTP_201_CREATED
        data = res.json()

        assert "id" in data
        assert "join_code" in data
        assert data["join_code"].startswith("GAP-")
        assert len(data["join_code"]) == 10  # GAP- + 6 chars
        assert data["status"] == "collecting_responses"
        assert "creator_participant_id" in data
        assert data["creator_participant_id"] is not None
        assert "participant_token" in data
        assert data["participant_token"].startswith("mst_sec_")

    def test_join_session_with_valid_code(self, client):
        """Verify participant can join using join code and receives valid credential."""
        create_res = client.post(
            "/api/sessions",
            json={
                "title": "Payment Gateway Integration",
                "description": "Integrate Stripe and PayPal.",
                "creator_name": "Tech Lead",
            },
        ).json()

        join_code = create_res["join_code"]
        session_id = create_res["id"]

        join_res = client.post(
            "/api/sessions/join",
            json={
                "join_code": join_code.lower(),  # Test case-insensitivity
                "display_name": "Frontend Dev",
            },
        )
        assert join_res.status_code == status.HTTP_200_OK
        join_data = join_res.json()

        assert join_data["session_id"] == session_id
        assert "participant_id" in join_data
        assert join_data["display_name"] == "Frontend Dev"
        assert join_data["participant_token"].startswith("mst_sec_")

    def test_join_session_with_invalid_code_returns_404(self, client):
        """Verify joining with an unknown join code returns HTTP 404."""
        res = client.post(
            "/api/sessions/join",
            json={"join_code": "GAP-INVALID", "display_name": "Intruder"},
        )
        assert res.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in res.json()["detail"].lower()

    def test_authenticated_access_with_valid_token(self, client):
        """Verify protected session status endpoint accepts valid bearer token."""
        s = client.post(
            "/api/sessions",
            json={"title": "Cloud Migration", "creator_name": "DevOps"},
        ).json()

        headers = {"Authorization": f"Bearer {s['participant_token']}"}
        res = client.get(f"/api/sessions/{s['id']}/status", headers=headers)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["session_id"] == s["id"]
        assert data["user_has_submitted"] is False

    def test_unauthenticated_request_to_protected_endpoint_returns_401(self, client):
        """Verify protected endpoints reject requests lacking Authorization header."""
        s = client.post(
            "/api/sessions",
            json={"title": "Security Task", "creator_name": "Auditor"},
        ).json()

        # Call /status without header
        res_status = client.get(f"/api/sessions/{s['id']}/status")
        assert res_status.status_code == status.HTTP_401_UNAUTHORIZED
        assert "authorization header required" in res_status.json()["detail"].lower()

        # Call /participants without header
        res_parts = client.get(f"/api/sessions/{s['id']}/participants")
        assert res_parts.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_or_malformed_token_returns_401(self, client):
        """Verify malformed or forged bearer tokens are rejected with 401."""
        s = client.post(
            "/api/sessions",
            json={"title": "Security Task", "creator_name": "Auditor"},
        ).json()

        # 1. Malformed format (missing 'Bearer ')
        res_malformed = client.get(
            f"/api/sessions/{s['id']}/status",
            headers={"Authorization": "Token mst_sec_fake123"},
        )
        assert res_malformed.status_code == status.HTTP_401_UNAUTHORIZED

        # 2. Forged non-existent token
        res_forged = client.get(
            f"/api/sessions/{s['id']}/status",
            headers={"Authorization": "Bearer mst_sec_totally_fake_random_credential"},
        )
        assert res_forged.status_code == status.HTTP_401_UNAUTHORIZED
        assert "invalid or expired" in res_forged.json()["detail"].lower()

    def test_cross_session_access_rejected_with_403(self, client):
        """Verify token issued for Session 1 cannot access Session 2."""
        s1 = client.post("/api/sessions", json={"title": "Alpha Project", "creator_name": "Lead A"}).json()
        s2 = client.post("/api/sessions", json={"title": "Beta Project", "creator_name": "Lead B"}).json()

        headers_s2 = {"Authorization": f"Bearer {s2['participant_token']}"}

        # Attempt to access s1 status using s2 token
        res_cross = client.get(f"/api/sessions/{s1['id']}/status", headers=headers_s2)
        assert res_cross.status_code == status.HTTP_403_FORBIDDEN
        assert "do not belong to this session" in res_cross.json()["detail"]


class TestBlindSubmissionAndPrivacyEnforcement:
    """Tests for server-side blind submission rules and interpretation text leakage prevention."""

    def test_submit_interpretation_lifecycle(self, client):
        """Verify valid interpretation submission, duplicate prevention, and blank rejection."""
        s = client.post("/api/sessions", json={"title": "Task A", "creator_name": "Lead"}).json()
        headers = {"Authorization": f"Bearer {s['participant_token']}"}

        # 1. Reject blank interpretation with 422
        blank_res = client.post(
            f"/api/sessions/{s['id']}/interpretations",
            headers=headers,
            json={"response_text": "   "},
        )
        assert blank_res.status_code == 422

        # 2. Submit valid interpretation -> 201 Created
        sub_res = client.post(
            f"/api/sessions/{s['id']}/interpretations",
            headers=headers,
            json={
                "response_text": "Implement OAuth2 with GitHub and Google login.",
                "assumptions": ["Social provider client secrets exist."],
                "success_criteria": ["Users can authenticate via GitHub."],
            },
        )
        assert sub_res.status_code == status.HTTP_201_CREATED
        assert sub_res.json()["submitted"] is True
        assert "interpretation_id" in sub_res.json()

        # 3. Duplicate submission by same participant -> 409 Conflict
        dup_res = client.post(
            f"/api/sessions/{s['id']}/interpretations",
            headers=headers,
            json={"response_text": "Second attempt to overwrite."},
        )
        assert dup_res.status_code == status.HTTP_409_CONFLICT
        assert "already submitted" in dup_res.json()["detail"].lower()

    def test_privacy_gate_blocks_issues_before_submission(self, client):
        """Verify participant cannot view issues before submitting their own interpretation."""
        s = client.post("/api/sessions", json={"title": "Launch App", "creator_name": "Lead"}).json()

        join = client.post(
            "/api/sessions/join",
            json={"join_code": s["join_code"], "display_name": "Curious Dev"},
        ).json()
        dev_headers = {"Authorization": f"Bearer {join['participant_token']}"}

        # Developer attempts to view issues before submitting -> 403 Forbidden
        issues_res = client.get(f"/api/sessions/{s['id']}/issues", headers=dev_headers)
        assert issues_res.status_code == status.HTTP_403_FORBIDDEN
        assert "submit your own interpretation" in issues_res.json()["detail"].lower()

    def test_no_interpretation_text_leakage_in_participant_and_status_endpoints(self, client):
        """Verify /participants and /status endpoints strictly omit interpretation text."""
        s = client.post("/api/sessions", json={"title": "Privacy Test", "creator_name": "Lead"}).json()
        lead_headers = {"Authorization": f"Bearer {s['participant_token']}"}

        # Lead submits secret interpretation
        client.post(
            f"/api/sessions/{s['id']}/interpretations",
            headers=lead_headers,
            json={"response_text": "SUPER_SECRET_LEAD_INTERPRETATION_TEXT"},
        )

        # Dev joins
        dev = client.post(
            "/api/sessions/join",
            json={"join_code": s["join_code"], "display_name": "Dev B"},
        ).json()
        dev_headers = {"Authorization": f"Bearer {dev['participant_token']}"}

        # 1. Dev inspects /participants
        p_res = client.get(f"/api/sessions/{s['id']}/participants", headers=dev_headers)
        assert p_res.status_code == status.HTTP_200_OK
        p_data = p_res.json()
        assert len(p_data["participants"]) == 2

        for p in p_data["participants"]:
            assert "interpretation" not in p
            assert "response_text" not in p
            assert "assumptions" not in p
            assert "success_criteria" not in p

        # 2. String check: ensure secret text never appears anywhere in /participants JSON
        assert "SUPER_SECRET_LEAD_INTERPRETATION_TEXT" not in p_res.text

        # 3. Dev inspects /status
        stat_res = client.get(f"/api/sessions/{s['id']}/status", headers=dev_headers)
        assert stat_res.status_code == status.HTTP_200_OK
        stat_data = stat_res.json()
        assert stat_data["participant_count"] == 2
        assert stat_data["submission_count"] == 1
        assert stat_data["user_has_submitted"] is False
        assert stat_data.get("user_interpretation") is None
        assert "SUPER_SECRET_LEAD_INTERPRETATION_TEXT" not in stat_res.text

    def test_participant_can_view_only_their_own_submitted_interpretation(self, client):
        """Verify participants can view only their own submitted interpretation and never peers'."""
        s = client.post("/api/sessions", json={"title": "Privacy Isolation", "creator_name": "Lead"}).json()
        lead_headers = {"Authorization": f"Bearer {s['participant_token']}"}

        # Dev joins
        dev = client.post(
            "/api/sessions/join",
            json={"join_code": s["join_code"], "display_name": "Dev"},
        ).json()
        dev_headers = {"Authorization": f"Bearer {dev['participant_token']}"}

        # Before submission: both see has_submitted=False and null interpretation
        lead_me_pre = client.get(f"/api/sessions/{s['id']}/interpretations/me", headers=lead_headers)
        assert lead_me_pre.status_code == status.HTTP_200_OK
        assert lead_me_pre.json()["has_submitted"] is False
        assert lead_me_pre.json()["interpretation"] is None

        # Lead submits
        client.post(
            f"/api/sessions/{s['id']}/interpretations",
            headers=lead_headers,
            json={
                "response_text": "LEAD_CONFIDENTIAL_SPEC_123",
                "assumptions": "Postgres and Redis required",
            },
        )

        # Dev submits different text
        client.post(
            f"/api/sessions/{s['id']}/interpretations",
            headers=dev_headers,
            json={
                "response_text": "DEV_CONFIDENTIAL_SPEC_456",
                "assumptions": "SQLite and in-memory cache",
            },
        )

        # 1. Lead reads own interpretation via dedicated /me endpoint
        lead_me = client.get(f"/api/sessions/{s['id']}/interpretations/me", headers=lead_headers)
        assert lead_me.status_code == status.HTTP_200_OK
        lead_me_data = lead_me.json()
        assert lead_me_data["has_submitted"] is True
        assert lead_me_data["interpretation"] == "LEAD_CONFIDENTIAL_SPEC_123"
        assert lead_me_data["assumptions"] == "Postgres and Redis required"
        assert "DEV_CONFIDENTIAL_SPEC_456" not in lead_me.text

        # 2. Lead reads own interpretation via /status
        lead_stat = client.get(f"/api/sessions/{s['id']}/status", headers=lead_headers)
        assert lead_stat.status_code == status.HTTP_200_OK
        assert lead_stat.json()["user_interpretation"] == "LEAD_CONFIDENTIAL_SPEC_123"
        assert "DEV_CONFIDENTIAL_SPEC_456" not in lead_stat.text

        # 3. Dev reads own interpretation via dedicated /me endpoint
        dev_me = client.get(f"/api/sessions/{s['id']}/interpretations/me", headers=dev_headers)
        assert dev_me.status_code == status.HTTP_200_OK
        dev_me_data = dev_me.json()
        assert dev_me_data["has_submitted"] is True
        assert dev_me_data["interpretation"] == "DEV_CONFIDENTIAL_SPEC_456"
        assert dev_me_data["assumptions"] == "SQLite and in-memory cache"
        assert "LEAD_CONFIDENTIAL_SPEC_123" not in dev_me.text

        # 4. Dev reads own interpretation via /status
        dev_stat = client.get(f"/api/sessions/{s['id']}/status", headers=dev_headers)
        assert dev_stat.status_code == status.HTTP_200_OK
        assert dev_stat.json()["user_interpretation"] == "DEV_CONFIDENTIAL_SPEC_456"
        assert "LEAD_CONFIDENTIAL_SPEC_123" not in dev_stat.text

        # 5. /participants endpoint still omits all interpretations
        p_res = client.get(f"/api/sessions/{s['id']}/participants", headers=lead_headers)
        assert p_res.status_code == status.HTTP_200_OK
        assert "LEAD_CONFIDENTIAL_SPEC_123" not in p_res.text
        assert "DEV_CONFIDENTIAL_SPEC_456" not in p_res.text

        # 6. Unauthenticated access rejected with 401
        res_unauth = client.get(f"/api/sessions/{s['id']}/interpretations/me")
        assert res_unauth.status_code == status.HTTP_401_UNAUTHORIZED

        # 7. Cross-session access rejected with 403
        s_other = client.post(
            "/api/sessions", json={"title": "Other Session", "creator_name": "Other Lead"}
        ).json()
        other_headers = {"Authorization": f"Bearer {s_other['participant_token']}"}
        res_cross = client.get(f"/api/sessions/{s['id']}/interpretations/me", headers=other_headers)
        assert res_cross.status_code == status.HTTP_403_FORBIDDEN


class TestParticipantIdContractAndAgreementConfirmation:
    """Targeted regression tests for participant ID contract and agreement confirmation."""

    @patch("backend.app.services.analysis_service.analyze_interpretations", new_callable=AsyncMock)
    def test_dynamic_creator_and_joined_participant_can_confirm(self, mock_ai, client):
        """Verify creator and join-code participant can confirm using IDs returned by API."""
        mock_ai.return_value = {
            "status": "completed",
            "summary": "Consensus on launch scope.",
            "issues": [],
            "complementary_perspectives": [],
            "issue_counts": {"total": 0, "by_type": {}, "by_priority": {}},
            "error_message": None,
            "metadata": {"provider": "mock", "model": "mock", "participant_count": 2},
        }

        # 1. Create dynamic session
        s = client.post("/api/sessions", json={"title": "Launch Contract", "creator_name": "Lead Dev"}).json()
        creator_pid = s["creator_participant_id"]
        lead_headers = {"Authorization": f"Bearer {s['participant_token']}"}

        # 2. Join from join code
        j = client.post("/api/sessions/join", json={"join_code": s["join_code"], "display_name": "QA Lead"}).json()
        joined_pid = j["participant_id"]
        qa_headers = {"Authorization": f"Bearer {j['participant_token']}"}

        # 3. Submit interpretations
        client.post(
            f"/api/sessions/{s['id']}/interpretations",
            headers=lead_headers,
            json={"response_text": "Deliver secure auth and database migrations."},
        )
        client.post(
            f"/api/sessions/{s['id']}/interpretations",
            headers=qa_headers,
            json={"response_text": "Verify test suite pass rate and staging deployment."},
        )

        # 4. Trigger analysis
        client.post(f"/api/sessions/{s['id']}/analyze")

        # 5. Creator confirms using creator_participant_id returned by create endpoint
        conf_creator = client.post(
            f"/api/sessions/{s['id']}/agreement/confirm",
            json={"participant_id": creator_pid},
        )
        assert conf_creator.status_code == status.HTTP_200_OK
        assert creator_pid in conf_creator.json()["confirmed_by"]
        assert conf_creator.json()["is_fully_confirmed"] is False

        # 6. Joined participant confirms using participant_id returned by join endpoint
        conf_joined = client.post(
            f"/api/sessions/{s['id']}/agreement/confirm",
            json={"participant_id": joined_pid},
        )
        assert conf_joined.status_code == status.HTTP_200_OK
        assert joined_pid in conf_joined.json()["confirmed_by"]
        assert conf_joined.json()["is_fully_confirmed"] is True

    @patch("backend.app.services.analysis_service.analyze_interpretations", new_callable=AsyncMock)
    def test_unsubmitted_participant_cannot_confirm(self, mock_ai, client):
        """Verify a participant who joined but has not submitted cannot confirm the agreement."""
        mock_ai.return_value = {
            "status": "completed",
            "summary": "Partial consensus.",
            "issues": [],
            "complementary_perspectives": [],
            "issue_counts": {"total": 0, "by_type": {}, "by_priority": {}},
            "error_message": None,
            "metadata": {"provider": "mock", "model": "mock", "participant_count": 2},
        }

        s = client.post("/api/sessions", json={"title": "Submission Gate", "creator_name": "Lead"}).json()
        lead_headers = {"Authorization": f"Bearer {s['participant_token']}"}

        # 2 participants join
        p1 = client.post("/api/sessions/join", json={"join_code": s["join_code"], "display_name": "Submitter"}).json()
        p2 = client.post("/api/sessions/join", json={"join_code": s["join_code"], "display_name": "Lurker"}).json()

        # Only Lead and Submitter submit
        client.post(f"/api/sessions/{s['id']}/interpretations", headers=lead_headers, json={"response_text": "Scope A"})
        client.post(f"/api/sessions/{s['id']}/interpretations", headers={"Authorization": f"Bearer {p1['participant_token']}"}, json={"response_text": "Scope B"})

        client.post(f"/api/sessions/{s['id']}/analyze")

        # Lurker attempts to confirm without having submitted
        res = client.post(
            f"/api/sessions/{s['id']}/agreement/confirm",
            json={"participant_id": p2["participant_id"]},
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "has not submitted" in res.json()["detail"].lower()

    @patch("backend.app.services.analysis_service.analyze_interpretations", new_callable=AsyncMock)
    def test_invalid_or_unrelated_participant_id_rejected(self, mock_ai, client):
        """Verify an unknown or cross-session participant identifier is rejected."""
        mock_ai.return_value = {
            "status": "completed",
            "summary": "Consensus.",
            "issues": [],
            "complementary_perspectives": [],
            "issue_counts": {"total": 0, "by_type": {}, "by_priority": {}},
            "error_message": None,
            "metadata": {"provider": "mock", "model": "mock", "participant_count": 2},
        }

        s1 = client.post("/api/sessions", json={"title": "Session 1", "creator_name": "Lead"}).json()
        lead_headers = {"Authorization": f"Bearer {s1['participant_token']}"}
        p1 = client.post("/api/sessions/join", json={"join_code": s1["join_code"], "display_name": "Dev 1"}).json()

        client.post(f"/api/sessions/{s1['id']}/interpretations", headers=lead_headers, json={"response_text": "Scope 1"})
        client.post(f"/api/sessions/{s1['id']}/interpretations", headers={"Authorization": f"Bearer {p1['participant_token']}"}, json={"response_text": "Scope 2"})
        client.post(f"/api/sessions/{s1['id']}/analyze")

        # Arbitrary random attacker ID
        res_fake = client.post(
            f"/api/sessions/{s1['id']}/agreement/confirm",
            json={"participant_id": "malicious-attacker-id"},
        )
        assert res_fake.status_code == status.HTTP_400_BAD_REQUEST
        assert "has not submitted" in res_fake.json()["detail"].lower()

        # Session 2 participant attempting to confirm Session 1
        s2 = client.post("/api/sessions", json={"title": "Session 2", "creator_name": "Other Lead"}).json()
        res_cross = client.post(
            f"/api/sessions/{s1['id']}/agreement/confirm",
            json={"participant_id": s2["creator_participant_id"]},
        )
        assert res_cross.status_code == status.HTTP_400_BAD_REQUEST
        assert "has not submitted" in res_cross.json()["detail"].lower()

    @patch("backend.app.services.analysis_service.analyze_interpretations", new_callable=AsyncMock)
    def test_legacy_preset_demo_confirmation_and_bridge_test(self, mock_ai, client):
        """Verify that legacy preset demo identifiers (participant-a/b/c) continue to work cleanly."""
        mock_ai.return_value = {
            "status": "completed",
            "summary": "Demo issues.",
            "issues": [
                {
                    "type": "scope_difference",
                    "title": "Auth Scope",
                    "description": "Email vs Phone login.",
                    "evidence": [
                        {"participant_id": "participant-a", "quote": "email login", "source_field": "interpretation"},
                        {"participant_id": "participant-b", "quote": "phone login", "source_field": "interpretation"},
                    ],
                    "impact": "Scope mismatch.",
                    "priority": "high",
                    "confidence": 0.95,
                    "clarification_question": "Should phone be included?",
                }
            ],
            "complementary_perspectives": [],
            "issue_counts": {"total": 1, "by_type": {"scope_difference": 1}, "by_priority": {"high": 1}},
            "error_message": None,
            "metadata": {"provider": "mock", "model": "mock", "participant_count": 3},
        }

        # 1. Create demo session and 3 legacy participants
        s = client.post("/api/sessions", json={"title": "Prepare launch"}).json()
        s_id = s["id"]
        client.post(f"/api/sessions/{s_id}/participants", json={"participant_id": "participant-a", "name": "Alex", "interpretation": "email login"})
        client.post(f"/api/sessions/{s_id}/participants", json={"participant_id": "participant-b", "name": "Jordan", "interpretation": "phone login"})
        client.post(f"/api/sessions/{s_id}/participants", json={"participant_id": "participant-c", "name": "Taylor", "interpretation": "responsive ui"})

        # 2. Analyze
        client.post(f"/api/sessions/{s_id}/analyze")

        # 3. Resolve issue
        issues = client.get(f"/api/sessions/{s_id}/issues").json()
        client.patch(f"/api/sessions/{s_id}/issues/{issues[0]['id']}", json={"resolution_status": "resolved", "resolution_notes": "Email only."})

        # 4. Confirm legacy IDs
        c1 = client.post(f"/api/sessions/{s_id}/agreement/confirm", json={"participant_id": "participant-a"})
        assert c1.status_code == 200
        assert c1.json()["is_fully_confirmed"] is False

        c2 = client.post(f"/api/sessions/{s_id}/agreement/confirm", json={"participant_id": "participant-b"})
        assert c2.status_code == 200
        assert c2.json()["is_fully_confirmed"] is False

        c3 = client.post(f"/api/sessions/{s_id}/agreement/confirm", json={"participant_id": "participant-c"})
        assert c3.status_code == 200
        assert c3.json()["is_fully_confirmed"] is True

        # 5. Bridge Test
        bt = client.get(f"/api/sessions/{s_id}/bridge-test").json()
        assert bt["bridge_status"] == "bridged"
        assert bt["resolution_percentage"] == 100.0
        assert bt["is_fully_confirmed"] is True

