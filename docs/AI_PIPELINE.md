# MISUNDERSTOOD: AI Analysis & Evidence Pipeline

This document details how participant interpretations enter the AI pipeline, how deterministic verification eliminates fabricated findings, how deduplication operates, and how multi-provider fallback is configured.

---

## 1. Pipeline Overview

```
Input: Task & Participant Submissions
               │
               ▼
   [1. Input Validation & Short-Circuits]
      - Validates Pydantic schemas (TaskInput, ParticipantInput)
      - Count < 2: returns status='insufficient_data'
      - Identical inputs: returns status='completed' with clean consensus
               │
               ▼
   [2. Prompt Construction & LLM Inference]
      - System Prompt (role as neutral mediator, zero decision-making)
      - User Prompt (verbatim participant submissions)
      - Dispatches to Gemini / OpenRouter / OpenAI
               │
               ▼
   [3. JSON Extraction & Candidate Parsing]
      - Parses raw text, strips markdown code fences, extracts JSON
      - Validates candidates against Issue and ComplementaryPerspective schemas
               │
               ▼
   [4. Deterministic Evidence Validation]
      - Verifies participant IDs against submitted records
      - Verifies exact contiguous string slices in original text
      - Enforces multi-participant citations for contradictions/scope differences
      - Discards unverified quotes; drops issues lacking verified evidence
               │
               ▼
   [5. Deterministic Deduplication]
      - Suppresses generic umbrella issues when specific findings exist
      - Deduplicates overlapping restatements using Jaccard and keyword subsets
      - Preserves distinct clarification decisions sharing evidence
               │
               ▼
   [6. Fail-Safe Quality Guard]
      - If candidate findings were proposed but all were rejected by evidence rules,
        returns status='failed' rather than falsely communicating consensus
               │
               ▼
Output: Validated AnalysisResult Dictionary
```

> **Important**: The LLM acts strictly as a **heuristic proposer**. It is not assumed to be hallucination-proof. The deterministic validation layer in Python enforces evidence constraints on all model outputs before they are accepted.

---

## 2. Supported Issue Types

Every verified finding is classified under one of four issue types (`backend/ai/schemas.py`):

| Issue Type | Description | Evidence Rule |
| :--- | :--- | :--- |
| `scope_difference` | Divergence in the expected scope, boundary, or deliverables of the task. | **Must cite >= 2 distinct participants.** |
| `contradiction` | Direct conflict where satisfying one interpretation prevents satisfying another. | **Must cite >= 2 distinct participants.** |
| `unconfirmed_assumption` | An unverified constraint, technology, or precondition stated by one party. | Cites the participant stating the assumption. |
| `omission` | A critical aspect left undefined or completely omitted in interpretations. | Cites the participant whose statement reveals the gap. |

### Vague Inputs Policy
Inputs such as *"Make it good"* or *"Finish everything"* are insufficiently specified. The system does not invent artificial contradictions or omissions. Instead, the AI prompt instructs the mediator to return an unconfirmed finding or a clarification question acknowledging that the task requires further definition, returning zero issues if no specific misunderstanding is supported by evidence.

---

## 3. Evidence Validation Rules

Implemented in `backend/ai/validator.py`:

1. **Exact Contiguous Excerpts**: Every quote in `evidence` must be an exact, contiguous substring of the referenced participant's text.
2. **Search Priority Order**:
   - `interpretation`
   - `assumptions`
   - `success_criteria`
3. **Whitespace Normalization**: Collapses multiple whitespace characters and trims boundaries (`" ".join(text.split())`). No fuzzy, phonetic, or semantic approximation is permitted.
4. **Casing Recovery**: The validator extracts the exact case-preserved slice from the participant's original normalized submission.
5. **No Silent Rewriting**: Unmatched quotes are dropped. If an issue has no remaining verified quotes, the entire issue is rejected.
6. **Multi-Participant Citations**: For `scope_difference` and `contradiction`, the validator checks that the verified quotes belong to at least 2 distinct participant IDs. If only 1 participant is cited, the issue is rejected.

---

## 4. Deterministic Issue Deduplication

LLMs frequently generate multiple issues that ask the same fundamental question using different phrasing. The deduplication algorithm runs purely in Python without external embedding APIs:

### 1. Generic Umbrella Suppression
Findings whose titles and clarification questions contain only generic scoping terms (e.g., *login*, *auth*, *requirements*, *application*, *launch*) are classified as umbrella issues. If more specific findings exist (e.g., *phone login scope*), umbrella issues are pruned regardless of output ordering.

### 2. Lexical & Subset Overlap Detection
- Extracts domain decision keywords by removing stopwords and normalising synonyms (e.g., `signin` → `login`, `signup` → `registration`, `reset` → `recovery`).
- Calculates Jaccard similarity between candidate and existing clarification questions. If Jaccard >= 0.50 or candidate specific tokens form a subset of existing specific tokens, the candidate is discarded as a restatement.
- Calculates title token overlap (Jaccard >= 0.65).

### 3. Distinct Decision Preservation
Findings that share evidence but require different decisions are preserved. For example:
- *Phone login scope* (Decision: Support SMS auth or email only?)
- *Password recovery scope* (Decision: Build self-service reset or rely on support tickets?)

Both are retained even if they cite the same sentence from Participant B.

---

## 5. Priority and Confidence Fields

### Priority Levels
- `critical`: Foundational architectural disagreements or blocking contradictions that prevent work from starting or cause major data/system incompatibility.
- `high`: Significant scope or feature differences that directly impact the release timeline or external user experience.
- `medium`: Unconfirmed secondary requirements, edge-case handling, or unverified technical assumptions.
- `low`: Minor styling, naming, or cosmetic differences.

Priority calibration reflects the cost of leaving the question unaddressed, with uncertainty leaning toward lower priority rather than false alarms.

### Confidence Scores
- Float between `0.0` and `1.0`.
- Represents the degree to which the verbatim evidence directly demonstrates the discrepancy.

---

## 6. Complementary Perspectives

Differences between participants are not always misunderstandings. When participants highlight compatible, non-conflicting needs (such as a developer focusing on authentication while a designer focuses on mobile responsiveness), these are categorized as `complementary_perspectives`.

Complementary perspectives:
- Must also cite verified verbatim evidence.
- Are not counted as issues in the Misunderstanding Map.
- Are automatically included in the compiled Shared Agreement checklist.

---

## 7. Provider Configuration & Fallback

The LLM client (`backend/ai/client.py`) supports three providers:

| Provider | Client Driver | Default Model | Token Cap |
| :--- | :--- | :--- | :--- |
| **Gemini** | `google-genai` SDK | `gemini-2.5-flash` | Configurable (`AI_MAX_TOKENS`, default 3000) |
| **OpenRouter** | HTTPX AsyncClient | `google/gemini-2.5-flash` | Configurable (`AI_MAX_TOKENS`, default 3000) |
| **OpenAI** | HTTPX AsyncClient | `gpt-4o-mini` | Configurable (`AI_MAX_TOKENS`, default 3000) |

### Provider Modes

#### 1. Explicit Mode (`AI_PROVIDER=gemini|openrouter|openai`)
- Directly uses the specified provider.
- Never silently switches providers on failure. If the selected provider errors, it raises an explicit exception.

#### 2. Automatic Mode (`AI_PROVIDER=auto`)
- Resolves available API keys in order of preference:
  `Gemini → OpenRouter → OpenAI`
- If the primary provider fails due to an **eligible fallback error**, it automatically attempts the next configured provider.
- Eligible errors for fallback:
  - Authentication / invalid API key (`401`, `403`)
  - Quota exhausted or rate limits (`429`)
  - Network timeouts
  - Provider internal errors (`500`, `502`, `503`, `504`)
  - Unparseable or malformed JSON responses

---

## 8. Verification & Testing

### Running Offline Tests
The test suite in `backend/tests/test_ai_analyzer.py` runs without internet access or real API keys using mock providers:

```bash
python3 -m pytest backend/tests/test_ai_analyzer.py -v
```

This verifies:
- Exact whitespace normalization and slice extraction.
- Rejection of fabricated quotes and invalid participant IDs.
- Contradiction rejection when fewer than 2 participants are cited.
- Required scenarios A through E (scope difference, complementary requirements, unconfirmed requirement, similar interpretations, insufficient evidence).
- Deduplication cases A through E.
- Fallback chain behavior and credential sanitization.

### Live API Testing (Optional)
To test against a live AI provider with real network calls:

1. Add your API key to `.env` (e.g. `GEMINI_API_KEY=...`).
2. Set `AI_PROVIDER=gemini` or `auto`.
3. Run a test script using `backend.ai.analyze_interpretations`:
   ```bash
   python3 -c "
   import asyncio
   from backend.ai import analyze_interpretations

   task = {'title': 'Prepare application for launch'}
   participants = [
       {'participant_id': 'dev', 'interpretation': 'Complete email and password login.'},
       {'participant_id': 'pm', 'interpretation': 'Complete email or phone login, registration, and password recovery.'}
   ]
   result = asyncio.run(analyze_interpretations(task, participants))
   print('Status:', result['status'])
   print('Issues found:', len(result['issues']))
   for iss in result['issues']:
       print('-', iss['title'], f'({iss[\"type\"]})')
   "
   ```
