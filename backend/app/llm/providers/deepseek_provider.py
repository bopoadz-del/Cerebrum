"""
DeepSeek provider for the LLM layer.
Uses the OpenAI-compatible API.
"""

from typing import Optional

from app.llm.providers.openai_provider import OpenAIProvider


class DeepSeekProvider(OpenAIProvider):
    """DeepSeek provider via OpenAI-compatible API."""

    name = "deepseek"

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com/v1",
        default_model: str = "deepseek-chat",
    ):
        super().__init__(api_key=api_key, base_url=base_url, default_model=default_model)
