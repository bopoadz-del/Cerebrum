"""
OpenAI provider for the LLM layer.
"""

import uuid
from typing import Optional

from openai import AsyncOpenAI

from app.core.logging import get_logger
from app.llm.models import LLMMessage, LLMRequest, LLMResponse, LLMChoice, LLMUsage
from app.llm.providers.base import BaseLLMProvider

logger = get_logger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider."""

    name = "openai"

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        default_model: str = "gpt-4o-mini",
    ):
        super().__init__(api_key=api_key, base_url=base_url, default_model=default_model)
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def chat(self, request: LLMRequest) -> LLMResponse:
        model = request.model or self.default_model
        messages = [{"role": m.role.value, "content": m.content} for m in request.messages]

        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
        }
        if request.max_tokens:
            kwargs["max_tokens"] = request.max_tokens
        if request.response_format:
            kwargs["response_format"] = request.response_format
        if request.tools:
            kwargs["tools"] = request.tools
            kwargs["tool_choice"] = request.tool_choice or "auto"

        try:
            completion = await self.client.chat.completions.create(**kwargs)
        except Exception as e:
            logger.error(f"OpenAI chat completion failed: {e}")
            raise

        choices = []
        for c in completion.choices:
            msg = LLMMessage(role=c.message.role, content=c.message.content or "")
            choice = LLMChoice(
                index=c.index,
                message=msg,
                finish_reason=c.finish_reason,
            )
            if c.message.tool_calls:
                choice.message.name = c.message.tool_calls[0].function.name
                choice.tool_calls = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in c.message.tool_calls
                ]
            choices.append(choice)

        usage = LLMUsage(
            prompt_tokens=completion.usage.prompt_tokens if completion.usage else 0,
            completion_tokens=completion.usage.completion_tokens if completion.usage else 0,
            total_tokens=completion.usage.total_tokens if completion.usage else 0,
        )

        return LLMResponse(
            id=completion.id or str(uuid.uuid4()),
            model=model,
            provider=self.name,
            choices=choices,
            usage=usage,
            raw_response=completion,
        )
