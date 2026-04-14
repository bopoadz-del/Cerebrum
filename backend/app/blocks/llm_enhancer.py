"""
LLM Enhancer Block - AI Core layer for text extraction and structuring.
"""

from typing import Any, Dict, List, Optional

from app.core.block import BaseBlock, BlockConfig
from app.core.block_registry import BLOCK_REGISTRY
from app.llm import get_llm_client, LLMMessage


class LLMEnhancerBlock(BaseBlock):
    """AI text extraction and structuring using the unified LLM layer."""

    def __init__(self):
        super().__init__()
        self.config = BlockConfig(
            name="llm_enhancer",
            version="1.0",
            description="AI text extraction and structured output generation",
        )
        self.llm = get_llm_client()

    async def execute(self, action: str, input_data: dict, params: dict) -> dict:
        return await super().execute(action, input_data, params)

    async def extract_entities(self, input_data: dict, params: dict) -> dict:
        """Extract named entities from text using LLM."""
        text = input_data.get("text", "")
        entity_types = params.get("entity_types", ["organization", "person", "location", "date", "amount"])
        if not text:
            return {"status": "error", "error": "Missing 'text' in input_data"}
        prompt = (
            f"Extract the following entity types from the text: {', '.join(entity_types)}.\n"
            f"Respond as JSON with keys matching the entity types and values as lists.\n\nText:\n{text}\n"
        )
        try:
            result = await self.llm.json_chat(
                messages=[LLMMessage(role="user", content=prompt)],
                model=params.get("model"),
                temperature=0.1,
            )
            return {"status": "success", "entities": result}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def summarize(self, input_data: dict, params: dict) -> dict:
        """Summarize text using LLM."""
        text = input_data.get("text", "")
        max_words = params.get("max_words", 100)
        if not text:
            return {"status": "error", "error": "Missing 'text' in input_data"}
        prompt = f"Summarize the following text in under {max_words} words:\n\n{text}"
        try:
            response = await self.llm.chat(
                messages=[LLMMessage(role="user", content=prompt)],
                model=params.get("model"),
                temperature=0.3,
                max_tokens=512,
            )
            summary = response.choices[0].message.content if response.choices else ""
            return {"status": "success", "summary": summary.strip()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def classify(self, input_data: dict, params: dict) -> dict:
        """Classify text into provided categories."""
        text = input_data.get("text", "")
        categories = params.get("categories", [])
        if not text:
            return {"status": "error", "error": "Missing 'text' in input_data"}
        if not categories:
            return {"status": "error", "error": "Missing 'categories' in params"}
        prompt = (
            f"Classify the following text into exactly one of these categories: {', '.join(categories)}.\n"
            f"Respond as JSON with keys 'category' and 'confidence' (0-1).\n\nText:\n{text}\n"
        )
        try:
            result = await self.llm.json_chat(
                messages=[LLMMessage(role="user", content=prompt)],
                model=params.get("model"),
                temperature=0.1,
            )
            return {"status": "success", "classification": result}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def structure_json(self, input_data: dict, params: dict) -> dict:
        """Convert unstructured text into structured JSON using LLM."""
        text = input_data.get("text", "")
        schema_hint = params.get("schema_hint", "")
        if not text:
            return {"status": "error", "error": "Missing 'text' in input_data"}
        prompt = (
            "Convert the following unstructured text into structured JSON.\n"
            f"{schema_hint}\n\nText:\n{text}\n"
        )
        try:
            result = await self.llm.json_chat(
                messages=[LLMMessage(role="user", content=prompt)],
                model=params.get("model"),
                temperature=0.1,
            )
            return {"status": "success", "structured": result}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_actions(self) -> Dict[str, Any]:
        return {
            "extract_entities": self.extract_entities,
            "summarize": self.summarize,
            "classify": self.classify,
            "structure_json": self.structure_json,
        }


# Auto-register on import
BLOCK_REGISTRY.register(LLMEnhancerBlock())
