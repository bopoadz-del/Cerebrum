"""
OpenAI API Stub

Stub implementation for OpenAI API.
"""

from typing import Any, Dict, List, Optional, Generator
from datetime import datetime
from .base import BaseStub, StubResponse


class OpenAIStub(BaseStub):
    """
    Stub for OpenAI API.
    
    Provides mock responses for:
    - Chat completions
    - Embeddings
    - Fine-tuning
    - Transcriptions
    """
    
    service_name = "openai"
    version = "1.0.0-stub"
    
    _mock_responses = {
        "default": "This is a stub response from the AI. In production, this would be a real OpenAI completion.",
        "document": "Based on the document analysis, I can see this is a construction project with the following key points: 1) Foundation work required, 2) Steel framework to be installed, 3) Estimated completion in Q4.",
        "classification": '{"category": "construction_document", "confidence": 0.95, "entities": ["foundation", "steel", "timeline"]}',
        "extraction": '{"action_items": [{"task": "Review foundation plans", "assignee": "Engineer", "due": "2024-03-01"}]',
    }
    
    def get_info(self) -> Dict[str, Any]:
        """Return stub information."""
        return {
            "service": self.service_name,
            "version": self.version,
            "mode": "stub",
            "models": ["gpt-4-stub", "gpt-3.5-stub", "text-embedding-stub"],
        }
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4-stub",
        **kwargs
    ) -> StubResponse:
        """Mock chat completion."""
        self._log_call("chat_completion", model=model, message_count=len(messages))
        
        # Determine response type based on message content
        last_message = messages[-1].get("content", "").lower() if messages else ""
        response_type = "default"
        if "document" in last_message or "analyze" in last_message:
            response_type = "document"
        elif "classif" in last_message:
            response_type = "classification"
        elif "extract" in last_message or "action" in last_message:
            response_type = "extraction"
        
        content = self._mock_responses.get(response_type, self._mock_responses["default"])
        
        return self._success_response(
            data={
                "id": "chatcmpl-stub-999",
                "object": "chat.completion",
                "created": int(datetime.utcnow().timestamp()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150,
                },
            },
            message="Chat completion (stub)",
        )
    
    def create_embedding(self, input_text: str, model: str = "text-embedding-stub") -> StubResponse:
        """Mock embedding creation."""
        self._log_call("create_embedding", model=model, input_length=len(input_text))
        
        # Return a deterministic mock embedding (1536 dimensions)
        import hashlib
        hash_val = int(hashlib.md5(input_text.encode()).hexdigest(), 16)
        embedding = [(hash_val % 1000) / 1000.0 for _ in range(1536)]
        
        return self._success_response(
            data={
                "object": "list",
                "data": [{
                    "object": "embedding",
                    "embedding": embedding,
                    "index": 0,
                }],
                "model": model,
                "usage": {"prompt_tokens": len(input_text.split()), "total_tokens": len(input_text.split())},
            },
            message="Embedding created (stub)",
        )
    
    def transcribe_audio(self, audio_file: str, model: str = "whisper-stub") -> StubResponse:
        """Mock audio transcription."""
        self._log_call("transcribe_audio", audio_file=audio_file, model=model)
        return self._success_response(
            data={
                "text": "This is a stub transcription. In production, this would be actual transcribed audio content.",
                "task": "transcribe",
                "language": "en",
                "duration": 120.0,
                "segments": [
                    {"id": 0, "start": 0.0, "end": 10.0, "text": "Stub segment 1"},
                    {"id": 1, "start": 10.0, "end": 20.0, "text": "Stub segment 2"},
                ],
            },
            message="Audio transcribed (stub)",
        )
    
    def classify_document(self, text: str, categories: List[str]) -> StubResponse:
        """Mock document classification."""
        self._log_call("classify_document", categories=categories)
        
        # Simple keyword-based classification for stub
        text_lower = text.lower()
        category_scores = {}
        for cat in categories:
            score = 0.5  # Base score
            if cat.lower() in text_lower:
                score = 0.9
            category_scores[cat] = score
        
        # Pick highest score
        best_category = max(category_scores, key=category_scores.get)
        
        return self._success_response(
            data={
                "classification": best_category,
                "confidence": category_scores[best_category],
                "scores": category_scores,
            },
            message="Document classified (stub)",
        )
    
    def extract_entities(self, text: str, entity_types: List[str]) -> StubResponse:
        """Mock entity extraction."""
        self._log_call("extract_entities", entity_types=entity_types)
        
        # Simple regex-based stub extraction
        import re
        entities = []
        
        # Dates
        date_pattern = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
        for match in re.finditer(date_pattern, text):
            entities.append({"text": match.group(), "type": "DATE", "start": match.start(), "end": match.end()})
        
        # Emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        for match in re.finditer(email_pattern, text):
            entities.append({"text": match.group(), "type": "EMAIL", "start": match.start(), "end": match.end()})
        
        return self._success_response(
            data={"entities": entities},
            message=f"Extracted {len(entities)} entities (stub)",
        )
