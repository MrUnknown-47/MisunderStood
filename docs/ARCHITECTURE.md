# MISUNDERSTOOD: System Architecture

This document describes the architectural design, data models, lifecycle states, and core algorithms of the MISUNDERSTOOD collaboration platform.

---

## 1. Architectural Components

MISUNDERSTOOD consists of four cohesive layers:

```
┌────────────────────────────────────────────────────────┐
│                   React 19 Frontend                    │
│   - Single Page Application built with Vite 8          │
│   - Blind submission inputs for participants           │
│   - Misunderstanding Map with verbatim evidence        │
│   - Shared Agreement and Bridge Test dashboard         │
└───────────────────────────┬────────────────────────────┘
                            │ HTTP JSON /api/*
┌───────────────────────────▼────────────────────────────┐
│                    FastAPI Backend                     │
│   - Route Controllers: sessions, issues, agreements    │
│   - Analysis Orchestration Service                     │
│   - Concurrency Locking & Lifecycle Guards             │
│   - Idempotent Issue Synchronization                   │
└──────────────┬──────────────────────────┬──────────────┘
               │                          │
┌──────────────▼─────────────┐ ┌──────────▼──────────────┐
│     SQLAlchemy Database    │ │    AI / ML Module       │
│  - SessionModel            │ │  - analyzer.py          │
│  - ParticipantModel        │ │  - client.py            │
│  - AnalysisModel           │ │  - validator.py         │
│  - IssueModel              │ │  - prompts.py           │
│  - AgreementModel          │ │  - schemas.py           │
└────────────────────────────┘ └─────────────────────────┘
```

### Frontend (`frontend/`)
- Pure React 19 application bundled with Vite.
- Communicates with the backend exclusively via `frontend/src/api.js`.
- In development, Vite proxies `/api` requests to `http://127.0.0.1:8000`.
- In production, FastAPI mounts `frontend/dist` directly at root `/`, enabling single-binary or single-process deployment.

### FastAPI Application (`backend/app/`)
- Modular router structure (`routes/sessions.py`, `routes/issues.py`, `routes/agreements.py`).
- Session and transaction management via SQLAlchemy dependency injection (`get_db`).
- Input validation and schema enforcement via Pydantic v2 models.
- Concurrency locks ensuring that simultaneous analysis requests cannot produce race conditions or duplicate issue records.

### Database (`backend/app/database.py`, `backend/app/models.py`)
- Configured by default for SQLite (`sqlite:///./misunderstood.db`), fully compatible with PostgreSQL via standard SQLAlchemy engine pooling and migrations.
- Automatically initializes schema tables during FastAPI startup lifespan.

### AI / ML Module (`backend/ai/`)
- Completely decoupled library module with a single public entrypoint:
  ```python
  from backend.ai import analyze_interpretations
  ```
- Handles input schema validation, deterministic short-circuits (zero/one participant, identical consensus), prompt construction, multi-provider LLM communication, deterministic quote validation, and issue deduplication.

---

## 2. Request and Data Flow

```
[User]
   │
   ├── 1. POST /api/sessions ──> Creates SessionModel (status='collecting')
   │
   ├── 2. POST /api/sessions/{id}/participants ──> Upserts ParticipantModel
   │
   ├── 3. POST /api/sessions/{id}/analyze
   │       │
   │       ├── Checks session existence (404 if missing)
   │       ├── Checks status != 'analyzing' (409 conflict lock)
   │       ├── Validates participant_count >= 2 (400 if insufficient)
   │       ├── Sets session.status = 'analyzing'
   │       │
   │       ├── Invokes backend.ai.analyze_interpretations()
   │       │     ├── Short-circuits (0, 1, or identical participants)
   │       │     ├── Calls configured LLM (Gemini / OpenRouter / OpenAI)
   │       │     ├── EvidenceValidator verifies exact verbatim quotes
   │       │     └── Deduplicates restatements & generic umbrella issues
   │       │
   │       ├── Persists AnalysisModel (status='completed')
   │       ├── Synchronizes IssueModel records:
   │       │     ├── Updates AI fields for existing findings
   │       │     ├── PRESERVES existing resolution_status & resolution_notes
   │       │     ├── Inserts new findings with status='open'
   │       │     └── Prunes stale unaddressed open issues
   │       │
   │       └── Sets session.status = 'completed'
   │
   ├── 4. PATCH /api/sessions/{id}/issues/{issue_id} ──> Updates status ('resolved'/'dismissed')
   │
   ├── 5. GET /api/sessions/{id}/agreement ──> Compiles checklist from resolved issues
   │
   ├── 6. POST /api/sessions/{id}/agreement/confirm ──> Signs off participant
   │
   └── 7. GET /api/sessions/{id}/bridge-test ──> Computes resolution percentage & bridge status
```

---

## 3. Session and Participant Lifecycle

A session transitions through explicit states:

```
               ┌───────────────┐
               │  collecting   │ <── Initial state upon session creation
               └───────┬───────┘
                       │ User requests analysis (requires >= 2 participants)
                       ▼
               ┌───────────────┐
               │   analyzing   │ <── Concurrency lock active
               └───────┬───────┘
          ┌────────────┴────────────┐
          │                         │
          ▼                         ▼
   ┌───────────────┐         ┌───────────────┐
   │   completed   │         │    failed     │
   └───────────────┘         └───────────────┘
```

- `collecting`: Session created, accepting participant submissions.
- `analyzing`: Analysis in progress. Subsequent analysis calls while in this state are rejected with `HTTP 409 Conflict`.
- `completed`: Analysis finished successfully. Issues and analysis records are persisted.
- `failed`: LLM provider or unexpected runtime error occurred. Session status marks failure, and the analysis record stores error diagnostics.
- `insufficient_data`: Set if requested with fewer than 2 participants.

---

## 4. AI Analysis & Evidence Verification

A primary objective of MISUNDERSTOOD is **deterministic evidence validation**. LLMs can fabricate or paraphrase quotes when attempting to highlight differences. To prevent ungrounded findings from being presented as fact, all candidate quotes are deterministically checked against participant raw text.

### Verification Algorithm
1. The AI module prompts the LLM to return candidate issues along with exact quotes and the participant ID.
2. The candidate issues pass through `EvidenceValidator`:
   - Checks that `participant_id` matches a real participant in the session.
   - Searches for `quote` as a contiguous slice in the participant's `interpretation`, `assumptions`, or `success_criteria`.
   - Uses conservative whitespace normalization (collapsing consecutive spaces and trimming) without fuzzy or phonetic matching.
   - For `contradiction` and `scope_difference` issues, enforces that quotes from **at least 2 distinct participants** are verified.
3. Any candidate quote that cannot be found verbatim in the submitted text is discarded.
4. If an issue loses all evidence, it is rejected entirely.
5. **Fail-Safe Guard**: If the model proposed issues, but every issue was rejected due to unverified quotes, the system does not return `completed` with 0 issues (which would falsely imply consensus). Instead, it sets `status = "failed"` with diagnostic details.

---

## 5. Issue Deduplication & Decision Preservation

### Deterministic Deduplication
LLMs often produce overlapping findings from the same participant submissions (e.g., asking whether phone login is included, while also asking whether authentication covers phone numbers).

The deduplication pipeline (`backend/ai/validator.py`):
1. **Suppresses generic umbrella issues**: If specific findings exist (e.g., phone login scope), broad umbrella findings (e.g., "Authentication requirements differ") are suppressed regardless of the order emitted by the LLM.
2. **Detects decision keyword overlap**: Questions targeting identical decision tokens (using Jaccard similarity >= 0.50 or subset containment) are deduplicated, keeping the first finding and logging the restatement reason.
3. **Preserves distinct decisions**: Independent decisions sharing evidence (e.g., phone login vs. password recovery) are preserved as separate issues.

### Human Decision Preservation
When participants re-run AI analysis after modifying interpretations:
- Issues are matched by compound key: `(issue.type.lower(), issue.title.lower().strip())`.
- If an issue was previously marked `resolved` or `dismissed` by the team, its `resolution_status` and `resolution_notes` are **strictly preserved** while its AI description and confidence scores are refreshed.
- Issues that disappear from the new analysis are deleted **only if they were `open`**. If the team already resolved or dismissed them, they remain persisted.

---

## 6. Agreement Confirmation & The Bridge Test

The platform tracks the transition from divergence to confirmed alignment:

### Shared Agreement Compilation
- Aggregates the core task title and description.
- Appends every `resolved` issue along with the recorded agreed decision note.
- Appends every identified `complementary_perspective`.
- Compiles `excluded_items` from `dismissed` issues (e.g., features explicitly agreed as out-of-scope).

### Multi-Party Confirmation
- Each participant confirms the agreement by submitting their `participant_id`.
- The agreement becomes `is_fully_confirmed = True` when all session participants have explicitly confirmed.

### The Bridge Test Formula
The Bridge Test measures objective resolution progress from persisted records:

```text
Resolution % = ((Resolved Issues + Dismissed Issues) / Initial Issues) * 100
```

- **Zero Initial Issues Edge Case**: If `initial_issues == 0` (clean consensus), the resolution percentage defaults to `100.0%`. However, `bridge_status` does not immediately become `"bridged"`. It remains `"unresolved"` until participants review and sign off, transitioning to `"in_progress"` upon initial confirmation and `"bridged"` only once all participants confirm (`is_fully_confirmed == True`).
- Status is `"bridged"` when `open_count == 0` and `is_fully_confirmed == True`.
- Status is `"in_progress"` if any issue has been addressed or any participant confirmed, but open issues or unconfirmed participants remain.
- Otherwise, status is `"unresolved"`.

---

## 7. Error Handling & Provider Fallback

The LLM client (`backend/ai/client.py`) implements multi-provider resilience:

- **Explicit Mode (`AI_PROVIDER=gemini|openrouter|openai`)**:
  - Direct execution against the specified provider.
  - Never silently switches providers on failure.
- **Automatic Mode (`AI_PROVIDER=auto`)**:
  - Determines available keys in preference order: `Gemini` → `OpenRouter` → `OpenAI`.
  - Automatically falls back to the next configured provider if eligible errors occur (rate limits, 401/403 credential rejections, timeouts, 500 server errors, or malformed JSON responses).
- **Sanitized Errors**: Exception strings and HTTP error details sanitize credentials to ensure API keys are never leaked to logs or client responses.
