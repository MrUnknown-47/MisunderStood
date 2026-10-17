"""Live API Validation Runner for MISUNDERSTOOD.

Executes controlled live scenarios against the real provider (Gemini or OpenRouter):
  - Scenario A: Genuine scope difference (phone login vs email only)
  - Scenario B: Complementary requirements (mobile responsive vs accessibility)
  - Scenario C: Vague responses (make it good vs finish everything)

Security: Never prints or logs API keys or credentials.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.ai import LLMClient, analyze_interpretations


SCENARIOS = {
    "A": {
        "name": "Scenario A: Genuine Scope Difference",
        "description": "Tests detection of differing feature expectations (phone login vs email only).",
        "task": {
            "title": "Prepare the application for launch",
            "description": "Complete essential authentication functionality before release.",
        },
        "participants": [
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
        ],
    },
    "B": {
        "name": "Scenario B: Complementary Requirements",
        "description": "Tests recognition of compatible, non-competing requirements.",
        "task": {
            "title": "Prepare user interface for launch",
            "description": "Ensure UI quality standards are met before release.",
        },
        "participants": [
            {
                "participant_id": "participant-a",
                "interpretation": "The interface should be mobile responsive.",
            },
            {
                "participant_id": "participant-b",
                "interpretation": "The interface should have accessible text and controls.",
            },
        ],
    },
    "C": {
        "name": "Scenario C: Vague Responses",
        "description": "Tests handling of insufficiently specified inputs without manufacturing fake issues.",
        "task": {
            "title": "Launch the app",
            "description": "Do the launch work.",
        },
        "participants": [
            {
                "participant_id": "participant-a",
                "interpretation": "Make it good.",
            },
            {
                "participant_id": "participant-b",
                "interpretation": "Finish everything.",
            },
        ],
    },
}


async def run_scenario(key: str, client: LLMClient) -> None:
    scenario = SCENARIOS[key]
    print(f"\n{'='*70}")
    print(f"RUNNING: {scenario['name']}")
    print(f"Goal: {scenario['description']}")
    print(f"Provider: {client.provider} | Model: {client.model}")
    print(f"{'='*70}")

    result = await analyze_interpretations(
        scenario["task"], scenario["participants"], client=client
    )

    print(f"Status: {result['status']}")
    print(f"Summary: {result['summary']}")
    print(f"Issues Detected: {result['issue_counts']['total']}")

    if result["issues"]:
        for i, iss in enumerate(result["issues"], 1):
            print(f"\n  [Issue #{i}] {iss['title']} ({iss['type']})")
            print(f"    Priority: {iss['priority']} | Confidence: {iss['confidence']}")
            print(f"    Clarification: {iss['clarification_question']}")
            print(f"    Verified Evidence:")
            for ev in iss["evidence"]:
                print(f"      - {ev['participant_id']} ({ev['source_field']}): \"{ev['quote']}\"")

    if result["complementary_perspectives"]:
        print(f"\n  Complementary Perspectives ({len(result['complementary_perspectives'])}):")
        for i, comp in enumerate(result["complementary_perspectives"], 1):
            print(f"    [{i}] {comp['title']}")
            print(f"        {comp['description']}")
            for ev in comp["evidence"]:
                print(f"        - {ev['participant_id']}: \"{ev['quote']}\"")

    print(f"\nMetadata: {result['metadata']}")


async def main():
    parser = argparse.ArgumentParser(
        description="Run live MISUNDERSTOOD API validation scenarios."
    )
    parser.add_argument(
        "--scenario",
        choices=["A", "B", "C", "all"],
        default="A",
        help="Which scenario to execute (A, B, C, or all). Default is A.",
    )
    parser.add_argument(
        "--provider",
        choices=["auto", "gemini", "openrouter", "openai"],
        default="auto",
        help="Which provider to use (gemini, openrouter, openai, auto). Default is auto.",
    )
    args = parser.parse_args()

    client = LLMClient(provider=args.provider)
    if not client.api_key:
        print(
            f"ERROR: No API key found for provider '{client.provider}'. "
            "Please check your .env configuration.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Active Provider: {client.provider} ({client.model})")
    print("Credentials detected safely. Starting live validation...\n")

    if args.scenario == "all":
        for k in ["A", "B", "C"]:
            await run_scenario(k, client)
    else:
        await run_scenario(args.scenario, client)

    print(f"\n{'='*70}")
    print("LIVE VALIDATION RUN FINISHED.")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    asyncio.run(main())
