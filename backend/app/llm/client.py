"""
Unified LLM client with provider routing, retries, and error handling.
Uses DeepSeek as the default provider.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Type

from app.core.config import settings
from app.core.logging import get_logger
from app.llm.models import LLMMessage, LLMRequest, LLMResponse
from app.llm.providers.base import BaseLLMProvider
from app.llm.providers.deepseek_provider import DeepSeekProvider
from app.llm.providers.ollama_provider import OllamaProvider

logger = get_logger(__name__)

_PROVIDER_REGISTRY: Dict[str, Type[BaseLLMProvider]] = {
    "deepseek": DeepSeekProvider,
    "ollama": OllamaProvider,
}

# Fallback chain: if the primary provider fails, try the next one.
_FALLBACK_CHAIN: Dict[str, str] = {
    "deepseek": "ollama",
}

# Module-level singleton — prevents re-creating httpx.AsyncClient on every call.
_default_client: Optional["LLMClient"] = None


class LLMClient:
    """
    Unified async LLM client with DeepSeek as default.

    Usage:
        client = LLMClient()
        response = await client.chat(
            messages=[LLMMessage(role="user", content="Hello")],
            provider="deepseek",
            model="deepseek-chat"
        )
    """

    def __init__(self, default_provider: Optional[str] = None):
        self.default_provider = default_provider or self._infer_default_provider()
        self._providers: Dict[str, BaseLLMProvider] = {}

    def _infer_default_provider(self) -> str:
        """Pick the best available provider based on configured API keys."""
        if settings.DEEPSEEK_API_KEY:
            return "deepseek"
        return "ollama"

    def _get_provider(self, name: str) -> BaseLLMProvider:
        if name in self._providers:
            return self._providers[name]

        provider_cls = _PROVIDER_REGISTRY.get(name)
        if not provider_cls:
            raise ValueError(f"Unknown LLM provider: {name}. Available: {list(_PROVIDER_REGISTRY.keys())}")

        instance = self._create_provider_instance(name, provider_cls)
        self._providers[name] = instance
        return instance

    def _create_provider_instance(self, name: str, provider_cls: Type[BaseLLMProvider]) -> BaseLLMProvider:
        if name == "deepseek":
            if not settings.DEEPSEEK_API_KEY:
                raise RuntimeError("DEEPSEEK_API_KEY is not configured")
            return provider_cls(api_key=settings.DEEPSEEK_API_KEY)
        if name == "ollama":
            return provider_cls()
        return provider_cls()

    async def chat(
        self,
        messages: List[LLMMessage],
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = 4096,
        response_format: Optional[Dict[str, str]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        retries: int = 2,
    ) -> LLMResponse:
        """Send a chat completion request with automatic retry."""
        provider_name = provider or self.default_provider
        request = LLMRequest(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            tools=tools,
            tool_choice=tool_choice,
        )

        last_error: Optional[Exception] = None
        for attempt in range(retries + 1):
            try:
                llm_provider = self._get_provider(provider_name)
                if not llm_provider.is_available():
                    raise RuntimeError(f"Provider '{provider_name}' is not available")
                return await llm_provider.chat(request)
            except Exception as e:
                last_error = e
                logger.warning(
                    "LLM request failed (attempt %d/%d) for provider %s: %s",
                    attempt + 1,
                    retries + 1,
                    provider_name,
                    e,
                )
                if attempt < retries:
                    await asyncio.sleep(1.5 * (attempt + 1))

        # All retries exhausted — try the fallback provider once if the caller
        # didn't pin a specific provider.
        if provider is None:
            fallback_name = _FALLBACK_CHAIN.get(provider_name)
            if fallback_name:
                try:
                    fallback_provider = self._get_provider(fallback_name)
                    if isinstance(fallback_provider, OllamaProvider):
                        available = await fallback_provider.probe()
                    else:
                        available = fallback_provider.is_available()
                    if available:
                        logger.warning(
                            "Primary provider '%s' failed; falling back to '%s'",
                            provider_name,
                            fallback_name,
                        )
                        return await fallback_provider.chat(request)
                except Exception as fb_e:
                    logger.error("Fallback provider '%s' also failed: %s", fallback_name, fb_e)

        logger.error("All LLM request attempts failed for provider %s", provider_name)
        raise last_error or RuntimeError("LLM request failed")

    async def json_chat(
        self,
        messages: List[LLMMessage],
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = 4096,
        retries: int = 2,
    ) -> Any:
        """
        Convenience method for structured JSON output.
        Returns the parsed JSON dict.
        """
        response = await self.chat(
            messages=messages,
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            retries=retries,
        )
        content = response.choices[0].message.content if response.choices else "{}"
        import json
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM JSON response: %s", content)
            raise ValueError(f"Invalid JSON from LLM: {e}") from e


def get_llm_client(default_provider: Optional[str] = None) -> LLMClient:
    """Factory for getting a configured LLM client."""
    return LLMClient(default_provider=default_provider)


def get_default_client() -> LLMClient:
    """Return the module-level singleton LLMClient, creating it once.

    Reusing the singleton keeps the DeepSeekProvider's httpx.AsyncClient alive
    across requests instead of leaking a new connection pool per call.
    """
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client
