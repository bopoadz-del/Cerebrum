"""
AI Service - Simple DeepSeek integration for chat completions.
"""

import os
from typing import List, Dict, Any, Optional
import httpx

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEFAULT_MODEL = "deepseek-chat"


class AIService:
    """Simple DeepSeek AI service."""
    
    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY
    
    def is_available(self) -> bool:
        """Check if DeepSeek is configured."""
        return bool(self.api_key)
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> Dict[str, Any]:
        """
        Generate chat completion using DeepSeek API.
        
        Returns:
            Dict with 'content', 'model', 'tokens_used'
        """
        if not self.api_key:
            raise RuntimeError("DEEPSEEK_API_KEY not set")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                DEEPSEEK_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": DEFAULT_MODEL,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
        
        return {
            "content": data["choices"][0]["message"]["content"],
            "model": data.get("model", DEFAULT_MODEL),
            "tokens_used": data.get("usage", {}).get("total_tokens", 0),
        }


# Global instance
_ai_service = None


def get_ai_service() -> AIService:
    """Get AI service instance."""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service


async def generate_chat_response(
    messages: List[Dict[str, str]],
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
) -> str:
    """Convenience wrapper for chat completion."""
    service = get_ai_service()
    
    full_messages = messages.copy()
    if system_prompt:
        full_messages.insert(0, {"role": "system", "content": system_prompt})
    
    response = await service.chat_completion(messages=full_messages, temperature=temperature)
    return response["content"]
