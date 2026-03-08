"""Multi-LLM Agentic Router for MortgageFintechOS.

Routes agent requests to the optimal LLM based on task type, complexity,
and cost efficiency. Supports OpenAI, Anthropic (Claude), and OpenRouter
as providers with automatic fallback.

Architecture based on mixture-of-experts routing where each agent's task
type maps to the most capable model for that domain.
"""

import json
from datetime import datetime, timezone
from typing import Any

import aiohttp
import structlog

logger = structlog.get_logger()

# Model routing matrix — maps task categories to optimal models
# Based on benchmark research: coding → Claude/GPT-4, analysis → Claude,
# security → Claude, data → GPT-4, general → best available
MODEL_ROUTES: dict[str, dict[str, str]] = {
    "code_generation": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-6-20250514",
        "fallback_provider": "openrouter",
        "fallback_model": "anthropic/claude-sonnet-4-6",
    },
    "code_review": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-6-20250514",
        "fallback_provider": "openrouter",
        "fallback_model": "anthropic/claude-sonnet-4-6",
    },
    "security_analysis": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-6-20250514",
        "fallback_provider": "openrouter",
        "fallback_model": "anthropic/claude-sonnet-4-6",
    },
    "document_analysis": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-6-20250514",
        "fallback_provider": "openrouter",
        "fallback_model": "google/gemini-2.5-pro-preview",
    },
    "income_analysis": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-6-20250514",
        "fallback_provider": "openrouter",
        "fallback_model": "openai/gpt-4o",
    },
    "data_engineering": {
        "provider": "openrouter",
        "model": "openai/gpt-4o",
        "fallback_provider": "anthropic",
        "fallback_model": "claude-sonnet-4-6-20250514",
    },
    "codebase_analysis": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-6-20250514",
        "fallback_provider": "openrouter",
        "fallback_model": "openai/o3-mini",
    },
    "general": {
        "provider": "openrouter",
        "model": "anthropic/claude-sonnet-4-6",
        "fallback_provider": "openai",
        "fallback_model": "gpt-4o-mini",
    },
}

# Agent-to-task-category mapping
AGENT_TASK_ROUTES: dict[str, dict[str, str]] = {
    "ATLAS": {
        "generate_api": "code_generation",
        "build_feature": "code_generation",
        "run_migration": "code_generation",
        "scaffold_component": "code_generation",
    },
    "CIPHER": {
        "owasp_scan": "security_analysis",
        "compliance_check": "security_analysis",
        "encryption_audit": "security_analysis",
        "patch_vulnerability": "code_generation",
    },
    "FORGE": {
        "deploy": "code_generation",
        "rollback": "code_generation",
        "build_pipeline": "code_generation",
        "rotate_secrets": "security_analysis",
    },
    "NEXUS": {
        "review_pr": "code_review",
        "generate_tests": "code_generation",
        "analyze_debt": "code_review",
        "refactor": "code_generation",
    },
    "STORM": {
        "build_etl": "data_engineering",
        "hmda_report": "data_engineering",
        "uldd_export": "data_engineering",
        "optimize_query": "data_engineering",
    },
    "MARTIN": {
        "classify_document": "document_analysis",
        "validate_ocr": "document_analysis",
        "detect_fraud": "security_analysis",
        "audit_completeness": "document_analysis",
        "run_document_audit": "document_analysis",
    },
    "NOVA": {
        "calculate_income": "income_analysis",
        "calculate_dti": "income_analysis",
        "recalculate_income": "income_analysis",
        "evaluate_collections": "income_analysis",
        "full_income_analysis": "income_analysis",
    },
    "JARVIS": {
        "draft_loe": "document_analysis",
        "map_conditions": "document_analysis",
        "lookup_compliance": "document_analysis",
        "manage_condition": "document_analysis",
    },
    "DIEGO": {
        "triage_loan": "general",
        "advance_stage": "general",
        "check_pipeline_health": "general",
        "get_pipeline_report": "general",
    },
    "SENTINEL": {
        "scan_codebase": "codebase_analysis",
        "analyze_trends": "codebase_analysis",
        "reverse_engineer": "codebase_analysis",
        "generate_build_plan": "code_generation",
    },
}

# Provider endpoints
PROVIDERS = {
    "openai": {
        "url": "https://api.openai.com/v1/chat/completions",
        "key_header": "Authorization",
        "key_prefix": "Bearer ",
    },
    "anthropic": {
        "url": "https://api.anthropic.com/v1/messages",
        "key_header": "x-api-key",
        "key_prefix": "",
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "key_header": "Authorization",
        "key_prefix": "Bearer ",
    },
}


class LLMRouter:
    """Routes agent LLM requests to optimal models with automatic fallback."""

    def __init__(
        self,
        openai_key: str = "",
        anthropic_key: str = "",
        openrouter_key: str = "",
        default_provider: str = "openrouter",
        default_model: str = "anthropic/claude-sonnet-4-6",
    ):
        self._keys = {
            "openai": openai_key,
            "anthropic": anthropic_key,
            "openrouter": openrouter_key,
        }
        self._default_provider = default_provider
        self._default_model = default_model
        self._log = logger.bind(component="llm_router")
        self._total_requests = 0
        self._total_tokens = 0

    def _get_route(self, agent_name: str, action: str) -> dict[str, str]:
        """Determine the optimal model route for an agent action."""
        agent_routes = AGENT_TASK_ROUTES.get(agent_name, {})
        category = agent_routes.get(action, "general")
        return MODEL_ROUTES.get(category, MODEL_ROUTES["general"])

    def _has_key(self, provider: str) -> bool:
        return bool(self._keys.get(provider, ""))

    async def complete(
        self,
        agent_name: str,
        action: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Route a completion request to the optimal LLM."""
        route = self._get_route(agent_name, action)
        provider = route["provider"]
        model = route["model"]

        # Check if we have a key for the primary provider
        if not self._has_key(provider):
            provider = route.get("fallback_provider", self._default_provider)
            model = route.get("fallback_model", self._default_model)

        # Final fallback to any available provider
        if not self._has_key(provider):
            for p in ["openrouter", "anthropic", "openai"]:
                if self._has_key(p):
                    provider = p
                    model = self._default_model
                    break
            else:
                return {"error": "No LLM API keys configured", "response": ""}

        self._total_requests += 1
        self._log.info(
            "llm_routing",
            agent=agent_name,
            action=action,
            provider=provider,
            model=model,
        )

        try:
            if provider == "anthropic":
                return await self._call_anthropic(model, system_prompt, user_prompt, temperature, max_tokens)
            else:
                return await self._call_openai_compatible(provider, model, system_prompt, user_prompt, temperature, max_tokens)
        except Exception as e:
            self._log.error("llm_request_failed", provider=provider, error=str(e))
            # Try fallback
            fb_provider = route.get("fallback_provider", "")
            fb_model = route.get("fallback_model", "")
            if fb_provider and self._has_key(fb_provider) and fb_provider != provider:
                self._log.info("llm_fallback", from_provider=provider, to_provider=fb_provider)
                try:
                    if fb_provider == "anthropic":
                        return await self._call_anthropic(fb_model, system_prompt, user_prompt, temperature, max_tokens)
                    else:
                        return await self._call_openai_compatible(fb_provider, fb_model, system_prompt, user_prompt, temperature, max_tokens)
                except Exception as e2:
                    return {"error": f"Both providers failed: {e}, {e2}", "response": ""}
            return {"error": str(e), "response": ""}

    async def _call_anthropic(
        self, model: str, system_prompt: str, user_prompt: str,
        temperature: float, max_tokens: int,
    ) -> dict[str, Any]:
        """Call Anthropic Messages API."""
        headers = {
            "x-api-key": self._keys["anthropic"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(PROVIDERS["anthropic"]["url"], headers=headers, json=body) as resp:
                data = await resp.json()
                if resp.status == 200:
                    content = data.get("content", [{}])[0].get("text", "")
                    usage = data.get("usage", {})
                    self._total_tokens += usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                    return {
                        "response": content,
                        "model": model,
                        "provider": "anthropic",
                        "tokens": usage,
                    }
                else:
                    return {"error": str(data)[:300], "response": "", "status": resp.status}

    async def _call_openai_compatible(
        self, provider: str, model: str, system_prompt: str,
        user_prompt: str, temperature: float, max_tokens: int,
    ) -> dict[str, Any]:
        """Call OpenAI-compatible API (OpenAI or OpenRouter)."""
        config = PROVIDERS[provider]
        headers = {
            config["key_header"]: config["key_prefix"] + self._keys[provider],
            "Content-Type": "application/json",
        }
        if provider == "openrouter":
            headers["HTTP-Referer"] = "https://mortgagefintechos.ai"
            headers["X-Title"] = "MortgageFintechOS"

        body = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(config["url"], headers=headers, json=body) as resp:
                data = await resp.json()
                if resp.status == 200:
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    usage = data.get("usage", {})
                    self._total_tokens += usage.get("total_tokens", 0)
                    return {
                        "response": content,
                        "model": model,
                        "provider": provider,
                        "tokens": usage,
                    }
                else:
                    return {"error": str(data)[:300], "response": "", "status": resp.status}

    def get_status(self) -> dict[str, Any]:
        """Return router status."""
        available = [p for p in ["openai", "anthropic", "openrouter"] if self._has_key(p)]
        return {
            "available_providers": available,
            "default_provider": self._default_provider,
            "default_model": self._default_model,
            "total_requests": self._total_requests,
            "total_tokens": self._total_tokens,
        }
