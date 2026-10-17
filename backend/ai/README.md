# MISUNDERSTOOD: AI/ML Analysis Module

> **Tagline:** "Same conversation. Different realities."  
> **Theme:** Bridge the Gap (Devlympics Hackathon)

The AI/ML component of MISUNDERSTOOD acts as an **objective mediator** that detects semantic divergences, scope discrepancies, and unconfirmed assumptions between team members when interpreting a shared task.

---

## 1. Public Module Contract

The primary entry point is:

```python
async def analyze_interpretations(
    task: dict,
    participants: list[dict],
    client: Optional[LLMClient] = None,
) -> dict:
```

### Input Parameters

```python
task = {
    "title": "Prepare the application for launch",
    "description": "Complete essential authentication functionality before release." # optional
}

participants = [
    {
        "participant_id": "participant-a",
        "interpretation": "Finish email and password login.",
        "assumptions": "PostgreSQL database will be used.", # optional
        "success_criteria": "Unit tests pass and auth API returns 200." # optional
    },
    {
        "participant_id": "participant-b",
        "interpretation": "Finish email or phone login, registration, and password recovery."
    }
]
```

### Output Schema

The function returns a pure JSON-serializable dictionary adhering to `AnalysisResult`:

```json
{
  "status": "completed",
  "summary": "Participants agree on core authentication, but disagree on whether phone login and password recovery are part of the initial launch milestone.",
  "issues": [
    {
      "type": "scope_difference",
      "title": "Scope of Authentication Functionality",
      "description": "Participant A expects only email/password login, while Participant B includes phone login and password recovery.",
      "evidence": [
        {
          "participant_id": "participant-a",
          "quote": "Finish email and password login.",
          "source_field": "interpretation"
        },
        {
          "participant_id": "participant-b",
          "quote": "Finish email or phone login, registration, and password recovery.",
          "source_field": "interpretation"
        }
      ],
      "impact": "Team members may build differing auth backends, causing launch blockers.",
      "priority": "high",
      "confidence": 0.95,
      "clarification_question": "Should phone login and password recovery be included in the initial launch milestone?"
    }
  ],
  "complementary_perspectives": [],
  "issue_counts": {
    "total": 1,
    "by_type": {
      "scope_difference": 1
    },
    "by_priority": {
      "high": 1
    }
  },
  "error_message": null,
  "metadata": {
    "model": "google/gemini-2.5-flash",
    "participant_count": 2,
    "unverified_quotes_dropped": 0,
    "rejected_issue_count": 0
  }
}
```

---

## 2. Status States

| `status` | Meaning | Next Action for Backend |
| :--- | :--- | :--- |
| `"completed"` | Analysis finished successfully. `issues` may contain 0 or more verified findings. | Render Misunderstanding Map / checklist. |
| `"insufficient_data"` | Less than 2 participants have submitted interpretations. Bypasses LLM. | Prompt remaining participants to submit. |
| `"failed"` | Provider error, timeout, or invalid inputs. `error_message` contains details. | Alert user / show retry button. Never masks as consensus! |

---

## 3. Evidence Integrity (Zero-Hallucination Guard)

Every finding returned by the model undergoes deterministic validation:
1. **Verbatim Quotation**: Quotes must be exact contiguous substrings from the participant's original text (normalized for whitespace).
2. **Participant Validation**: The referenced `participant_id` must exist in the input session.
3. **Multi-Participant Evidence**: For `contradiction` and `scope_difference` issues, verified evidence from at least **two distinct participants** is required. If evidence from one participant fails verification, the finding is dropped.
4. **No Rewriting**: Fabricated quotes are discarded, never silently altered.

---

## 4. Configuration & Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `AI_PROVIDER` | `auto` | Provider mode: `auto` (cascades `gemini` -> `openrouter` -> `openai`), or explicit `gemini`, `openrouter`, `openai`. |
| `GEMINI_API_KEY` | *(Optional)* | Google Gemini API key (supports `gemini-2.5-flash`). |
| `OPENROUTER_API_KEY` | *(Optional)* | OpenRouter Bearer API token. |
| `OPENAI_API_KEY` | *(Optional)* | OpenAI API key. |
| `AI_MODEL` | Provider default | Model override (e.g., `gemini-2.5-flash` or `google/gemini-2.5-flash`). |
| `AI_MAX_TOKENS` | `3000` | Max token budget per call. |

---

## 5. Running Automated Tests

All unit tests run **completely offline** without API keys or live network calls:

```bash
python3 -m pytest backend/tests/test_ai_analyzer.py -v
```

### Running Controlled Live Scenarios

To run live validation against any provider:

```bash
# Run all scenarios using auto provider resolution:
python3 backend/tests/run_live_scenarios.py --provider auto --scenario all

# Run specific provider (e.g. Gemini direct):
python3 backend/tests/run_live_scenarios.py --provider gemini --scenario all

# Or run individual scenarios (A: Scope difference, B: Complementary, C: Vague):
python3 backend/tests/run_live_scenarios.py --provider gemini --scenario A
python3 backend/tests/run_live_scenarios.py --provider openrouter --scenario B
python3 backend/tests/run_live_scenarios.py --provider auto --scenario C
```

---

## 6. Minimal Integration Example (FastAPI)

```python
from fastapi import FastAPI, HTTPException
from backend.ai import analyze_interpretations

app = FastAPI()

@app.post("/sessions/{session_id}/analyze")
async def trigger_analysis(session_id: str, payload: dict):
    # payload: {"task": {...}, "participants": [...]}
    task = payload.get("task")
    participants = payload.get("participants", [])
    
    result = await analyze_interpretations(task, participants)
    
    if result["status"] == "failed":
        raise HTTPException(status_code=502, detail=result["error_message"])
        
    return result
```
