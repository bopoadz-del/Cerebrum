"""
Abstract base class for LLM providers.
"""

from abc import ABC, abstractmethod
from typing import Optional

from app.llm.models import LLMRequest, LLMResponse


class BaseLLMProvider(ABC):
    """Abstract base for all LLM providers."""

    name: str = "base"

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, default_model: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url
        self.default_model = default_model

    @abstractmethod
    async def chat(self, request: LLMRequest) -> LLMResponse:
        """Execute an async chat completion request."""
        raise NotImplementedError

    def is_available(self) -> bool:
        """Check if the provider is configured and available."""
        return True
