from fastapi import status
from app.integrations.ai_client import get_ai_client
from app.main import app


def test_trigger_analysis_insufficient_responses(client):
    s = client.post("/api/sessions", json={
        "title": "Launch Task",
        "description": "Prepare application for launch.",
        "min_participants": 2
    }).json()
    headers = {"Authorization": f"Bearer {s['participant_token']}"}

    # Only 1 participant submits
    client.post(
        f"/api/sessions/{s['id']}/interpretations",
        headers=headers,
        json={"response_text": "I will deploy the server."}
    )

    # Trigger analysis -> 400
    res = client.post(f"/api/sessions/{s['id']}/analyze", headers=headers)
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "at least 2 interpretations required" in res.json()["detail"]


def test_trigger_analysis_success(client):
    s = client.post("/api/sessions", json={
        "title": "Launch Task",
        "description": "Prepare application for launch.",
        "min_participants": 2
    }).json()
    lead_headers = {"Authorization": f"Bearer {s['participant_token']}"}

    # Dev joins
    dev = client.post("/api/sessions/join", json={
        "join_code": s["join_code"],
        "display_name": "Developer"
    }).json()
    dev_headers = {"Authorization": f"Bearer {dev['participant_token']}"}

    # Both submit
    client.post(
        f"/api/sessions/{s['id']}/interpretations",
        headers=lead_headers,
        json={"response_text": "Finish email and password login."}
    )
    client.post(
        f"/api/sessions/{s['id']}/interpretations",
        headers=dev_headers,
        json={"response_text": "Finish email or phone login and password recovery."}
    )

    # Trigger analysis
    res = client.post(f"/api/sessions/{s['id']}/analyze", headers=lead_headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["status"] == "completed"
    assert data["issues_count"] >= 1

    # Verify session transitioned to reviewing_issues
    sess_res = client.get(f"/api/sessions/{s['id']}", headers=lead_headers)
    assert sess_res.json()["status"] == "reviewing_issues"

    # Verify issues retrieval
    issues_res = client.get(f"/api/sessions/{s['id']}/issues", headers=lead_headers)
    assert issues_res.status_code == status.HTTP_200_OK
    issues_data = issues_res.json()
    assert len(issues_data["issues"]) >= 1
    # Check evidence structure
    first_issue = issues_data["issues"][0]
    assert len(first_issue["evidence"]) >= 1
    assert "quote" in first_issue["evidence"][0]


def test_ai_failure_recovery_without_losing_responses(client):
    class FailingAIClient:
        async def analyze_interpretations(self, task, participants):
            raise TimeoutError("Upstream LLM timed out.")

    app.dependency_overrides[get_ai_client] = lambda: FailingAIClient()

    try:
        s = client.post("/api/sessions", json={
            "title": "Crash Test",
            "description": "Testing AI crash recovery.",
            "min_participants": 2
        }).json()
        lead_headers = {"Authorization": f"Bearer {s['participant_token']}"}

        p2 = client.post("/api/sessions/join", json={
            "join_code": s["join_code"],
            "display_name": "Dev B"
        }).json()
        p2_headers = {"Authorization": f"Bearer {p2['participant_token']}"}

        # Both submit
        client.post(
            f"/api/sessions/{s['id']}/interpretations",
            headers=lead_headers,
            json={"response_text": "Lead interpretation."}
        )
        client.post(
            f"/api/sessions/{s['id']}/interpretations",
            headers=p2_headers,
            json={"response_text": "Dev interpretation."}
        )

        # Trigger analysis -> should fail gracefully with 502
        res = client.post(f"/api/sessions/{s['id']}/analyze", headers=lead_headers)
        assert res.status_code == status.HTTP_502_BAD_GATEWAY
        assert "interpretations remain saved" in res.json()["detail"].lower()

        # Verify responses are still intact in session status
        stat = client.get(f"/api/sessions/{s['id']}/status", headers=lead_headers).json()
        assert stat["submission_count"] == 2
        assert stat["status"] == "collecting_responses"
    finally:
        # Restore mock
        from app.integrations.ai_client import MockAIClient
        app.dependency_overrides[get_ai_client] = lambda: MockAIClient()
