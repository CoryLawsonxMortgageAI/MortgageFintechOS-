"""LLM Client — Multi-provider free model integration.

Connects MortgageFintechOS agents to free LLM providers for intelligent
code generation, analysis, and decision-making. Supports automatic
failover between providers.

Supported Free Providers:
1. Groq (Primary) — Llama 3.3 70B, fastest inference, free tier
2. Google Gemini (Secondary) — Gemini 2.0 Flash, free tier, great for code
3. Together AI (Tertiary) — Llama 3.1 70B, free credits on signup
"""

from typing import Any

import aiohttp
import structlog

logger = structlog.get_logger()


class LLMClient:
    """Multi-provider LLM client with automatic failover."""

    def __init__(
        self,
        groq_api_key: str = "",
        groq_model: str = "llama-3.3-70b-versatile",
        google_api_key: str = "",
        google_model: str = "gemini-2.0-flash",
        together_api_key: str = "",
        together_model: str = "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
    ):
        self._providers: list[dict[str, Any]] = []
        self._log = logger.bind(component="llm_client")
        self._total_requests: int = 0
        self._total_tokens: int = 0

        # Register providers in priority order
        if groq_api_key:
            self._providers.append({
                "name": "groq",
                "api_key": groq_api_key,
                "model": groq_model,
                "base_url": "https://api.groq.com/openai/v1/chat/completions",
                "auth_header": "Bearer",
            })

        if google_api_key:
            self._providers.append({
                "name": "google",
                "api_key": google_api_key,
                "model": google_model,
                "base_url": f"https://generativelanguage.googleapis.com/v1beta/models/{google_model}:generateContent",
                "auth_header": "x-goog-api-key",
            })

        if together_api_key:
            self._providers.append({
                "name": "together",
                "api_key": together_api_key,
                "model": together_model,
                "base_url": "https://api.together.xyz/v1/chat/completions",
                "auth_header": "Bearer",
            })

    @property
    def available(self) -> bool:
        return len(self._providers) > 0

    async def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        """Send a completion request with automatic failover between providers."""
        if not self._providers:
            return {"content": "", "error": "No LLM providers configured", "provider": "none"}

        for provider in self._providers:
            try:
                result = await self._call_provider(provider, prompt, system_prompt, max_tokens, temperature)
                self._total_requests += 1
                return result
            except Exception as e:
                self._log.warning("llm_provider_failed", provider=provider["name"], error=str(e))
                continue

        return {"content": "", "error": "All LLM providers failed", "provider": "none"}

    async def _call_provider(
        self,
        provider: dict[str, Any],
        prompt: str,
        system_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> dict[str, Any]:
        """Call a specific LLM provider."""
        name = provider["name"]

        if name == "google":
            return await self._call_google(provider, prompt, system_prompt, max_tokens, temperature)
        else:
            # OpenAI-compatible API (Groq, Together)
            return await self._call_openai_compatible(provider, prompt, system_prompt, max_tokens, temperature)

    async def _call_openai_compatible(
        self,
        provider: dict[str, Any],
        prompt: str,
        system_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> dict[str, Any]:
        """Call OpenAI-compatible API (Groq, Together)."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"{provider['auth_header']} {provider['api_key']}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": provider["model"],
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(provider["base_url"], json=payload, headers=headers) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    raise RuntimeError(f"{provider['name']} API error {resp.status}: {error[:200]}")

                data = await resp.json()
                content = data["choices"][0]["message"]["content"]
                tokens = data.get("usage", {}).get("total_tokens", 0)
                self._total_tokens += tokens

                self._log.info("llm_completion", provider=provider["name"], tokens=tokens)
                return {
                    "content": content,
                    "provider": provider["name"],
                    "model": provider["model"],
                    "tokens": tokens,
                }

    async def _call_google(
        self,
        provider: dict[str, Any],
        prompt: str,
        system_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> dict[str, Any]:
        """Call Google Gemini API."""
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": provider["api_key"],
        }

        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{provider['model']}:generateContent"

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    raise RuntimeError(f"Google API error {resp.status}: {error[:200]}")

                data = await resp.json()
                content = data["candidates"][0]["content"]["parts"][0]["text"]

                self._log.info("llm_completion", provider="google", model=provider["model"])
                return {
                    "content": content,
                    "provider": "google",
                    "model": provider["model"],
                    "tokens": 0,
                }

    def get_status(self) -> dict[str, Any]:
        return {
            "providers": [p["name"] for p in self._providers],
            "total_requests": self._total_requests,
            "total_tokens": self._total_tokens,
            "available": self.available,
        }
