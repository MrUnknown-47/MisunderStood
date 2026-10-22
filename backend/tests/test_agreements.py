from fastapi import status


def _setup_resolved_session(client):
    s = client.post("/api/sessions", json={
        "title": "Launch Task",
        "description": "Prepare application for launch.",
        "min_participants": 2
    }).json()
    lead_headers = {"Authorization": f"Bearer {s['participant_token']}"}

    dev = client.post("/api/sessions/join", json={
        "join_code": s["join_code"],
        "display_name": "Dev"
    }).json()
    dev_headers = {"Authorization": f"Bearer {dev['participant_token']}"}

    client.post(f"/api/sessions/{s['id']}/interpretations", headers=lead_headers, json={"response_text": "Email login only."})
    client.post(f"/api/sessions/{s['id']}/interpretations", headers=dev_headers, json={"response_text": "Email or phone login."})

    client.post(f"/api/sessions/{s['id']}/analyze", headers=lead_headers)
    issues = client.get(f"/api/sessions/{s['id']}/issues", headers=lead_headers).json()["issues"]

    # Resolve first issue
    client.patch(
        f"/api/issues/{issues[0]['id']}",
        headers=lead_headers,
        json={"status": "resolved", "resolution_text": "Email login only for MVP."}
    )

    return s, dev, lead_headers, dev_headers


def test_generate_and_confirm_agreement(client):
    s, dev, lead_headers, dev_headers = _setup_resolved_session(client)

    # 1. Generate agreement
    agr_res = client.post(f"/api/sessions/{s['id']}/agreement", headers=lead_headers)
    assert agr_res.status_code == status.HTTP_201_CREATED
    agr_data = agr_res.json()
    assert agr_data["status"] == "pending_confirmation"
    agreement_id = agr_data["agreement_id"]

    # Check checklist content
    content = agr_data["content"]
    assert len(content["confirmed_requirements"]) >= 1

    # Session status is now agreement_pending
    sess = client.get(f"/api/sessions/{s['id']}", headers=lead_headers).json()
    assert sess["status"] == "agreement_pending"

    # 2. Lead confirms
    lead_conf = client.post(
        f"/api/agreements/{agreement_id}/confirm",
        headers=lead_headers,
        json={"confirmed": True, "comment": "Agreed by lead"}
    )
    assert lead_conf.status_code == status.HTTP_200_OK
    assert lead_conf.json()["all_participants_confirmed"] is False
    assert lead_conf.json()["session_status"] == "agreement_pending"

    # 3. Duplicate confirmation by lead -> 409
    dup_conf = client.post(
        f"/api/agreements/{agreement_id}/confirm",
        headers=lead_headers,
        json={"confirmed": True}
    )
    assert dup_conf.status_code == status.HTTP_409_CONFLICT

    # 4. Dev confirms -> all confirmed, session completed!
    dev_conf = client.post(
        f"/api/agreements/{agreement_id}/confirm",
        headers=dev_headers,
        json={"confirmed": True, "comment": "Agreed by dev"}
    )
    assert dev_conf.status_code == status.HTTP_200_OK
    assert dev_conf.json()["all_participants_confirmed"] is True
    assert dev_conf.json()["session_status"] == "completed"

    # Verify session is now completed
    sess_after = client.get(f"/api/sessions/{s['id']}", headers=lead_headers).json()
    assert sess_after["status"] == "completed"
