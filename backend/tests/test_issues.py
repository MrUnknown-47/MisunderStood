import uuid
from fastapi import status


def _setup_session_with_issues(client):
    s = client.post("/api/sessions", json={
        "title": "Auth Task",
        "description": "Build user auth.",
        "min_participants": 2
    }).json()
    lead_headers = {"Authorization": f"Bearer {s['participant_token']}"}

    dev = client.post("/api/sessions/join", json={
        "join_code": s["join_code"],
        "display_name": "Dev"
    }).json()
    dev_headers = {"Authorization": f"Bearer {dev['participant_token']}"}

    client.post(f"/api/sessions/{s['id']}/interpretations", headers=lead_headers, json={"response_text": "Email login only."})
    client.post(f"/api/sessions/{s['id']}/interpretations", headers=dev_headers, json={"response_text": "Email and phone login."})

    client.post(f"/api/sessions/{s['id']}/analyze", headers=lead_headers)
    issues = client.get(f"/api/sessions/{s['id']}/issues", headers=lead_headers).json()["issues"]
    return s, dev, lead_headers, issues


def test_resolve_issue(client):
    s, dev, lead_headers, issues = _setup_session_with_issues(client)
    issue_id = issues[0]["id"]

    res = client.patch(
        f"/api/issues/{issue_id}",
        headers=lead_headers,
        json={
            "status": "resolved",
            "resolution_text": "We agree on email-only login for v1."
        }
    )
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["status"] == "resolved"
    assert data["resolution_text"] == "We agree on email-only login for v1."


def test_dismiss_issue(client):
    s, dev, lead_headers, issues = _setup_session_with_issues(client)
    issue_id = issues[0]["id"]

    res = client.patch(
        f"/api/issues/{issue_id}",
        headers=lead_headers,
        json={"status": "dismissed"}
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["status"] == "dismissed"


def test_resolve_issue_requires_resolution_text(client):
    s, dev, lead_headers, issues = _setup_session_with_issues(client)
    issue_id = issues[0]["id"]

    res = client.patch(
        f"/api/issues/{issue_id}",
        headers=lead_headers,
        json={"status": "resolved"}
    )
    assert res.status_code == 422
    assert "resolution text is required" in res.json()["detail"].lower()


def test_cross_session_issue_patch_forbidden(client):
    s, dev, lead_headers, issues = _setup_session_with_issues(client)
    issue_id = issues[0]["id"]

    # Other session participant
    s2 = client.post("/api/sessions", json={"title": "Other", "description": "Other"}).json()
    other_headers = {"Authorization": f"Bearer {s2['participant_token']}"}

    res = client.patch(
        f"/api/issues/{issue_id}",
        headers=other_headers,
        json={"status": "dismissed"}
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN
