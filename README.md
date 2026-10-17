# MISUNDERSTOOD

> "Same conversation. Different realities."  
> **Theme**: Bridge the Gap — Devlympics Hackathon

MISUNDERSTOOD is a collaboration platform designed to discover and bridge divergences when team members interpret the same task instruction differently.

---

## The Problem

When a team receives an instruction such as *"Prepare the application for launch"*, participants often interpret the scope and deliverables through their own individual lens:
- A developer focuses on backend authentication (email and password login).
- A project manager expects self-service account recovery, phone login, and registration.
- A designer expects mobile-responsive styling and an onboarding walkthrough.

Because everyone assumes they share a common understanding, these gaps typically remain hidden until deployment or sprint review, causing rework and friction.

MISUNDERSTOOD acts as a neutral mediator. It collects task interpretations independently in blind mode, analyzes submissions for discrepancies using verified evidence quotes, guides the team with clarification questions, and tracks agreement on a shared checklist via the **Bridge Test**.

---

## How It Works

```
1. Create Session
   Host creates a task session with a 6-character code (or loads the 3-party demo).

2. Blind Submissions
   Participants independently submit their interpretation, assumptions, and success criteria.
   Submissions remain private to avoid anchoring bias.

3. AI Analysis & Evidence Verification
   The AI analyzes submissions for scope differences, contradictions, unconfirmed assumptions,
   and omitted requirements. Every finding must cite verified verbatim quotations.

4. Misunderstanding Map
   Findings are displayed with priority levels, exact quotes, and actionable clarification questions.

5. Team Resolution
   Participants discuss and resolve or dismiss findings, documenting agreed decisions.

6. Confirmed Agreement & The Bridge Test
   Resolved decisions compile into a confirmed checklist with explicit participant sign-offs.
   The Bridge Test measures resolution progress from detection to consensus.
```

---

## Core Features

- **Blind Submission Protocol**: Hides participant interpretations prior to analysis to prevent conformity bias.
- **Evidence-Backed Findings**: Every identified discrepancy must cite exact verbatim excerpts from participant submissions. Findings lacking evidence or citing single participants for multi-party disputes are rejected.
- **Deterministic Deduplication**: Overlapping findings sharing evidence are deduplicated if they ask the same question, while distinct decisions are preserved.
- **Decision Preservation**: Re-running the AI analysis never overwrites human decisions (`resolved` or `dismissed`) or agreed notes.
- **Multi-Party Confirmation**: Tracks explicit sign-offs per participant on the shared agreement checklist.
- **The Bridge Test**: Calculates the percentage of addressed misunderstandings and signals when a task has achieved confirmed consensus.
- **Multi-Provider AI Engine**: Supports Google Gemini, OpenRouter, and OpenAI with automatic fallback and credential protection.

---

## Technology Stack

- **Backend**: Python 3.10+, FastAPI, SQLAlchemy, Pydantic v2, Uvicorn, SQLite (PostgreSQL compatible via `psycopg2`).
- **AI / LLM**: Multi-provider client supporting Google Gemini (direct via `google-genai`), OpenRouter, and OpenAI via `httpx`.
- **Frontend**: React 19, Vite 8, Lucide React icons.
- **Testing**: Pytest, HTTPX AsyncClient (`pytest-asyncio`).

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────┐
│                   React 19 Frontend                    │
│   (Session Creation, Submissions, Map, Agreement)      │
└───────────────────────────┬────────────────────────────┘
                            │ /api HTTP requests
┌───────────────────────────▼────────────────────────────┐
│                  FastAPI Backend                       │
│  ┌──────────────────────┐   ┌────────────────────────┐ │
│  │    Route Handlers    │   │   Analysis Service     │ │
│  │ (Sessions, Issues,   │──>│ (Lifecycle, Lock,      │ │
│  │  Agreements)         │   │  Decision Preservation)│ │
│  └──────────────────────┘   └───────────┬────────────┘ │
│             │                           │              │
│  ┌──────────▼───────────┐   ┌───────────▼────────────┐ │
│  │  SQLAlchemy Database │   │    backend.ai Module   │ │
│  │  (Sessions, Issues,  │   │  ┌──────────────────┐  │ │
│  │   Agreements, etc.)  │   │  │   LLM Client     │  │ │
│  └──────────────────────┘   │  └────────┬─────────┘  │ │
│                             │  ┌────────▼─────────┐  │ │
│                             │  │ EvidenceValidator│  │ │
│                             │  └──────────────────┘  │ │
│                             └────────────────────────┘ │
└────────────────────────────────────────────────────────┘
```

For full details, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Prerequisites

- Python 3.10 or higher
- Node.js 18 or higher (with npm)
- (Optional) AI API key from Google Gemini, OpenRouter, or OpenAI for live AI analysis. Offline tests and demo mode work without an API key.

---

## Local Setup & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/vaibhav100/Shunya.git
cd Shunya
```

### 2. Backend Setup
```bash
# Create and activate a Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install backend dependencies
pip install fastapi uvicorn sqlalchemy pydantic python-dotenv httpx pytest pytest-asyncio google-genai psycopg2-binary
```

### 3. Frontend Setup
```bash
cd frontend
npm install
cd ..
```

### 4. Environment Configuration
Copy the sample environment file to `.env`:
```bash
cp .env.example .env
```

Configure your `.env` file:
```env
# AI Provider API Keys (at least one is required for live LLM analysis)
GEMINI_API_KEY=your_gemini_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Provider Configuration
# Options: auto (gemini -> openrouter -> openai), gemini, openrouter, openai
AI_PROVIDER=auto
AI_MODEL=
AI_MAX_TOKENS=3000

# Optional Database URL (defaults to SQLite: sqlite:///./misunderstood.db)
DATABASE_URL=sqlite:///./misunderstood.db

# Optional CORS origins (comma-separated)
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

---

## Running the Application

### Option A: Unified Server (FastAPI serves API + Built Frontend)
Build the frontend assets and run FastAPI:
```bash
# 1. Build frontend production assets
cd frontend && npm run build && cd ..

# 2. Start FastAPI server
python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
Open [http://localhost:8000](http://localhost:8000) in your browser.

### Option B: Active Development Mode (Vite Dev Server + FastAPI)
Run the backend and frontend development servers concurrently:

**Terminal 1 — Backend:**
```bash
python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 — Frontend Dev Server:**
```bash
cd frontend
npm run dev
```
Open [http://localhost:5173](http://localhost:5173). Requests to `/api/*` are proxied to port 8000 automatically.

---

## Running Tests

The test suite runs **100% offline** using deterministic fixtures without live API calls:

```bash
python3 -m pytest backend/tests -v
```

Test suite coverage:
- `backend/tests/test_ai_analyzer.py`: Unit tests for evidence validation, deduction rules, duplicate elimination, priority calibration, and provider fallback behavior.
- `backend/tests/test_backend_integration.py`: Integration tests for API lifecycle transitions, issue patching, concurrency safeguards, human decision preservation, agreement compilation, and Bridge Test calculations.

---

## API Documentation

When the FastAPI server is running, interactive OpenAPI documentation is available at:
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

Full markdown endpoint documentation is available at [docs/API.md](docs/API.md).

---

## Project Structure

```text
Shunya/
├── README.md                      # Project documentation and quickstart
├── .env.example                   # Environment configuration template
├── .gitignore                     # Git ignore rules (secrets, DBs, caches)
├── backend/
│   ├── ai/                        # AI analysis and validation engine
│   │   ├── __init__.py            # Public interface (analyze_interpretations)
│   │   ├── analyzer.py            # AI workflow coordinator & short-circuits
│   │   ├── client.py              # Multi-provider LLM client (Gemini, OpenRouter, OpenAI)
│   │   ├── prompts.py             # System and user prompt builders
│   │   ├── schemas.py             # AnalysisResult and issue Pydantic models
│   │   └── validator.py           # Verbatim quote & multi-participant evidence validator
│   ├── app/                       # FastAPI application
│   │   ├── config.py              # Application configuration and environment loading
│   │   ├── database.py            # SQLAlchemy engine, session maker, init_db
│   │   ├── main.py                # FastAPI entrypoint, CORS, static file mount
│   │   ├── models.py              # SQLAlchemy database models
│   │   ├── schemas.py             # API request and response Pydantic schemas
│   │   ├── routes/
│   │   │   ├── sessions.py        # /api/sessions endpoints
│   │   │   ├── issues.py          # /api/sessions/{id}/issues endpoints
│   │   │   └── agreements.py      # /api/sessions/{id}/agreement & bridge-test
│   │   └── services/
│   │       └── analysis_service.py # Orchestrator, concurrency lock & decision preservation
│   └── tests/                     # Automated test suite (100% offline)
│       ├── mock_data.py           # Deterministic test fixtures and scenarios
│       ├── test_ai_analyzer.py    # Unit tests for AI engine and validation
│       └── test_backend_integration.py # Integration tests for backend API
├── docs/                          # Detailed project documentation
│   ├── ARCHITECTURE.md            # System architecture and lifecycle
│   ├── API.md                     # Endpoint specifications and schemas
│   ├── AI_PIPELINE.md             # Evidence validation, deduplication, and providers
│   ├── DEVELOPMENT.md             # Developer guide and contributing standards
│   └── DEMO.md                    # Repeatable hackathon demonstration guide
└── frontend/                      # React SPA
    ├── package.json               # Node dependencies
    ├── vite.config.js             # Vite configuration with API proxy
    ├── index.html                 # HTML entrypoint
    ├── src/
    │   ├── api.js                 # Backend API client functions
    │   ├── App.jsx                # Main application component
    │   ├── index.css              # Styling, theme tokens, layout
    │   └── main.jsx               # React DOM bootstrap
    └── dist/                      # Production build assets (served by FastAPI)
```

---

## Documentation Index

- [Architecture & Design](docs/ARCHITECTURE.md)
- [API Reference](docs/API.md)
- [AI Pipeline & Evidence Validation](docs/AI_PIPELINE.md)
- [Developer Guide](docs/DEVELOPMENT.md)
- [Demo Script](docs/DEMO.md)
