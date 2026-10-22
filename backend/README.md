# MISUNDERSTOOD — Backend API & Database

> *"Same conversation. Different realities."*  
> An AI-powered collaboration platform that detects and resolves differences in how people interpret the same task.

---

## 1. Overview

**MISUNDERSTOOD** addresses a fundamental breakdown in team collaboration: people frequently use the same words to describe a task while holding incompatible interpretations, unconfirmed assumptions, and mismatched success criteria.

This backend provides the complete REST API, database architecture, session state machine, independent-submission privacy gate, AI analysis orchestrator, issue resolution engine, agreement confirmation workflow, and Bridge Test metric calculation.

---

## 2. Technology Stack

- **Language:** Python 3.14+
- **Web Framework:** [FastAPI](https://fastapi.tiangolo.com/) with asynchronous endpoints and OpenAPI documentation at `/docs`
- **Data Validation & Schemas:** [Pydantic v2](https://docs.pydantic.dev/) & `pydantic-settings`
- **Database & ORM:** [SQLAlchemy 2.0](https://www.sqlalchemy.org/) supporting PostgreSQL / Supabase with seamless SQLite dual-compatibility for zero-config local testing
- **Schema Migrations:** [Alembic](https://alembic.sqlalchemy.org/)
- **Automated Testing:** [Pytest](https://docs.pytest.org/) with isolated in-memory testing fixtures

---

## 3. Database Architecture

The backend manages seven relational tables using UUID primary keys, UTC server timestamps, foreign key constraints with cascade deletes, and indexed query columns:

```
┌────────────────────────────────────────────────────────┐
│                        sessions                        │
│  (id, join_code, title, description, context, status)  │
└───────────────────────────┬────────────────────────────┘
                            │
       ┌────────────────────┼────────────────────┐
       ▼                    ▼                    ▼
┌──────────────┐     ┌─────────────┐      ┌──────────────┐
│ participants │     │   analyses  │      │  agreements  │
└──────┬───────┘     └──────┬──────┘      └──────┬───────┘
       │                    │                    │
       ▼                    ▼                    ▼
┌────────────────┐   ┌─────────────┐      ┌─────────────────────────┐
│interpretations │   │   issues    │      │ agreement_confirmations │
└────────────────┘   └─────────────┘      └─────────────────────────┘
```

### Table Definitions

1. **`sessions`**: Collaboration session metadata, task description, context, human-readable unique join code (e.g., `GAP-4821`), and state machine status.
2. **`participants`**: Session membership, participant display names, roles (`creator` vs `participant`), and high-entropy bearer token hashes.
3. **`interpretations`**: Submitted independent interpretations, explicit assumptions, and success criteria. Enforces unique constraint on `(session_id, participant_id)`.
4. **`analyses`**: AI analysis audit run, model identifier, prompt version, execution status, and raw validated JSON output.
5. **`issues`**: Individual evidence-backed misunderstandings (`contradiction`, `assumption`, `omission`, `scope_difference`, `success_criteria_difference`), title, description, quotes, priority (`low`, `medium`, `high`), clarification question, and status (`open`, `discussing`, `resolved`, `dismissed`).
6. **`agreements`**: Structured shared agreement checklist (`confirmed_requirements`, `unresolved_decisions`, `optional_suggestions`), version number, and state.
7. **`agreement_confirmations`**: Formal participant confirmations. Enforces unique constraint on `(agreement_id, participant_id)`.

---

## 4. Session State Machine

The backend enforces strict state transitions on the server:

```
collecting_responses ──► analyzing ──► reviewing_issues ──► agreement_pending ──► completed
```

- **`collecting_responses`**: Participants join and submit independent interpretations. Responses from others remain hidden.
- **`analyzing`**: AI analysis is triggered; state is locked to prevent concurrent duplicate analyses.
- **`reviewing_issues`**: Participants review detected issues, inspect quoted evidence, answer clarification questions, and resolve or dismiss issues.
- **`agreement_pending`**: A shared agreement checklist is generated from resolved items; participants review and confirm.
- **`completed`**: Transitioned automatically once all submitting participants have confirmed the shared agreement.

---

## 5. Required REST API Endpoints

All endpoints use JSON payloads and return descriptive `{"detail": "..."}` errors on failures.

### Health
| Method | Path | Description | Authorization |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | Backend and database connectivity check | None |

### Sessions & Participants
| Method | Path | Description | Authorization |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/sessions` | Create a new session, generate join code, issue creator token | None |
| `POST` | `/api/sessions/join` | Join session via code, issue participant token | None |
| `GET` | `/api/sessions/{session_id}` | Retrieve authorized session metadata | Bearer Token |
| `GET` | `/api/sessions/{session_id}/participants` | List participants and submission status (text stripped) | Bearer Token |
| `GET` | `/api/sessions/{session_id}/status` | Check aggregate progress and readiness for analysis | Bearer Token |

### Interpretations & Analysis
| Method | Path | Description | Authorization |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/sessions/{session_id}/interpretations` | Submit independent interpretation (enforces privacy gate) | Bearer Token |
| `POST` | `/api/sessions/{session_id}/analyze` | Trigger AI gap detection and persist validated findings | Bearer Token |
| `GET` | `/api/sessions/{session_id}/issues` | Retrieve evidence-backed issues and complementary perspectives | Bearer Token |

### Issue Resolution
| Method | Path | Description | Authorization |
| :--- | :--- | :--- | :--- |
| `PATCH` | `/api/issues/{issue_id}` | Update status (`discussing`, `resolved`, `dismissed`) & resolution | Bearer Token |

### Agreements & Confirmations
| Method | Path | Description | Authorization |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/sessions/{session_id}/agreement` | Generate structured shared agreement from resolved issues | Bearer Token |
| `POST` | `/api/agreements/{agreement_id}/confirm` | Record participant confirmation (advances session on completion) | Bearer Token |

### Bridge Test
| Method | Path | Description | Authorization |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/sessions/{session_id}/bridge-test` | Return resolution metrics calculated from stored records | Bearer Token |

---

## 6. Security & Privacy Gate

1. **Independent Interpretation Privacy Gate:**
   - Participants must not be influenced by seeing other people's submissions.
   - The backend enforces this strictly on the server: `GET /api/sessions/{session_id}/participants` and `GET /api/sessions/{session_id}/status` never expose interpretation text.
   - Calling `GET /api/sessions/{session_id}/issues` is blocked (`403 Forbidden`) until the caller submits their own response.
2. **Session-Scoped Authorization:**
   - Every session creation and join operation returns a cryptographically secure random bearer token (`mst_sec_...`).
   - The SHA-256 hash of this token is stored in the database.
   - Subsequent calls validate the token and ensure the caller's participant belongs to the specific session referenced in the URL path. Cross-session access attempts return `403 Forbidden`.
3. **Secret Protection:**
   - All internal credentials and AI API keys remain on the backend and are never returned to client apps.

---

## 7. AI Engine Integration (Member 3 Adapter)

The backend decouples AI analysis through the `AIAnalysisProvider` protocol in `app/integrations/ai_client.py`:

```python
async def analyze_interpretations(
    task: dict,
    participants: list[dict]
) -> dict: ...
```

### Resiliency & Recovery
- Interpretations are persisted and committed **before** calling the AI service.
- If the AI engine times out or fails, the analysis record is marked `status="failed"` and the session returns to a safe state, allowing instant retries without data loss.
- Returned evidence quotes are checked against actual participant submissions, preventing hallucinated attributions.
- A built-in `MockAIClient` supports offline testing, automated CI, and demonstrations without paid API costs.

---

## 8. Bridge Test Metrics

The Bridge Test calculates resolution metrics strictly from persisted database records:
- \(N_0\) = `initial_issue_count`
- \(R\) = `resolved_issue_count`
- \(U\) = `unresolved_issue_count` (`open` or `discussing`)
- \(D\) = `dismissed_issue_count`

$$\text{Resolution Rate} = \frac{R}{N_0} \times 100$$

*Note: If \(N_0 = 0\) (zero initial issues detected), `resolution_rate` returns `null` ("Not applicable").*

---

## 9. Local Setup & Execution

### 1. Clone & Setup Virtual Environment
```bash
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Default `.env` configuration uses SQLite (`sqlite:///./misunderstood.db`) and `USE_MOCK_AI=true` for instant zero-dependency local execution.

For PostgreSQL / Supabase, simply update `DATABASE_URL`:
```ini
DATABASE_URL=postgresql://postgres:yourpassword@db.supabase.co:5432/postgres
```

### 4. Run Database Migrations
```bash
python -m alembic upgrade head
```

### 5. Start Backend Server
```bash
uvicorn app.main:app --reload --port 8000
```
Open **[http://localhost:8000/docs](http://localhost:8000/docs)** to view the interactive FastAPI Swagger documentation.

---

## 10. Automated Testing

Run the full automated test suite (22 unit, integration, security, and end-to-end tests):
```bash
python -m pytest -v
```
All tests use in-memory SQLite and mock AI integrations, executing in under 2 seconds with zero network overhead.
