"""
AI Service

DeepSeek integration for chat completions and agent tasks.
Falls back to stub responses if DeepSeek is not configured.
"""

import os
from typing import List, Dict, Any, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)

# DeepSeek API Configuration
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY") or os.getenv("DEEPSEEKK_API_KEY") or settings.DEEPSEEK_API_KEY
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"  # DeepSeek V3


class AIService:
    """AI service for chat completions and agent tasks using DeepSeek."""
    
    def __init__(self):
        self.deepseek_key = DEEPSEEK_API_KEY
        self.http_client = httpx.AsyncClient(timeout=60.0)
    
    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()
    
    def is_available(self) -> bool:
        """Check if DeepSeek is configured."""
        return bool(self.deepseek_key)
    
    def get_provider(self) -> str:
        """Get the AI provider."""
        return "deepseek" if self.deepseek_key else "none"
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate chat completion using DeepSeek API.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (defaults to deepseek-chat)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            
        Returns:
            Response dict with 'content', 'tokens_used', 'model', etc.
        """
        if not self.deepseek_key:
            raise RuntimeError("DeepSeek API key not configured. Set DEEPSEEK_API_KEY.")
        
        return await self._deepseek_completion(
            messages, model or DEFAULT_DEEPSEEK_MODEL, temperature, max_tokens, stream
        )
    
    async def _deepseek_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        stream: bool,
    ) -> Dict[str, Any]:
        """Call DeepSeek API for chat completion."""
        headers = {
            "Authorization": f"Bearer {self.deepseek_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        
        try:
            response = await self.http_client.post(
                f"{DEEPSEEK_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "content": data["choices"][0]["message"]["content"],
                "role": "assistant",
                "model": data.get("model", model),
                "tokens_used": data.get("usage", {}).get("total_tokens", 0),
                "finish_reason": data["choices"][0].get("finish_reason", "stop"),
                "provider": "deepseek",
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"DeepSeek API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"DeepSeek request failed: {e}")
            raise


# Global service instance
_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """Get AI service instance."""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service


async def generate_chat_response(
    messages: List[Dict[str, str]],
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
) -> str:
    """
    Convenience function to generate a chat response using DeepSeek.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        system_prompt: Optional system prompt
        model: Model to use
        temperature: Sampling temperature
        
    Returns:
        Generated response text
    """
    service = get_ai_service()
    
    # Prepend system message if provided
    full_messages = messages.copy()
    if system_prompt:
        full_messages.insert(0, {"role": "system", "content": system_prompt})
    
    response = await service.chat_completion(
        messages=full_messages,
        model=model,
        temperature=temperature,
    )
    
    return response["content"]
