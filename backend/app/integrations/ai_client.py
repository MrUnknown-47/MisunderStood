import json
import logging
from typing import Protocol, List, Dict, Any
import httpx
from app.config import get_settings

logger = logging.getLogger("misunderstood.ai_client")
settings = get_settings()


class AIAnalysisProvider(Protocol):
    async def analyze_interpretations(
        self,
        task: Dict[str, Any],
        participants: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze task and submitted participant interpretations to identify misunderstandings."""
        ...


class MockAIClient:
    """Deterministic, robust mock AI client for development, demos, and testing."""

    async def analyze_interpretations(
        self,
        task: Dict[str, Any],
        participants: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        task_title = task.get("title", "")
        task_desc = task.get("description", "")
        
        # Prepare quotes from participants
        p_data = []
        for p in participants:
            p_id = str(p.get("participant_id", ""))
            text = p.get("interpretation", "")
            p_data.append((p_id, text))

        issues = []
        complementary = []

        # Analyze content dynamically or based on standard test cases
        all_text = " ".join(t for _, t in p_data).lower()

        # Check for authentication/login scope contradiction
        email_p = [pid for pid, txt in p_data if "email" in txt.lower()]
        phone_p = [pid for pid, txt in p_data if "phone" in txt.lower()]

        if email_p and phone_p:
            e_quote = next(txt for pid, txt in p_data if pid == email_p[0])
            p_quote = next(txt for pid, txt in p_data if pid == phone_p[0])
            issues.append({
                "type": "scope_difference",
                "title": "Conflicting login requirements",
                "description": "Participants disagree on whether login should support email only or phone number authentication.",
                "evidence": [
                    {"participant_id": email_p[0], "quote": e_quote},
                    {"participant_id": phone_p[0], "quote": p_quote}
                ],
                "priority": "high",
                "clarification_question": "Should the first release support email login only, or both email and phone login?"
            })

        # Check for password recovery unconfirmed assumption
        recovery_p = [pid for pid, txt in p_data if "password recovery" in txt.lower() or "password-reset" in txt.lower() or "recovery" in txt.lower()]
        if recovery_p and len(recovery_p) < len(p_data):
            rec_quote = next(txt for pid, txt in p_data if pid == recovery_p[0])
            issues.append({
                "type": "assumption",
                "title": "Unconfirmed password recovery requirement",
                "description": "One participant assumes password recovery is in scope, but others have not confirmed it.",
                "evidence": [
                    {"participant_id": recovery_p[0], "quote": rec_quote}
                ],
                "priority": "medium",
                "clarification_question": "Is password recovery an essential requirement for the first release?"
            })

        # Check for responsive design / mobile as complementary perspective
        mobile_p = [pid for pid, txt in p_data if "responsive" in txt.lower() or "mobile" in txt.lower()]
        if mobile_p:
            mob_quote = next(txt for pid, txt in p_data if pid == mobile_p[0])
            complementary.append({
                "title": "Mobile-responsive user experience",
                "description": "Participant highlighted interface responsiveness which complements the functional capabilities.",
                "evidence": [
                    {"participant_id": mobile_p[0], "quote": mob_quote}
                ]
            })

        # Fallback if no specific keyword triggered: generate meaningful baseline issue from first 2 participants
        if not issues and len(p_data) >= 2:
            p1_id, p1_txt = p_data[0]
            p2_id, p2_txt = p_data[1]
            issues.append({
                "type": "scope_difference",
                "title": "Interpretation alignment discrepancy",
                "description": "Participants articulated different core priorities for completing the task.",
                "evidence": [
                    {"participant_id": p1_id, "quote": p1_txt},
                    {"participant_id": p2_id, "quote": p2_txt}
                ],
                "priority": "medium",
                "clarification_question": f"Which primary deliverable should take precedence for '{task_title}'?"
            })

        return {
            "summary": f"Identified {len(issues)} potential gap(s) and {len(complementary)} complementary perspective(s).",
            "issues": issues,
            "complementary_perspectives": complementary
        }


class LiveAIClient:
    """Production LLM client utilizing Gemini / external provider via HTTP."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        self.api_key = api_key
        self.model = model

    async def analyze_interpretations(
        self,
        task: Dict[str, Any],
        participants: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if not self.api_key:
            logger.warning("AI_API_KEY is not set. Falling back to MockAIClient.")
            mock = MockAIClient()
            return await mock.analyze_interpretations(task, participants)

        system_instruction = (
            "You are the analysis engine for MISUNDERSTOOD, an AI tool that detects and resolves "
            "differences in interpretations of a shared task.\n"
            "Analyze the task and participant interpretations. Output valid JSON adhering to:\n"
            "{\n"
            "  \"summary\": \"string\",\n"
            "  \"issues\": [\n"
            "    {\n"
            "      \"type\": \"contradiction\" | \"assumption\" | \"omission\" | \"scope_difference\" | \"success_criteria_difference\",\n"
            "      \"title\": \"string\",\n"
            "      \"description\": \"string\",\n"
            "      \"evidence\": [{\"participant_id\": \"uuid\", \"quote\": \"exact quote\"}],\n"
            "      \"priority\": \"low\" | \"medium\" | \"high\",\n"
            "      \"clarification_question\": \"neutral targeted question\"\n"
            "    }\n"
            "  ],\n"
            "  \"complementary_perspectives\": [\n"
            "    {\"title\": \"string\", \"description\": \"string\", \"evidence\": [{\"participant_id\": \"uuid\", \"quote\": \"string\"}]}\n"
            "  ]\n"
            "}\n"
            "Rules: Quote exact phrases. Do not invent statements. Distinguish genuine contradictions from complementary ideas."
        )

        user_content = json.dumps({"task": task, "participants": participants}, indent=2)

        # Call Gemini API
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": system_instruction},
                        {"text": f"Here is the task and interpretations:\n{user_content}"}
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json"
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                logger.error(f"AI Provider error: {resp.status_code} - {resp.text}")
                raise RuntimeError(f"AI service returned error: {resp.status_code}")

            data = resp.json()
            try:
                text_content = data["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(text_content)
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                logger.error(f"Failed to parse AI response: {e}")
                raise ValueError("Malformed response from AI service.")


def get_ai_client() -> AIAnalysisProvider:
    """Return appropriate AI client based on configuration."""
    if settings.USE_MOCK_AI or not settings.AI_API_KEY:
        return MockAIClient()
    return LiveAIClient(api_key=settings.AI_API_KEY, model=settings.AI_MODEL)
