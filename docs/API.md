# MISUNDERSTOOD: API Reference

This document provides specifications for all endpoints in the MISUNDERSTOOD backend API.

All endpoints are prefixed with `/api`.  
When the backend is running, interactive documentation is also available at `http://localhost:8000/docs`.

---

## Table of Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Service health status check |
| `POST` | `/api/sessions` | Create a new collaborative task session |
| `GET` | `/api/sessions/{session_id}` | Retrieve session details and participant counts |
| `POST` | `/api/sessions/{session_id}/participants` | Submit or update an independent interpretation |
| `POST` | `/api/sessions/{session_id}/analyze` | Trigger AI misunderstanding analysis |
| `GET` | `/api/sessions/{session_id}/analysis` | Retrieve latest analysis result and findings |
| `GET` | `/api/sessions/{session_id}/issues` | List findings for a session with optional status filter |
| `PATCH` | `/api/sessions/{session_id}/issues/{issue_id}` | Update finding resolution status and decision notes |
| `GET` | `/api/sessions/{session_id}/agreement` | Retrieve or compile the shared agreement checklist |
| `POST` | `/api/sessions/{session_id}/agreement/confirm` | Record participant sign-off on the agreement |
| `GET` | `/api/sessions/{session_id}/bridge-test` | Compute before-and-after Bridge Test metrics |

---

## 1. Health Check

### `GET /api/health`
Verifies backend service availability.

#### Response: `200 OK`
```json
{
  "status": "healthy",
  "app": "MISUNDERSTOOD",
  "version": "1.0.0"
}
```

---

## 2. Session Management

### `POST /api/sessions`
Creates a new collaborative session for a task instruction.

#### Request Body (`application/json`)
| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `title` | string | Yes | Task instruction given to the team (1–200 characters) |
| `description` | string | No | Optional technical context or background (max 2000 chars) |

```json
{
  "title": "Prepare the application for launch",
  "description": "Milestone 1 release readiness requirements"
}
```

#### Response: `201 Created`
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "session_code": "WLCJLN",
  "title": "Prepare the application for launch",
  "description": "Milestone 1 release readiness requirements",
  "status": "collecting",
  "participant_count": 0,
  "created_at": "2026-10-17T10:00:00Z",
  "updated_at": "2026-10-17T10:00:00Z"
}
```

---

### `GET /api/sessions/{session_id}`
Retrieves session metadata, participant submission counts, and current status.

#### Path Parameters
| Parameter | Type | Description |
| :--- | :--- | :--- |
| `session_id` | string (UUID) | The unique session identifier |

#### Response: `200 OK`
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "session_code": "WLCJLN",
  "title": "Prepare the application for launch",
  "description": "Milestone 1 release readiness requirements",
  "status": "collecting",
  "participant_count": 3,
  "created_at": "2026-10-17T10:00:00Z",
  "updated_at": "2026-10-17T10:05:00Z"
}
```

#### Common Errors
- `404 Not Found`: If `session_id` does not exist.

---

## 3. Participant Submissions

### `POST /api/sessions/{session_id}/participants`
Submits an independent interpretation of the task. If a participant with the same `participant_id` has already submitted to this session, their submission is updated.

#### Request Body (`application/json`)
| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `participant_id` | string | Yes | Unique participant handle or ID (1–100 chars) |
| `name` | string | No | Display name (max 100 chars) |
| `interpretation` | string | Yes | Interpretation of what the task requires (1–5000 chars) |
| `assumptions` | string | No | Unconfirmed assumptions made by participant (max 2000 chars) |
| `success_criteria` | string | No | Definition of done or success metric (max 2000 chars) |

```json
{
  "participant_id": "participant-a",
  "name": "Alex (Developer)",
  "interpretation": "Complete email and password login.",
  "assumptions": "PostgreSQL database will be used.",
  "success_criteria": "Unit tests pass and auth API returns 200."
}
```

#### Response: `201 Created`
```json
{
  "id": "7ca65f12-2123-4562-b3fc-1c863f66efa1",
  "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "participant_id": "participant-a",
  "name": "Alex (Developer)",
  "interpretation": "Complete email and password login.",
  "assumptions": "PostgreSQL database will be used.",
  "success_criteria": "Unit tests pass and auth API returns 200.",
  "submitted_at": "2026-10-17T10:02:00Z"
}
```

#### Common Errors
- `404 Not Found`: Session does not exist.
- `422 Unprocessable Entity`: Validation failure (e.g. empty interpretation).

---

## 4. AI Analysis

### `POST /api/sessions/{session_id}/analyze`
Triggers AI analysis across all submitted interpretations in the session.

#### Validation & Preconditions
- Requires at least 2 participant submissions with non-empty interpretations.
- Enforces concurrency lock: returns `409 Conflict` if analysis is currently in progress.

#### Response: `200 OK`
```json
{
  "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "analysis_id": "9ba12f34-1111-4562-b3fc-3c963f66bba2",
  "status": "completed",
  "summary": "Participants agree on core authentication, but differ on recovery and registration scope.",
  "issues": [
    {
      "id": "1fa85f64-5717-4562-b3fc-2c963f66afa1",
      "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "analysis_id": "9ba12f34-1111-4562-b3fc-3c963f66bba2",
      "type": "scope_difference",
      "title": "Scope of login methods and recovery differs",
      "description": "Participant A limits auth to email/password, while Participant B includes phone login and self-service password recovery.",
      "evidence": [
        {
          "participant_id": "participant-a",
          "quote": "Complete email and password login.",
          "source_field": "interpretation"
        },
        {
          "participant_id": "participant-b",
          "quote": "Complete email or phone login, registration, and password recovery.",
          "source_field": "interpretation"
        }
      ],
      "impact": "If unaccounted for, recovery workflows and SMS integrations may be missing from initial release.",
      "priority": "high",
      "confidence": 0.95,
      "clarification_question": "Should phone login and self-service password recovery be included in the launch release?",
      "resolution_status": "open",
      "resolution_notes": null,
      "created_at": "2026-10-17T10:10:00Z",
      "updated_at": "2026-10-17T10:10:00Z"
    }
  ],
  "complementary_perspectives": [
    {
      "title": "Mobile-responsive styling and onboarding",
      "description": "Designer's requirement for mobile viewports complements the backend auth scope.",
      "evidence": [
        {
          "participant_id": "participant-c",
          "quote": "Complete onboarding and mobile-responsive UI.",
          "source_field": "interpretation"
        }
      ]
    }
  ],
  "issue_counts": {
    "total": 1,
    "by_type": { "scope_difference": 1 },
    "by_priority": { "high": 1 }
  },
  "error_message": null,
  "metadata": {
    "provider": "gemini",
    "model": "gemini-2.5-flash",
    "participant_count": 3
  }
}
```

#### Common Errors
- `400 Bad Request`: Fewer than 2 participants have submitted interpretations.
- `404 Not Found`: Session does not exist.
- `409 Conflict`: Analysis is already running for this session.
- `502 Bad Gateway`: AI provider failure (network error, exhausted quota, unparseable model response).

---

### `GET /api/sessions/{session_id}/analysis`
Retrieves the latest persisted analysis snapshot and current issue states for a session.

#### Response: `200 OK`
Same schema as `POST /api/sessions/{session_id}/analyze`.

#### Common Errors
- `404 Not Found`: Session does not exist or no analysis has been run yet.

---

## 5. Issues & Findings Management

### `GET /api/sessions/{session_id}/issues`
Retrieves all persisted findings for a session.

#### Query Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `resolution_status` | string | No | Filter by status: `open`, `resolved`, or `dismissed` |

#### Response: `200 OK`
Returns a list of `IssueRead` objects.

---

### `PATCH /api/sessions/{session_id}/issues/{issue_id}`
Updates the human resolution status and records agreed decision notes.

#### Request Body (`application/json`)
| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `resolution_status` | string | Yes | One of: `"open"`, `"resolved"`, `"dismissed"` |
| `resolution_notes` | string | No | Team's agreed decision or scope justification (max 1000 chars) |

```json
{
  "resolution_status": "resolved",
  "resolution_notes": "Phone login deferred to v2. Password recovery included in v1."
}
```

#### Response: `200 OK`
Returns the updated `IssueRead` object with updated `resolution_status`, `resolution_notes`, and `updated_at`.

#### Common Errors
- `404 Not Found`: If session or issue ID is not found.
- `422 Unprocessable Entity`: If `resolution_status` is not one of `open`, `resolved`, `dismissed`.

---

## 6. Shared Agreement & Confirmation

### `GET /api/sessions/{session_id}/agreement`
Retrieves or automatically compiles the shared agreement checklist based on the task description and resolved/dismissed findings.

#### Response: `200 OK`
```json
{
  "id": "5ba85f64-5717-4562-b3fc-2c963f66aba1",
  "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "items": [
    "Core Deliverable: Prepare the application for launch",
    "Agreed: Scope of login methods and recovery differs (Phone login deferred to v2. Password recovery included in v1.)",
    "Complementary Alignment: Mobile-responsive styling and onboarding"
  ],
  "excluded_items": [
    "Excluded / Out of Scope: Social login integration (Marked out-of-scope by team)"
  ],
  "confirmed_by": ["participant-a"],
  "is_fully_confirmed": false,
  "created_at": "2026-10-17T10:15:00Z",
  "updated_at": "2026-10-17T10:18:00Z"
}
```

---

### `POST /api/sessions/{session_id}/agreement/confirm`
Records a participant's explicit confirmation of the agreement checklist.

#### Request Body (`application/json`)
| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `participant_id` | string | Yes | ID of the confirming participant (1–100 chars) |

```json
{
  "participant_id": "participant-b"
}
```

#### Response: `200 OK`
Returns the updated `AgreementRead` object. If all submitted participants have confirmed, `is_fully_confirmed` becomes `true`.

#### Common Errors
- `400 Bad Request`: If `participant_id` does not match any participant in the session.
- `404 Not Found`: Session does not exist.

---

## 7. The Bridge Test

### `GET /api/sessions/{session_id}/bridge-test`
Calculates before-and-after comparison metrics based on persisted issue states and participant confirmations.

#### Response: `200 OK`
```json
{
  "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "initial_issues_count": 3,
  "resolved_count": 2,
  "dismissed_count": 1,
  "open_count": 0,
  "resolution_percentage": 100.0,
  "is_fully_confirmed": true,
  "confirmed_participants": ["participant-a", "participant-b", "participant-c"],
  "total_participants": 3,
  "bridge_status": "bridged",
  "disclaimer": "This metric reflects the resolution of identified differences among participants, not proof of universal understanding."
}
```

#### Calculation & Edge Cases
The resolution percentage is computed from persisted counts:
```text
Resolution % = ((resolved_count + dismissed_count) / initial_issues_count) * 100.0
```
- **Zero Initial Issues**: When `initial_issues_count == 0`, `resolution_percentage` defaults to `100.0%`.
- However, `bridge_status` is not automatically `"bridged"`. It remains `"unresolved"` until participants review and sign off, transitioning to `"in_progress"` upon initial confirmation and `"bridged"` only once all participants confirm (`is_fully_confirmed == true`).

#### Status Meaning
- `"bridged"`: `open_count == 0` and `is_fully_confirmed == true`.
- `"in_progress"`: At least one issue resolved/dismissed or at least one participant confirmed, but open issues or pending confirmations remain.
- `"unresolved"`: No issues addressed and no confirmations recorded.
