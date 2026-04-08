"""
Local LLM Service using Ollama
Provides local inference without external API calls
"""

import os
import json
import requests
from typing import Optional, Dict, Any, Iterator
from app.core.logging import get_logger

logger = get_logger(__name__)

# Ollama configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
# Use smallest model for Render Starter tier (270M params, ~200MB)
# Can upgrade to qwen2.5:0.5b (~400MB) or llama3.2:1b (1.3GB) if needed
DEFAULT_MODEL = os.getenv("LOCAL_LLM_MODEL", "gemma3:270m")


class LocalLLMService:
    """Local LLM inference using Ollama."""
    
    def __init__(self, host: str = OLLAMA_HOST, model: str = DEFAULT_MODEL):
        self.host = host
        self.model = model
        self._available = None
    
    def is_available(self) -> bool:
        """Check if Ollama is running and model is available."""
        if self._available is not None:
            return self._available
            
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                available_models = [m["name"] for m in models]
                self._available = self.model in available_models
                if not self._available:
                    logger.warning(f"Model {self.model} not found. Available: {available_models}")
                return self._available
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            self._available = False
            return False
    
    def generate(
        self, 
        prompt: str, 
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False
    ) -> str:
        """Generate text completion."""
        if not self.is_available():
            raise RuntimeError("Local LLM not available. Is Ollama running?")
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }
        
        if system:
            payload["system"] = system
        
        try:
            response = requests.post(
                f"{self.host}/api/generate",
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            
            if stream:
                # Handle streaming response
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line)
                        if "response" in data:
                            full_response += data["response"]
                        if data.get("done"):
                            break
                return full_response
            else:
                data = response.json()
                return data.get("response", "")
                
        except Exception as e:
            logger.error(f"Local LLM generation failed: {e}")
            raise
    
    def chat(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False
    ) -> str:
        """Chat completion with message history."""
        if not self.is_available():
            raise RuntimeError("Local LLM not available. Is Ollama running?")
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }
        
        try:
            response = requests.post(
                f"{self.host}/api/chat",
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            
            if stream:
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            full_response += data["message"]["content"]
                        if data.get("done"):
                            break
                return full_response
            else:
                data = response.json()
                return data.get("message", {}).get("content", "")
                
        except Exception as e:
            logger.error(f"Local LLM chat failed: {e}")
            raise
    
    def embed(self, text: str) -> list:
        """Generate embeddings for text (for semantic search)."""
        try:
            response = requests.post(
                f"{self.host}/api/embeddings",
                json={"model": self.model, "prompt": text},
                timeout=30
            )
            response.raise_for_status()
            return response.json().get("embedding", [])
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise


# Global instance
_local_llm: Optional[LocalLLMService] = None


def get_local_llm() -> LocalLLMService:
    """Get or create LocalLLMService singleton."""
    global _local_llm
    if _local_llm is None:
        _local_llm = LocalLLMService()
    return _local_llm


def is_local_llm_available() -> bool:
    """Quick check if local LLM is available."""
    try:
        return get_local_llm().is_available()
    except:
        return False


# Convenience functions for direct use
def generate_with_local_llm(
    prompt: str,
    system: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048
) -> str:
    """Generate text using local LLM. Falls back gracefully."""
    try:
        llm = get_local_llm()
        if llm.is_available():
            return llm.generate(prompt, system, temperature, max_tokens)
    except Exception as e:
        logger.warning(f"Local LLM failed, no fallback: {e}")
    
    raise RuntimeError("Local LLM not available")
