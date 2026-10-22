from fastapi import status


def test_submit_interpretation(client):
    # 1. Create session
    s = client.post("/api/sessions", json={
        "title": "Auth Task",
        "description": "Build user auth.",
        "creator_name": "Lead"
    }).json()
    headers = {"Authorization": f"Bearer {s['participant_token']}"}

    # 2. Submit interpretation
    res = client.post(
        f"/api/sessions/{s['id']}/interpretations",
        headers=headers,
        json={
            "response_text": "I'll implement email/password login and a password reset flow.",
            "assumptions": ["Email service is configured."],
            "success_criteria": ["Users can sign in."]
        }
    )
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert data["submitted"] is True
    assert "interpretation_id" in data


def test_duplicate_submission_prevention(client):
    s = client.post("/api/sessions", json={
        "title": "Auth Task",
        "description": "Build user auth.",
        "creator_name": "Lead"
    }).json()
    headers = {"Authorization": f"Bearer {s['participant_token']}"}

    # First submission
    client.post(
        f"/api/sessions/{s['id']}/interpretations",
        headers=headers,
        json={"response_text": "First interpretation text."}
    )

    # Second submission by same participant -> 409
    dup_res = client.post(
        f"/api/sessions/{s['id']}/interpretations",
        headers=headers,
        json={"response_text": "Second interpretation attempt."}
    )
    assert dup_res.status_code == status.HTTP_409_CONFLICT
    assert "already submitted" in dup_res.json()["detail"].lower()


def test_blank_interpretation_rejected(client):
    s = client.post("/api/sessions", json={
        "title": "Auth Task",
        "description": "Build user auth.",
        "creator_name": "Lead"
    }).json()
    headers = {"Authorization": f"Bearer {s['participant_token']}"}

    res = client.post(
        f"/api/sessions/{s['id']}/interpretations",
        headers=headers,
        json={"response_text": "   "}
    )
    assert res.status_code == 422


def test_privacy_gate_before_submission(client):
    # Creator creates session
    s = client.post("/api/sessions", json={
        "title": "Launch Task",
        "description": "Launch the app."
    }).json()

    # Participant joins
    p = client.post("/api/sessions/join", json={
        "join_code": s["join_code"],
        "display_name": "Late Joiner"
    }).json()
    p_headers = {"Authorization": f"Bearer {p['participant_token']}"}

    # Participant tries to view issues before submitting while still collecting -> 403
    issues_res = client.get(f"/api/sessions/{s['id']}/issues", headers=p_headers)
    assert issues_res.status_code == status.HTTP_403_FORBIDDEN
    assert "submit your own interpretation" in issues_res.json()["detail"]
