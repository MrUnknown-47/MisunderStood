from fastapi import status


def test_create_session(client):
    payload = {
        "title": "Prepare application for launch",
        "description": "Finish the required functionality before release.",
        "context": "Focus on web users first.",
        "creator_name": "Project Lead",
        "min_participants": 2
    }
    response = client.post("/api/sessions", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "id" in data
    assert "join_code" in data
    assert data["join_code"].startswith("GAP-")
    assert data["status"] == "collecting_responses"
    assert "creator_participant_id" in data
    assert data["participant_token"].startswith("mst_sec_")


def test_join_session(client):
    # 1. Create session
    create_res = client.post("/api/sessions", json={
        "title": "Demo Task",
        "description": "Build user auth.",
        "creator_name": "Lead"
    })
    session_data = create_res.json()
    join_code = session_data["join_code"]
    session_id = session_data["id"]

    # 2. Join session
    join_res = client.post("/api/sessions/join", json={
        "join_code": join_code,
        "display_name": "Developer A"
    })
    assert join_res.status_code == status.HTTP_200_OK
    join_data = join_res.json()
    assert join_data["session_id"] == session_id
    assert "participant_id" in join_data
    assert join_data["participant_token"].startswith("mst_sec_")


def test_join_invalid_code(client):
    res = client.post("/api/sessions/join", json={
        "join_code": "INVALID-CODE",
        "display_name": "Hacker"
    })
    assert res.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in res.json()["detail"].lower()


def test_get_session_details_authorized(client):
    create_res = client.post("/api/sessions", json={
        "title": "Demo Task",
        "description": "Build user auth.",
        "creator_name": "Lead"
    })
    s = create_res.json()
    headers = {"Authorization": f"Bearer {s['participant_token']}"}

    res = client.get(f"/api/sessions/{s['id']}", headers=headers)
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["title"] == "Demo Task"


def test_cross_session_access_prevention(client):
    # Create session 1
    s1 = client.post("/api/sessions", json={
        "title": "Session 1",
        "description": "Task 1"
    }).json()

    # Create session 2
    s2 = client.post("/api/sessions", json={
        "title": "Session 2",
        "description": "Task 2"
    }).json()

    # Try to access session 1 using token from session 2
    headers = {"Authorization": f"Bearer {s2['participant_token']}"}
    res = client.get(f"/api/sessions/{s1['id']}", headers=headers)
    assert res.status_code == status.HTTP_403_FORBIDDEN
    assert "do not belong to this session" in res.json()["detail"]


def test_get_participants_and_status(client):
    create_res = client.post("/api/sessions", json={
        "title": "Demo Task",
        "description": "Build user auth.",
        "creator_name": "Lead"
    })
    s = create_res.json()
    headers = {"Authorization": f"Bearer {s['participant_token']}"}

    # Second participant joins
    client.post("/api/sessions/join", json={
        "join_code": s["join_code"],
        "display_name": "Dev 2"
    })

    # Get participants
    p_res = client.get(f"/api/sessions/{s['id']}/participants", headers=headers)
    assert p_res.status_code == status.HTTP_200_OK
    p_data = p_res.json()
    assert len(p_data["participants"]) == 2
    # Ensure text is NEVER included in participant list
    for p in p_data["participants"]:
        assert "response_text" not in p

    # Get status
    stat_res = client.get(f"/api/sessions/{s['id']}/status", headers=headers)
    assert stat_res.status_code == status.HTTP_200_OK
    stat_data = stat_res.json()
    assert stat_data["participant_count"] == 2
    assert stat_data["submission_count"] == 0
    assert stat_data["user_has_submitted"] is False
    assert stat_data["can_start_analysis"] is False
