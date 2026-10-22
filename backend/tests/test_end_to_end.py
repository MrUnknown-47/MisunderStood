from fastapi import status


def test_complete_end_to_end_user_journey(client):
    """Full integration test of the 12-stage user journey."""
    # 1. Team leader creates session
    create_resp = client.post("/api/sessions", json={
        "title": "Build persistent event registration system",
        "description": "Build an event registration system that can handle registrations and prevent people from registering more than once.",
        "context": "College hackathon project with 3 teammates.",
        "creator_name": "Project Lead",
        "min_participants": 3
    })
    assert create_resp.status_code == status.HTTP_201_CREATED
    lead_session = create_resp.json()
    session_id = lead_session["id"]
    join_code = lead_session["join_code"]
    lead_token = lead_session["participant_token"]
    lead_headers = {"Authorization": f"Bearer {lead_token}"}

    # 2. Developer and Designer join
    dev_resp = client.post("/api/sessions/join", json={
        "join_code": join_code,
        "display_name": "Developer"
    })
    assert dev_resp.status_code == status.HTTP_200_OK
    dev_token = dev_resp.json()["participant_token"]
    dev_headers = {"Authorization": f"Bearer {dev_token}"}

    des_resp = client.post("/api/sessions/join", json={
        "join_code": join_code,
        "display_name": "Designer"
    })
    assert des_resp.status_code == status.HTTP_200_OK
    des_token = des_resp.json()["participant_token"]
    des_headers = {"Authorization": f"Bearer {des_token}"}

    # 3. Check participants list (privacy preserved: no responses visible)
    participants_resp = client.get(f"/api/sessions/{session_id}/participants", headers=lead_headers)
    assert participants_resp.status_code == status.HTTP_200_OK
    parts = participants_resp.json()["participants"]
    assert len(parts) == 3
    for p in parts:
        assert p["has_submitted"] is False
        assert "response_text" not in p

    # 4. Independent interpretation submissions
    # Dev submits
    sub1 = client.post(
        f"/api/sessions/{session_id}/interpretations",
        headers=dev_headers,
        json={
            "response_text": "I'll create a registration form, save registrations in the database, and reject duplicate email addresses.",
            "assumptions": ["Email is the only unique identifier."],
            "success_criteria": ["Database rejects duplicate emails."]
        }
    )
    assert sub1.status_code == status.HTTP_201_CREATED

    # Designer checks issues before submitting -> 403 Forbidden
    des_premature_issues = client.get(f"/api/sessions/{session_id}/issues", headers=des_headers)
    assert des_premature_issues.status_code == status.HTTP_403_FORBIDDEN

    # Designer submits
    sub2 = client.post(
        f"/api/sessions/{session_id}/interpretations",
        headers=des_headers,
        json={
            "response_text": "I'll build the registration page and mobile responsive confirmation screen. Users should be able to register again if they want to correct a mistake with phone or email.",
            "assumptions": ["Users might need to edit entries."],
            "success_criteria": ["Responsive mobile screen."]
        }
    )
    assert sub2.status_code == status.HTTP_201_CREATED

    # Project Lead submits
    sub3 = client.post(
        f"/api/sessions/{session_id}/interpretations",
        headers=lead_headers,
        json={
            "response_text": "Each student should register only once, receive a confirmation email, and be able to edit their registration details later with password recovery.",
            "assumptions": ["Confirmation email is mandatory."],
            "success_criteria": ["One registration per student."]
        }
    )
    assert sub3.status_code == status.HTTP_201_CREATED

    # 5. Check session status: all 3 submitted, ready for analysis
    status_resp = client.get(f"/api/sessions/{session_id}/status", headers=lead_headers)
    assert status_resp.status_code == status.HTTP_200_OK
    assert status_resp.json()["can_start_analysis"] is True
    assert status_resp.json()["submission_count"] == 3

    # 6. Trigger AI analysis
    analyze_resp = client.post(f"/api/sessions/{session_id}/analyze", headers=lead_headers)
    assert analyze_resp.status_code == status.HTTP_200_OK
    analyze_data = analyze_resp.json()
    assert analyze_data["status"] == "completed"
    assert analyze_data["issues_count"] >= 1

    # 7. Retrieve findings and evidence
    issues_resp = client.get(f"/api/sessions/{session_id}/issues", headers=lead_headers)
    assert issues_resp.status_code == status.HTTP_200_OK
    issues_list = issues_resp.json()["issues"]
    assert len(issues_list) >= 1
    comp_list = issues_resp.json()["complementary_perspectives"]
    assert len(comp_list) >= 1  # mobile responsive captured!

    # 8. Team resolves and clarifies issues
    first_issue = issues_list[0]
    res_resp = client.patch(
        f"/api/issues/{first_issue['id']}",
        headers=lead_headers,
        json={
            "status": "resolved",
            "resolution_text": "Each student can have one registration per event; returning students can edit an existing registration using email."
        }
    )
    assert res_resp.status_code == status.HTTP_200_OK
    assert res_resp.json()["status"] == "resolved"

    # 9. Generate Shared Agreement
    agreement_resp = client.post(f"/api/sessions/{session_id}/agreement", headers=lead_headers)
    assert agreement_resp.status_code == status.HTTP_201_CREATED
    agreement = agreement_resp.json()
    agreement_id = agreement["agreement_id"]
    assert agreement["status"] == "pending_confirmation"
    assert len(agreement["content"]["confirmed_requirements"]) >= 2

    # 10. Confirm agreement by all participants
    # Lead confirms
    c1 = client.post(f"/api/agreements/{agreement_id}/confirm", headers=lead_headers, json={"confirmed": True})
    assert c1.status_code == status.HTTP_200_OK
    assert c1.json()["all_participants_confirmed"] is False

    # Dev confirms
    c2 = client.post(f"/api/agreements/{agreement_id}/confirm", headers=dev_headers, json={"confirmed": True})
    assert c2.status_code == status.HTTP_200_OK
    assert c2.json()["all_participants_confirmed"] is False

    # Designer confirms -> all confirmed!
    c3 = client.post(f"/api/agreements/{agreement_id}/confirm", headers=des_headers, json={"confirmed": True})
    assert c3.status_code == status.HTTP_200_OK
    assert c3.json()["all_participants_confirmed"] is True
    assert c3.json()["session_status"] == "completed"

    # 11. Verify session state is completed
    sess_check = client.get(f"/api/sessions/{session_id}", headers=lead_headers)
    assert sess_check.json()["status"] == "completed"

    # 12. Run Bridge Test
    bridge_resp = client.get(f"/api/sessions/{session_id}/bridge-test", headers=lead_headers)
    assert bridge_resp.status_code == status.HTTP_200_OK
    bt = bridge_resp.json()
    assert bt["initial_issue_count"] == len(issues_list)
    assert bt["resolved_issue_count"] >= 1
    assert bt["agreement_status"] == "confirmed"
    assert bt["resolution_rate"] is not None
    assert bt["resolution_rate"] > 0
