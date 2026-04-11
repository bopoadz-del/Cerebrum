"""
AI Service

OpenAI/Claude integration for chat completions and agent tasks.
Supports both OpenAI and Anthropic Claude APIs with fallback.
"""

import os
from typing import AsyncGenerator, List, Dict, Any, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)

# API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Default models
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"  # Fast and cost-effective
PREMIUM_OPENAI_MODEL = "gpt-4o"  # Higher quality
DEFAULT_CLAUDE_MODEL = "claude-3-5-sonnet-20241022"

# API Endpoints
OPENAI_BASE_URL = "https://api.openai.com/v1"
ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1"


class AIService:
    """AI service for chat completions and agent tasks."""
    
    def __init__(self):
        self.openai_key = OPENAI_API_KEY
        self.anthropic_key = ANTHROPIC_API_KEY
        self.http_client = httpx.AsyncClient(timeout=60.0)
    
    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()
    
    def is_available(self) -> bool:
        """Check if any AI provider is configured."""
        return bool(self.openai_key or self.anthropic_key)
    
    def get_provider(self) -> str:
        """Get the preferred AI provider."""
        if self.openai_key:
            return "openai"
        elif self.anthropic_key:
            return "anthropic"
        return "none"
    
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
        Generate chat completion using available AI provider.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (defaults based on provider)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            
        Returns:
            Response dict with 'content', 'tokens_used', 'model', etc.
        """
        # Try OpenAI first
        if self.openai_key:
            return await self._openai_completion(
                messages, model or DEFAULT_OPENAI_MODEL, temperature, max_tokens, stream
            )
        
        # Fall back to Claude
        if self.anthropic_key:
            return await self._claude_completion(
                messages, model or DEFAULT_CLAUDE_MODEL, temperature, max_tokens, stream
            )
        
        raise RuntimeError("No AI provider configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY.")
    
    async def _openai_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        stream: bool,
    ) -> Dict[str, Any]:
        """Call OpenAI API for chat completion."""
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
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
                f"{OPENAI_BASE_URL}/chat/completions",
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
                "provider": "openai",
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"OpenAI request failed: {e}")
            raise
    
    async def _claude_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        stream: bool,
    ) -> Dict[str, Any]:
        """Call Anthropic Claude API for chat completion."""
        headers = {
            "x-api-key": self.anthropic_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        
        # Convert OpenAI format to Claude format
        system_msg = None
        claude_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                claude_messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })
        
        payload = {
            "model": model,
            "messages": claude_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }
        
        if system_msg:
            payload["system"] = system_msg
        
        try:
            response = await self.http_client.post(
                f"{ANTHROPIC_BASE_URL}/messages",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "content": data["content"][0]["text"],
                "role": "assistant",
                "model": data.get("model", model),
                "tokens_used": data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0),
                "finish_reason": data.get("stop_reason", "stop"),
                "provider": "anthropic",
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"Claude API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Claude request failed: {e}")
            raise
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate text embedding using OpenAI."""
        if not self.openai_key:
            raise RuntimeError("OpenAI API key not configured for embeddings")
        
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": "text-embedding-3-small",
            "input": text,
        }
        
        try:
            response = await self.http_client.post(
                f"{OPENAI_BASE_URL}/embeddings",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
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
    Convenience function to generate a chat response.
    
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
