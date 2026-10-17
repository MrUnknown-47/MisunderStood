"""Mock fixtures and test datasets for MISUNDERSTOOD AI testing.

Contains standard scenarios (A through E), edge cases, and mocked model responses.
"""

# ============================================================================
# Scenario A: Clear Scope Difference
# ============================================================================
SCENARIO_A_TASK = {
    "title": "Prepare the application for launch",
    "description": "Complete essential authentication functionality.",
}

SCENARIO_A_PARTICIPANTS = [
    {
        "participant_id": "participant-a",
        "interpretation": "Finish email and password login.",
    },
    {
        "participant_id": "participant-b",
        "interpretation": (
            "Finish email or phone login, registration, and password recovery."
        ),
    },
]

SCENARIO_A_MOCK_RESPONSE = {
    "summary": "Participants have diverging expectations regarding authentication scope for the launch.",
    "issues": [
        {
            "type": "scope_difference",
            "title": "Discrepancy in login methods and account features",
            "description": "Participant A expects only email and password login, while Participant B includes phone login, registration, and password recovery.",
            "evidence": [
                {
                    "participant_id": "participant-a",
                    "quote": "Finish email and password login.",
                },
                {
                    "participant_id": "participant-b",
                    "quote": "Finish email or phone login, registration, and password recovery.",
                },
            ],
            "impact": "Engineers may build differing authentication scopes leading to launch delays.",
            "priority": "high",
            "confidence": 0.95,
            "clarification_question": "Should phone login, registration, and password recovery be part of the initial launch milestone?",
        }
    ],
    "complementary_perspectives": [],
}


# ============================================================================
# Scenario B: Complementary Requirements
# ============================================================================
SCENARIO_B_TASK = {
    "title": "Prepare user interface for launch",
    "description": "Ensure UI quality standards are met.",
}

SCENARIO_B_PARTICIPANTS = [
    {
        "participant_id": "participant-a",
        "interpretation": "The interface should be mobile responsive.",
    },
    {
        "participant_id": "participant-b",
        "interpretation": "The interface should have accessible text and controls.",
    },
]

SCENARIO_B_MOCK_RESPONSE = {
    "summary": "Participants have complementary UI priorities: responsiveness and accessibility. These can proceed together.",
    "issues": [],
    "complementary_perspectives": [
        {
            "title": "Complementary focus on responsiveness and accessibility",
            "description": "Participant A focused on mobile responsiveness while Participant B focused on accessible controls. These are mutually supportive.",
            "evidence": [
                {
                    "participant_id": "participant-a",
                    "quote": "The interface should be mobile responsive.",
                },
                {
                    "participant_id": "participant-b",
                    "quote": "The interface should have accessible text and controls.",
                },
            ],
        }
    ],
}


# ============================================================================
# Scenario C: Unconfirmed Requirement
# ============================================================================
SCENARIO_C_TASK = {
    "title": "Implement onboarding pages",
    "description": "Deliver user onboarding pages.",
}

SCENARIO_C_PARTICIPANTS = [
    {
        "participant_id": "participant-a",
        "interpretation": "Build the registration page.",
    },
    {
        "participant_id": "participant-b",
        "interpretation": "Build registration and password recovery.",
    },
]

SCENARIO_C_MOCK_RESPONSE = {
    "summary": "Both participants agree on building registration, but password recovery was mentioned only by Participant B.",
    "issues": [
        {
            "type": "omission",
            "title": "Unconfirmed password recovery scope",
            "description": "Password recovery was mentioned by Participant B but unaddressed by Participant A. This is an unconfirmed scope item rather than a proven disagreement.",
            "evidence": [
                {
                    "participant_id": "participant-b",
                    "quote": "password recovery",
                }
            ],
            "impact": "Uncertainty about whether password recovery is expected for this release.",
            "priority": "medium",
            "confidence": 0.85,
            "clarification_question": "Should password recovery be included alongside the registration page in this release?",
        }
    ],
    "complementary_perspectives": [],
}


# ============================================================================
# Scenario D: Similar Interpretations (Consensus)
# ============================================================================
SCENARIO_D_TASK = {
    "title": "Setup user registration",
    "description": "Deliver user signup mechanism.",
}

SCENARIO_D_PARTICIPANTS = [
    {
        "participant_id": "participant-a",
        "interpretation": "Users must register with email and password.",
    },
    {
        "participant_id": "participant-b",
        "interpretation": "Users should create an account using their email and password.",
    },
]

SCENARIO_D_MOCK_RESPONSE = {
    "summary": "Participants share an aligned understanding: user account creation with email and password.",
    "issues": [],
    "complementary_perspectives": [],
}


# ============================================================================
# Scenario E: Insufficient Evidence (Vague)
# ============================================================================
SCENARIO_E_TASK = {
    "title": "Launch the app",
    "description": "Do the launch work.",
}

SCENARIO_E_PARTICIPANTS = [
    {
        "participant_id": "participant-a",
        "interpretation": "Make it good.",
    },
    {
        "participant_id": "participant-b",
        "interpretation": "Finish everything.",
    },
]

SCENARIO_E_MOCK_RESPONSE = {
    "summary": "Participant interpretations ('Make it good', 'Finish everything') are too high-level and vague to determine alignment or specific scope differences. Clarification question: What specific deliverables, feature boundaries, or acceptance criteria define completion for this task?",
    "issues": [],
    "complementary_perspectives": [],
}
