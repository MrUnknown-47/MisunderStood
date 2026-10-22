"""LLM Provider Client for MISUNDERSTOOD.

Supports multiple AI providers with automatic detection:
1. Google Gemini (direct via google-genai SDK) - fastest, native structured JSON.
2. OpenRouter (OpenAI-compatible HTTP endpoint) - broad multi-model support.
3. OpenAI (direct OpenAI HTTP endpoint).

Handles resilient async execution, timeout bounds, controlled token budgets,
safe credential sanitization, and structured JSON parsing.
"""

import asyncio
import json
import os
import re
from typing import Any, Optional
import httpx

# Automatically load .env if available
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


# ============================================================================
# Exception Hierarchy
# ============================================================================


class AIClientError(Exception):
    """Base exception for AI client failures."""

    pass


class AIAuthError(AIClientError):
    """Missing or invalid API credentials."""

    pass


class AIProviderTimeoutError(AIClientError):
    """Provider request timed out."""

    pass


class AIProviderError(AIClientError):
    """Provider returned an error (HTTP error, rate limit, quota, etc.)."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class AIMalformedJSONError(AIClientError):
    """Model output could not be parsed as valid JSON."""

    pass


# ============================================================================
# Helper: Robust JSON Extraction
# ============================================================================


def extract_json_from_text(text: str) -> dict[str, Any]:
    """Extract and parse a JSON object from text that may contain markdown code fences

    or surrounding commentary.
    """
    if not text or not text.strip():
        raise AIMalformedJSONError("Model returned empty or whitespace-only response.")

    cleaned = text.strip()

    # 1. Direct parse attempt
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # 2. Extract from markdown code fences: ```json ... ``` or ``` ... ```
    fence_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    match = re.search(fence_pattern, cleaned)
    if match:
        fenced_content = match.group(1).strip()
        try:
            data = json.loads(fenced_content)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    # 3. Find outermost curly braces { ... }
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        brace_content = cleaned[first_brace : last_brace + 1]
        try:
            data = json.loads(brace_content)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    raise AIMalformedJSONError("Failed to extract valid JSON object from model response.")


# ============================================================================
# LLM Client Implementation (Multi-Provider)
# ============================================================================


class LLMClient:
    """Async client supporting Gemini, OpenRouter, and OpenAI providers."""

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
    ):
        # Resolve provider
        chosen_provider = (
            provider or os.environ.get("AI_PROVIDER", "auto")
        ).lower()

        # Token limit configuration
        env_max_tokens = os.environ.get("AI_MAX_TOKENS")
        self.max_tokens = (
            int(env_max_tokens)
            if env_max_tokens and env_max_tokens.isdigit()
            else (max_tokens or 3000)
        )

        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

        # Resolve provider & credentials
        gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get(
            "GOOGLE_API_KEY"
        )
        openrouter_key = os.environ.get("OPENROUTER_API_KEY")
        openai_key = os.environ.get("OPENAI_API_KEY")

        env_model = os.environ.get("AI_MODEL")
        clean_env_model = env_model.strip() if env_model and env_model.strip() else None

        self.is_auto = (chosen_provider == "auto")

        if self.is_auto:
            # Documented preference chain: gemini -> openrouter -> openai
            if gemini_key:
                self.provider = "gemini"
                self.api_key = api_key or gemini_key
                self.model = model or clean_env_model or "gemini-2.5-flash"
            elif openrouter_key:
                self.provider = "openrouter"
                self.api_key = api_key or openrouter_key
                self.model = model or clean_env_model or "google/gemini-2.5-flash"
            elif openai_key:
                self.provider = "openai"
                self.api_key = api_key or openai_key
                self.model = model or clean_env_model or "gpt-4o-mini"
            else:
                self.provider = "none"
                self.api_key = ""
                self.model = model or "none"
        else:
            self.provider = chosen_provider
            if self.provider == "gemini":
                self.api_key = api_key or gemini_key or ""
                self.model = model or clean_env_model or "gemini-2.5-flash"
            elif self.provider == "openrouter":
                self.api_key = api_key or openrouter_key or ""
                self.model = model or clean_env_model or "google/gemini-2.5-flash"
            elif self.provider == "openai":
                self.api_key = api_key or openai_key or ""
                self.model = model or clean_env_model or "gpt-4o-mini"
            else:
                self.api_key = api_key or ""
                self.model = model or clean_env_model or "default"

    async def generate_structured_json(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        """Dispatch to configured provider.

        If provider was explicitly selected (e.g. AI_PROVIDER=gemini), it will NEVER
        silently switch providers on failure.
        If provider is 'auto', it follows the preference chain (gemini -> openrouter -> openai)
        and falls back to subsequent configured providers if the primary fails.
        """
        if not self.is_auto:
            # Strict explicit provider mode: no fallback
            if not self.api_key:
                raise AIAuthError(
                    f"No API key configured for explicit provider '{self.provider}'. "
                    f"Please set {self.provider.upper()}_API_KEY."
                )
            return await self._dispatch_provider(
                self.provider, self.api_key, self.model, system_prompt, user_prompt
            )

        # Automatic mode: build available fallback chain in preference order
        gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        openrouter_key = os.environ.get("OPENROUTER_API_KEY")
        openai_key = os.environ.get("OPENAI_API_KEY")

        env_model = os.environ.get("AI_MODEL")
        clean_env_model = env_model.strip() if env_model and env_model.strip() else None

        candidates: list[tuple[str, str, str]] = []
        if gemini_key:
            candidates.append(("gemini", gemini_key, clean_env_model or "gemini-2.5-flash"))
        if openrouter_key:
            candidates.append(("openrouter", openrouter_key, clean_env_model or "google/gemini-2.5-flash"))
        if openai_key:
            candidates.append(("openai", openai_key, clean_env_model or "gpt-4o-mini"))

        if not candidates:
            raise AIAuthError(
                "No API key configured for automatic provider selection. "
                "Please configure GEMINI_API_KEY, OPENROUTER_API_KEY, or OPENAI_API_KEY."
            )

        last_error: Optional[Exception] = None
        for prov, key, mod in candidates:
            try:
                result = await self._dispatch_provider(prov, key, mod, system_prompt, user_prompt)
                # Update client state to reflect the successful provider
                self.provider = prov
                self.model = mod
                self.api_key = key
                return result
            except (
                AIProviderError,
                AIProviderTimeoutError,
                AIAuthError,
                AIMalformedJSONError,
            ) as exc:
                last_error = exc
                # Try next candidate in the preference chain
                continue

        if last_error:
            raise last_error

        raise AIProviderError("All available AI providers failed under automatic resolution.")

    async def _dispatch_provider(
        self,
        provider: str,
        api_key: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        """Dispatch a single structured JSON request to a specific provider."""
        if provider == "gemini":
            return await self._call_gemini_direct(api_key, model, system_prompt, user_prompt)
        elif provider == "openrouter":
            return await self._call_openrouter_direct(api_key, model, system_prompt, user_prompt)
        elif provider == "openai":
            return await self._call_openai_direct(api_key, model, system_prompt, user_prompt)
        else:
            raise AIProviderError(f"Unsupported AI provider: '{provider}'")

    # -------------------------------------------------------------------------
    # Direct Gemini Provider (via google.genai SDK)
    # -------------------------------------------------------------------------
    async def _call_gemini_direct(
        self, api_key: str, model: str, system_prompt: str, user_prompt: str
    ) -> dict[str, Any]:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise AIProviderError(
                "google-genai package is not installed."
            ) from exc

        client = genai.Client(api_key=api_key)
        full_contents = f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\nUSER REQUEST:\n{user_prompt}"

        last_exception: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                response = await asyncio.wait_for(
                    client.aio.models.generate_content(
                        model=model,
                        contents=full_contents,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.1,
                            max_output_tokens=self.max_tokens,
                        ),
                    ),
                    timeout=self.timeout_seconds,
                )

                if not response.text:
                    raise AIProviderError("Gemini returned empty response text.")

                return extract_json_from_text(response.text)

            except asyncio.TimeoutError as exc:
                last_exception = AIProviderTimeoutError(
                    f"Gemini request timed out after {self.timeout_seconds}s."
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(1.0)
                    continue
                raise last_exception from exc

            except Exception as exc:
                err_str = str(exc).lower()
                # Permanent auth / quota errors: do NOT retry
                if "api_key" in err_str or "unauthenticated" in err_str:
                    raise AIAuthError("Gemini authentication failed: invalid API key.") from exc
                if "quota" in err_str or "resource_exhausted" in err_str or "credit" in err_str:
                    raise AIProviderError("Gemini quota or credit limit reached.", status_code=429) from exc

                last_exception = AIProviderError(f"Gemini API error: {type(exc).__name__}")
                if attempt < self.max_retries:
                    await asyncio.sleep(1.0 * (2**attempt))
                    continue
                raise last_exception from exc

        if last_exception:
            raise last_exception
        raise AIProviderError("Unknown Gemini failure.")

    # -------------------------------------------------------------------------
    # OpenRouter Provider (via httpx)
    # -------------------------------------------------------------------------
    async def _call_openrouter_direct(
        self, api_key: str, model: str, system_prompt: str, user_prompt: str
    ) -> dict[str, Any]:
        base_url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-Title": "MISUNDERSTOOD",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": self.max_tokens,
            "temperature": 0.1,
        }
        return await self._call_http_openai_compatible(base_url, headers, payload)

    # -------------------------------------------------------------------------
    # OpenAI Provider (via httpx)
    # -------------------------------------------------------------------------
    async def _call_openai_direct(
        self, api_key: str, model: str, system_prompt: str, user_prompt: str
    ) -> dict[str, Any]:
        base_url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": self.max_tokens,
            "temperature": 0.1,
        }
        return await self._call_http_openai_compatible(base_url, headers, payload)

    # -------------------------------------------------------------------------
    # Shared HTTP Helper
    # -------------------------------------------------------------------------
    async def _call_http_openai_compatible(
        self, base_url: str, headers: dict, payload: dict
    ) -> dict[str, Any]:
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(self.timeout_seconds)
                ) as client:
                    response = await client.post(
                        base_url,
                        headers=headers,
                        json=payload,
                    )

                if response.status_code == 200:
                    resp_json = response.json()
                    choices = resp_json.get("choices", [])
                    if not choices:
                        raise AIProviderError("Provider returned empty choices array.")
                    message_content = choices[0].get("message", {}).get(
                        "content", ""
                    )
                    return extract_json_from_text(message_content)

                status = response.status_code
                if status in (400, 401, 402, 403, 422):
                    sanitized_msg = (
                        "Authentication failed"
                        if status == 401
                        else (
                            "Credit limit reached"
                            if status == 402
                            else (
                                "Forbidden access"
                                if status == 403
                                else f"Client error (HTTP {status})"
                            )
                        )
                    )
                    raise AIProviderError(
                        f"AI provider rejected request: {sanitized_msg}",
                        status_code=status,
                    )

                if status == 429:
                    resp_lower = response.text.lower()
                    if "quota" in resp_lower or "credit" in resp_lower or "billing" in resp_lower:
                        raise AIProviderError(
                            "AI provider credit or quota exhausted.",
                            status_code=429,
                        )

                if status in (429, 500, 502, 503, 504):
                    last_exception = AIProviderError(
                        f"Transient provider error (HTTP {status})",
                        status_code=status,
                    )
                    if attempt < self.max_retries:
                        await asyncio.sleep(1.0 * (2**attempt))
                        continue
                    raise last_exception

                raise AIProviderError(
                    f"Unexpected HTTP status {status} from provider.",
                    status_code=status,
                )

            except httpx.TimeoutException as exc:
                last_exception = AIProviderTimeoutError(
                    f"AI provider request timed out after {self.timeout_seconds}s."
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(1.0)
                    continue
                raise last_exception from exc

            except httpx.RequestError as exc:
                last_exception = AIProviderError(
                    f"Network error contacting AI provider: {type(exc).__name__}"
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(1.0)
                    continue
                raise last_exception from exc

        if last_exception:
            raise last_exception
        raise AIProviderError("Unknown provider failure.")
