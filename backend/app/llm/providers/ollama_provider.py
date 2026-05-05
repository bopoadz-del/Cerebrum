"""
Ollama / local LLM provider for the LLM layer.
"""

import os
import uuid
from typing import Optional

import httpx

from app.core.logging import get_logger
from app.llm.models import LLMMessage, LLMRequest, LLMResponse, LLMChoice, LLMUsage
from app.llm.providers.base import BaseLLMProvider

logger = get_logger(__name__)



class OllamaProvider(BaseLLMProvider):
    """Ollama local inference provider."""

    name = "ollama"

    def __init__(
        self,
        host: Optional[str] = None,
        default_model: str = "gemma3:270m",
    ):
        super().__init__(default_model=default_model)
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self._available = None

    def is_available(self) -> bool:
        # Return cached result if we already probed; otherwise optimistic True.
        # Sync I/O (requests.get) must not run inside the async event loop.
        # The real liveness check happens implicitly: chat() raises on connection error.
        if self._available is not None:
            return self._available
        return True

    async def probe(self) -> bool:
        """Async liveness check — safe to call from async context."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as c:
                r = await c.get(f"{self.host}/api/tags")
                self._available = r.status_code == 200
        except Exception as e:
            logger.warning("Ollama not available: %s", e)
            self._available = False
        return self._available

    async def chat(self, request: LLMRequest) -> LLMResponse:
        model = request.model or self.default_model
        messages = [{"role": m.role.value, "content": m.content} for m in request.messages]

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens or 2048,
            },
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(f"{self.host}/api/chat", json=payload)
                response.raise_for_status()
            except Exception as e:
                logger.error(f"Ollama chat completion failed: {e}")
                raise

            data = response.json()

        msg = data.get("message", {})
        choice = LLMChoice(
            index=0,
            message=LLMMessage(role=msg.get("role", "assistant"), content=msg.get("content", "")),
            finish_reason="stop" if data.get("done", True) else None,
        )

        usage = LLMUsage(
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            total_tokens=(data.get("prompt_eval_count", 0) + data.get("eval_count", 0)),
        )

        return LLMResponse(
            id=str(uuid.uuid4()),
            model=model,
            provider=self.name,
            choices=[choice],
            usage=usage,
            raw_response=data,
        )
