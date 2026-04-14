"""
Pydantic models for the LLM layer.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class LLMMessage(BaseModel):
    role: Role = Role.USER
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None


class ToolCall(BaseModel):
    id: str
    type: str = "function"
    function: Dict[str, Any]


class LLMChoice(BaseModel):
    index: int = 0
    message: LLMMessage
    finish_reason: Optional[str] = "stop"
    tool_calls: Optional[List[ToolCall]] = None


class LLMUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class LLMResponse(BaseModel):
    id: str = ""
    model: str = ""
    provider: str = ""
    choices: List[LLMChoice] = Field(default_factory=list)
    usage: LLMUsage = Field(default_factory=LLMUsage)
    raw_response: Optional[Any] = Field(default=None, description="Provider-specific raw response")


class LLMRequest(BaseModel):
    messages: List[LLMMessage]
    model: Optional[str] = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=4096, ge=1)
    response_format: Optional[Dict[str, str]] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Any] = None
    stream: bool = False
