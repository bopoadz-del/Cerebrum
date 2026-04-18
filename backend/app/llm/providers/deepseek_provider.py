"""
DeepSeek provider for the LLM layer.
Uses DeepSeek's OpenAI-compatible API but standalone (no OpenAI dependency).
"""

import uuid
from typing import Optional

import httpx

from app.core.logging import get_logger
from app.llm.models import LLMMessage, LLMRequest, LLMResponse, LLMChoice, LLMUsage
from app.llm.providers.base import BaseLLMProvider

logger = get_logger(__name__)


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek provider via OpenAI-compatible API."""

    name = "deepseek"
    DEFAULT_BASE_URL = "https://api.deepseek.com/v1"

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com/v1",
        default_model: str = "deepseek-chat",
    ):
        super().__init__(api_key=api_key, base_url=base_url, default_model=default_model)
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=60.0,
        )

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def chat(self, request: LLMRequest) -> LLMResponse:
        model = request.model or self.default_model
        messages = [{"role": m.role.value, "content": m.content} for m in request.messages]

        payload = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
        }
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens
        if request.response_format:
            payload["response_format"] = request.response_format
        if request.tools:
            payload["tools"] = request.tools
            payload["tool_choice"] = request.tool_choice or "auto"

        try:
            response = await self.client.post("/chat/completions", json=payload)
            response.raise_for_status()
            completion = response.json()
        except Exception as e:
            logger.error(f"DeepSeek chat completion failed: {e}")
            raise

        choices = []
        for c in completion.get("choices", []):
            msg = c.get("message", {})
            message = LLMMessage(role=msg.get("role", "assistant"), content=msg.get("content") or "")
            choice = LLMChoice(
                index=c.get("index", 0),
                message=message,
                finish_reason=c.get("finish_reason"),
            )
            if msg.get("tool_calls"):
                choice.message.name = msg["tool_calls"][0]["function"]["name"]
                choice.tool_calls = [
                    {
                        "id": tc["id"],
                        "type": tc["type"],
                        "function": {
                            "name": tc["function"]["name"],
                            "arguments": tc["function"]["arguments"],
                        },
                    }
                    for tc in msg["tool_calls"]
                ]
            choices.append(choice)

        usage_data = completion.get("usage", {})
        usage = LLMUsage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )

        return LLMResponse(
            id=completion.get("id") or str(uuid.uuid4()),
            model=model,
            provider=self.name,
            choices=choices,
            usage=usage,
            raw_response=completion,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
