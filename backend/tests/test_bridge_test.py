from fastapi import status
from app.integrations.ai_client import get_ai_client
from app.main import app


def test_bridge_test_zero_initial_issues(client):
    # Mock AI returning zero issues (e.g. perfect alignment)
    class ZeroIssueAIClient:
        async def analyze_interpretations(self, task, participants):
            return {
                "summary": "Full alignment detected.",
                "issues": [],
                "complementary_perspectives": []
            }

    app.dependency_overrides[get_ai_client] = lambda: ZeroIssueAIClient()
    try:
        s = client.post("/api/sessions", json={
            "title": "Aligned Task",
            "description": "Simple task.",
            "min_participants": 2
        }).json()
        lead_headers = {"Authorization": f"Bearer {s['participant_token']}"}

        dev = client.post("/api/sessions/join", json={"join_code": s["join_code"], "display_name": "Dev"}).json()
        dev_headers = {"Authorization": f"Bearer {dev['participant_token']}"}

        client.post(f"/api/sessions/{s['id']}/interpretations", headers=lead_headers, json={"response_text": "Aligned interpretation."})
        client.post(f"/api/sessions/{s['id']}/interpretations", headers=dev_headers, json={"response_text": "Aligned interpretation."})

        client.post(f"/api/sessions/{s['id']}/analyze", headers=lead_headers)

        bt_res = client.get(f"/api/sessions/{s['id']}/bridge-test", headers=lead_headers)
        assert bt_res.status_code == status.HTTP_200_OK
        data = bt_res.json()
        assert data["initial_issue_count"] == 0
        assert data["resolved_issue_count"] == 0
        assert data["unresolved_issue_count"] == 0
        assert data["dismissed_issue_count"] == 0
        # If N_0 == 0, resolution_rate must be null (not dividing by zero!)
        assert data["resolution_rate"] is None
    finally:
        from app.integrations.ai_client import MockAIClient
        app.dependency_overrides[get_ai_client] = lambda: MockAIClient()


def test_bridge_test_metrics_calculation(client):
    s = client.post("/api/sessions", json={
        "title": "Launch Task",
        "description": "Prepare application for launch.",
        "min_participants": 2
    }).json()
    lead_headers = {"Authorization": f"Bearer {s['participant_token']}"}

    dev = client.post("/api/sessions/join", json={"join_code": s["join_code"], "display_name": "Dev"}).json()
    dev_headers = {"Authorization": f"Bearer {dev['participant_token']}"}

    client.post(f"/api/sessions/{s['id']}/interpretations", headers=lead_headers, json={"response_text": "Finish email and password login."})
    client.post(f"/api/sessions/{s['id']}/interpretations", headers=dev_headers, json={"response_text": "Finish email or phone login and password recovery."})

    client.post(f"/api/sessions/{s['id']}/analyze", headers=lead_headers)
    issues = client.get(f"/api/sessions/{s['id']}/issues", headers=lead_headers).json()["issues"]

    total_issues = len(issues)
    assert total_issues >= 2

    # Check metrics before any resolution
    bt1 = client.get(f"/api/sessions/{s['id']}/bridge-test", headers=lead_headers).json()
    assert bt1["initial_issue_count"] == total_issues
    assert bt1["resolved_issue_count"] == 0
    assert bt1["unresolved_issue_count"] == total_issues
    assert bt1["dismissed_issue_count"] == 0
    assert bt1["resolution_rate"] == 0.0

    # Resolve issue 1
    client.patch(
        f"/api/issues/{issues[0]['id']}",
        headers=lead_headers,
        json={"status": "resolved", "resolution_text": "Resolved by team."}
    )

    # Dismiss issue 2
    client.patch(
        f"/api/issues/{issues[1]['id']}",
        headers=lead_headers,
        json={"status": "dismissed"}
    )

    # Re-check Bridge Test metrics
    bt2 = client.get(f"/api/sessions/{s['id']}/bridge-test", headers=lead_headers).json()
    assert bt2["initial_issue_count"] == total_issues
    assert bt2["resolved_issue_count"] == 1
    assert bt2["dismissed_issue_count"] == 1
    assert bt2["unresolved_issue_count"] == total_issues - 2
    expected_rate = round((1 / total_issues) * 100.0, 1)
    assert bt2["resolution_rate"] == expected_rate
