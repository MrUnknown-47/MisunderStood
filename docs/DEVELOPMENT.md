# MISUNDERSTOOD: Developer & Contributing Guide

This guide describes development workflows, repository conventions, coding standards, and procedures for extending the MISUNDERSTOOD codebase.

---

## 1. Development Setup

### Environment Requirements
- Python 3.10+
- Node.js 18+ and npm
- Git

### Virtual Environment & Dependencies
```bash
# Backend setup
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn sqlalchemy pydantic python-dotenv httpx pytest pytest-asyncio google-genai psycopg2-binary

# Frontend setup
cd frontend
npm install
cd ..
```

### Running in Development Mode
Run the backend with auto-reload and the frontend with Vite HMR:

```bash
# Terminal 1: Backend
python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Frontend
cd frontend
npm run dev
```

The Vite dev server runs at `http://localhost:5173` and proxies all `/api/*` traffic to `http://127.0.0.1:8000`.

---

## 2. Repository Conventions & Standards

### Naming
- **Files & Modules**: Snake case (`analysis_service.py`, `evidence_validator.py`).
- **Classes**: PascalCase (`EvidenceValidator`, `SessionModel`, `IssueRead`).
- **Functions & Variables**: Concise, descriptive snake_case (`load_session`, `session_id`, `is_redundant_issue`). Avoid unnecessary prefixes (`do_create_session`) or cryptic abbreviations (`sess_cd`).
- **React Components**: PascalCase (`App.jsx`), hooks in camelCase (`loadSession`).

### Comments & Documentation
- **Do not restate the code**: Avoid comments like `# return session` or `# validate input`.
- **Document non-obvious constraints**: Keep comments that explain safety requirements, architectural invariants, or platform quirks (e.g. SQLite multi-threading, why human resolution status is preserved across AI re-runs).
- **Keep docstrings informative and concise**: Focus on parameters, behavior, and error conditions without boilerplate filler.

---

## 3. How to Add a New API Endpoint

1. **Define Schema**: Add request and response models in `backend/app/schemas.py`.
2. **Add Route Handler**:
   - Locate the appropriate router under `backend/app/routes/` (or create a new router file).
   - Use dependency injection for the database session (`db: Session = Depends(get_db)`).
   - Return strongly typed Pydantic models.
3. **Register Route**: If creating a new router, mount it in `backend/app/main.py` under `settings.API_PREFIX`.
4. **Update Frontend Client**: Add corresponding fetch functions in `frontend/src/api.js`.
5. **Add Integration Tests**: Add automated tests in `backend/tests/test_backend_integration.py`.

---

## 4. How to Modify AI Analysis Safely

When modifying prompts or candidate handling in `backend/ai/`:

1. **Preserve Public Contract**: The public interface in `backend/ai/__init__.py` must remain:
   ```python
   async def analyze_interpretations(task: dict, participants: list[dict], client=None) -> dict: ...
   ```
2. **Do Not Weaken Evidence Verification**: Never bypass `EvidenceValidator` or allow unquoted/approximate findings into the output.
3. **Preserve Deduplication Rules**: Ensure that generic umbrella issues cannot suppress specific findings, and distinct decisions sharing evidence are retained.
4. **Run the Full Test Suite**: Always run `python3 -m pytest backend/tests -v` before committing.

---

## 5. Database Configuration & Migrations

### Default Configuration
By default, the backend uses local SQLite:
```env
DATABASE_URL=sqlite:///./misunderstood.db
```
The database engine is configured with `connect_args={"check_same_thread": False}` to support concurrent async requests across FastAPI worker threads.

### PostgreSQL Support
To use PostgreSQL in staging or production:
1. Ensure `psycopg2-binary` is installed.
2. Update `.env`:
   ```env
   DATABASE_URL=postgresql://user:password@localhost:5432/misunderstood
   ```
The models use standard SQLAlchemy types with `JSON` columns, which are natively supported in PostgreSQL.

---

## 6. Debugging Common Problems

### Problem: `HTTP 409 Conflict` during analysis
- **Cause**: An analysis is already in progress (`session.status == "analyzing"`).
- **Fix**: Wait for the active analysis to complete, or check logs if a previous run crashed without updating status.

### Problem: `HTTP 400 Bad Request` on `/analyze`
- **Cause**: The session has fewer than 2 participant submissions with non-empty interpretations.
- **Fix**: Submit interpretations from at least two participants.

### Problem: Frontend cannot connect to backend in development
- **Cause**: Vite dev server proxy is pointing to a port where FastAPI is not running.
- **Fix**: Confirm that FastAPI is listening on `127.0.0.1:8000` (`python3 -m uvicorn backend.app.main:app --port 8000`).

### Problem: Quotes rejected by EvidenceValidator
- **Cause**: The candidate finding contains words not present in the participant's original text, or cites the wrong participant.
- **Fix**: Verify raw submissions. Quotes must match exact contiguous substrings after standard whitespace normalization.

---

## 7. Pre-Commit / Pre-Demo Verification

Run this verification sequence before committing code or presenting a demonstration:

```bash
# 1. Run full backend test suite
python3 -m pytest backend/tests -v

# 2. Build production frontend bundle
cd frontend && npm run build && cd ..

# 3. Verify FastAPI imports cleanly
python3 -c "from backend.app.main import app; print('App imported successfully:', app.title)"
```
All commands must exit with code `0`.
