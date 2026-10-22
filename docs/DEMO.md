# MISUNDERSTOOD: Repeatable Demo Walkthrough

This guide provides a step-by-step demonstration script for presenters showcasing MISUNDERSTOOD during evaluations, hackathon judging, or team walkthroughs.

---

## Demo Summary & Narrative

- **Scenario**: A software team receives the instruction: *"Prepare the application for launch"*.
- **The Gap**:
  - The **Developer** assumes launch means finishing backend email/password authentication.
  - The **Project Manager** assumes launch requires phone login, user registration, and self-service password recovery.
  - The **Designer** assumes launch requires an onboarding walkthrough and mobile responsiveness.
- **The Outcome**: MISUNDERSTOOD highlights the scope differences, guides team resolution with actionable questions, builds a confirmed agreement, and demonstrates a **100% bridged consensus** via the Bridge Test.

---

## Step-by-Step Walkthrough

### Step 1: Launch Application
Start the unified server:
```bash
python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
Open [http://localhost:8000](http://localhost:8000) in your browser.

---

### Step 2: Load the Official 3-Party Scenario
On the home screen:
1. Notice the **Preset Scenario** card at the bottom.
2. Click **"Load Official 3-Party Demo"**.
3. The platform automatically:
   - Creates the session: *"Prepare the application for launch"*.
   - Populates submissions for Alex (Lead Developer), Jordan (Project Manager), and Taylor (Product Designer).
   - Generates a unique 6-character session code (e.g., `WLCJLN`).

---

### Step 3: Inspect Blind Submissions
Observe the submissions interface:
- **Blind Submission Protocol**: Notice that each participant has submitted their interpretation, assumptions, and success criteria independently.
- The UI indicates that **3 participants** have joined and the pre-analysis threshold (>= 2 submissions) is satisfied.

---

### Step 4: Run AI Analysis
1. Click **"Run AI Analysis"**.
2. An animated indicator appears while the AI engine:
   - Proposes candidate discrepancies.
   - Deterministically verifies verbatim quotations against participant submissions.
   - Deduplicates restatements.
3. The **Misunderstanding Map** renders on the right side of the screen.

---

### Step 5: Review Evidence-Backed Findings
Examine the detected issues:
1. **Scope Difference (High Priority)**:
   - Discrepancy between email-only login vs. phone login, registration, and self-service recovery.
   - Click **"Evidence (2)"** to view exact verbatim quotations cited directly from Alex's and Jordan's submissions.
   - Notice the **Clarification Question**:
     *"Should phone login and self-service password recovery be included in the launch release?"*
2. **Complementary Perspective**:
   - Notice that Taylor's requirement for mobile responsiveness and onboarding is recognized as a compatible need rather than a conflict.

---

### Step 6: Resolve and Dismiss Issues
Walk through the team resolution process:

1. **Resolve Authentication Scope**:
   - On the login scope difference issue, click **"Resolve"**.
   - In the input field, document the agreed decision:
     ```text
     Email and password auth included in v1. Phone login and recovery deferred to v2.
     ```
   - Click **"Save Resolution"**.
   - Notice the issue badge changes to **Resolved** and the agreed decision is displayed.

2. **Handle Secondary Findings (if any)**:
   - For non-blocking secondary differences, click **"Dismiss"** to record them as out of scope.

---

### Step 7: Confirm Agreement & Inspect The Bridge Test
Scroll down to the **Shared Confirmed Agreement** and **The Bridge Test** widget:

1. **Checklist Compilation**:
   - The agreed requirements now include:
     - Core Deliverable: *Prepare the application for launch*
     - Agreed resolution notes from Step 6.
     - Complementary alignments (mobile responsiveness).
   - Excluded items list any dismissed findings.

2. **Participant Confirmation**:
   - In the confirmation input, enter `participant-a` and click **"Confirm"**.
   - Enter `participant-b` and click **"Confirm"**.
   - Enter `participant-c` and click **"Confirm"**.
   - The badge updates to **Confirmed**.

3. **The Bridge Test Results**:
   - **Detected Gaps**: 1–3 (depending on provider heuristics).
   - **Open Gaps**: `0`.
   - **Resolution Percentage**: `100.0%`.
   - **Bridge Status**: `BRIDGED`.

---

## Expected Outcome Summary

| Metric | Before Analysis | After Analysis | After Resolution & Sign-Off |
| :--- | :--- | :--- | :--- |
| **Session Status** | `collecting` | `completed` | `completed` |
| **Open Issues** | `0` (hidden) | Identified by AI | `0` |
| **Agreement Status** | Uncompiled | Pending confirmation | `Confirmed` (`is_fully_confirmed = true`) |
| **Bridge Test Status** | `unresolved` | `in_progress` | `bridged` (100% resolution rate) |

> **Note on LLM Output**: When using live LLM providers, exact issue titles and clarification question phrasing may vary slightly across runs due to non-deterministic model sampling. However, the deterministic evidence verification rules and resolution workflow operate identically in every execution.
