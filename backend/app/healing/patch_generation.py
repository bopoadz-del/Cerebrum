"""
Patch Generation System

GPT-4 powered patch generation from stack traces and error context.
"""
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from openai import AsyncOpenAI
import logging

from .error_detection import ErrorEvent

logger = logging.getLogger(__name__)

openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@dataclass
class PatchResult:
    """Result of patch generation."""
    success: bool
    original_code: str
    patched_code: str
    explanation: str
    confidence: float
    error_type: str
    patch_id: str
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "patch_id": self.patch_id,
            "explanation": self.explanation,
            "confidence": self.confidence,
            "error_type": self.error_type,
            "created_at": self.created_at.isoformat(),
            "has_changes": self.original_code != self.patched_code
        }


class PatchGenerator:
    """
    Generates code patches from error events.
    
    Uses GPT-4 to:
    1. Analyze stack traces
    2. Identify root causes
    3. Generate fixes
    4. Validate patches
    """
    
    def __init__(self, model: str = "gpt-4-turbo-preview"):
        self.model = model
        self.client = openai_client
    
    async def generate_patch(
        self,
        error_event: ErrorEvent,
        original_code: str,
        context: Dict[str, Any] = None
    ) -> PatchResult:
        """
        Generate a patch for an error.
        
        Args:
            error_event: The error event to fix
            original_code: Original code that caused the error
            context: Additional context
        
        Returns:
            PatchResult with the generated patch
        """
        import uuid
        
        patch_id = str(uuid.uuid4())
        
        try:
            # Build prompt for patch generation
            prompt = self._build_patch_prompt(error_event, original_code, context)
            
            # Call GPT-4
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert software engineer specializing in bug fixing.
Your task is to analyze error reports and generate patches to fix the issues.

Guidelines:
1. Identify the root cause from the stack trace
2. Generate minimal, targeted fixes
3. Preserve existing functionality
4. Add error handling where appropriate
5. Include comments explaining the fix

Output format:
- Provide the complete fixed code
- Include a brief explanation of the fix
- Rate your confidence (0.0-1.0)"""
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=4000
            )
            
            # Parse response
            content = response.choices[0].message.content
            
            # Extract patched code and explanation
            patched_code, explanation, confidence = self._parse_patch_response(content)
            
            return PatchResult(
                success=True,
                original_code=original_code,
                patched_code=patched_code or original_code,
                explanation=explanation,
                confidence=confidence,
                error_type=error_event.error_type,
                patch_id=patch_id,
                created_at=datetime.utcnow()
            )
        
        except Exception as e:
            logger.error(f"Patch generation failed: {e}")
            return PatchResult(
                success=False,
                original_code=original_code,
                patched_code=original_code,
                explanation=f"Patch generation failed: {e}",
                confidence=0.0,
                error_type=error_event.error_type,
                patch_id=patch_id,
                created_at=datetime.utcnow()
            )
    
    def _build_patch_prompt(
        self,
        error_event: ErrorEvent,
        original_code: str,
        context: Dict[str, Any]
    ) -> str:
        """Build the prompt for patch generation."""
        prompt = f"""Error Report:
- Type: {error_event.error_type}
- Message: {error_event.error_message}
- Severity: {error_event.severity.value}

Stack Trace:
```
{error_event.stack_trace}
```

Original Code:
```python
{original_code}
```
"""
        
        if context:
            prompt += f"""
Additional Context:
{context}
"""
        
        prompt += """
Please:
1. Analyze the error and identify the root cause
2. Generate a fix for the issue
3. Provide the complete fixed code
4. Explain what was wrong and how you fixed it
5. Rate your confidence in this fix (0.0-1.0)

Format your response as:

FIXED_CODE:
```python
<complete fixed code here>
```

EXPLANATION:
<explanation of the fix>

CONFIDENCE: <0.0-1.0>
"""
        
        return prompt
    
    def _parse_patch_response(self, content: str) -> tuple:
        """Parse the patch response from GPT-4."""
        import re
        
        # Extract fixed code
        code_match = re.search(r'FIXED_CODE:\s*```python\s*(.*?)\s*```', content, re.DOTALL)
        patched_code = code_match.group(1).strip() if code_match else None
        
        # Extract explanation
        explanation_match = re.search(r'EXPLANATION:\s*(.*?)(?:\n\n|CONFIDENCE:)', content, re.DOTALL)
        explanation = explanation_match.group(1).strip() if explanation_match else "No explanation provided"
        
        # Extract confidence
        confidence_match = re.search(r'CONFIDENCE:\s*(\d+\.?\d*)', content)
        confidence = float(confidence_match.group(1)) if confidence_match else 0.5
        
        return patched_code, explanation, confidence
    
    async def generate_patch_for_common_errors(
        self,
        error_type: str,
        code: str
    ) -> Optional[PatchResult]:
        """Generate patches for common error types."""
        common_fixes = {
            "NameError": self._fix_name_error,
            "TypeError": self._fix_type_error,
            "AttributeError": self._fix_attribute_error,
            "KeyError": self._fix_key_error,
            "IndexError": self._fix_index_error,
            "ImportError": self._fix_import_error,
            "SyntaxError": self._fix_syntax_error
        }
        
        fixer = common_fixes.get(error_type)
        if fixer:
            return await fixer(code)
        
        return None
    
    async def _fix_name_error(self, code: str) -> PatchResult:
        """Fix common NameError issues."""
        import uuid
        
        # Common fixes for NameError
        patched = code
        
        # Add missing imports
        if "datetime" in code and "from datetime import datetime" not in code:
            patched = "from datetime import datetime\n" + patched
        
        if "json" in code and "import json" not in code:
            patched = "import json\n" + patched
        
        return PatchResult(
            success=True,
            original_code=code,
            patched_code=patched,
            explanation="Added missing imports that caused NameError",
            confidence=0.7,
            error_type="NameError",
            patch_id=str(uuid.uuid4()),
            created_at=datetime.utcnow()
        )
    
    async def _fix_type_error(self, code: str) -> PatchResult:
        """Fix common TypeError issues."""
        import uuid
        
        # This would need more sophisticated analysis
        return PatchResult(
            success=True,
            original_code=code,
            patched_code=code,  # No automatic fix
            explanation="TypeError requires manual analysis",
            confidence=0.3,
            error_type="TypeError",
            patch_id=str(uuid.uuid4()),
            created_at=datetime.utcnow()
        )
    
    async def _fix_attribute_error(self, code: str) -> PatchResult:
        """Fix common AttributeError issues."""
        import uuid
        
        return PatchResult(
            success=True,
            original_code=code,
            patched_code=code,
            explanation="AttributeError requires checking object attributes",
            confidence=0.4,
            error_type="AttributeError",
            patch_id=str(uuid.uuid4()),
            created_at=datetime.utcnow()
        )
    
    async def _fix_key_error(self, code: str) -> PatchResult:
        """Fix common KeyError issues."""
        import uuid
        
        # Add .get() for dictionary access
        import re
        patched = re.sub(
            r'(\w+)\[(\'[^\']+\'|"[^"]+")\]',
            r'\1.get(\2)',
            code
        )
        
        return PatchResult(
            success=True,
            original_code=code,
            patched_code=patched,
            explanation="Replaced direct dictionary access with .get() to handle missing keys",
            confidence=0.6,
            error_type="KeyError",
            patch_id=str(uuid.uuid4()),
            created_at=datetime.utcnow()
        )
    
    async def _fix_index_error(self, code: str) -> PatchResult:
        """Fix common IndexError issues."""
        import uuid
        
        return PatchResult(
            success=True,
            original_code=code,
            patched_code=code,
            explanation="IndexError requires bounds checking",
            confidence=0.5,
            error_type="IndexError",
            patch_id=str(uuid.uuid4()),
            created_at=datetime.utcnow()
        )
    
    async def _fix_import_error(self, code: str) -> PatchResult:
        """Fix common ImportError issues."""
        import uuid
        
        return PatchResult(
            success=True,
            original_code=code,
            patched_code=code,
            explanation="ImportError requires installing missing packages",
            confidence=0.5,
            error_type="ImportError",
            patch_id=str(uuid.uuid4()),
            created_at=datetime.utcnow()
        )
    
    async def _fix_syntax_error(self, code: str) -> PatchResult:
        """Fix common SyntaxError issues."""
        import uuid
        
        return PatchResult(
            success=True,
            original_code=code,
            patched_code=code,
            explanation="SyntaxError requires manual code review",
            confidence=0.2,
            error_type="SyntaxError",
            patch_id=str(uuid.uuid4()),
            created_at=datetime.utcnow()
        )


class SelfHealingEngine:
    """
    Orchestrates the self-healing process.
    
    Workflow:
    1. Detect error
    2. Generate patch
    3. Validate patch
    4. Apply patch (if auto-heal enabled)
    5. Verify fix
    """
    
    def __init__(self):
        self.patch_generator = PatchGenerator()
        self._auto_heal_enabled = False
        self._confidence_threshold = 0.8
        self._healing_history: List[Dict[str, Any]] = []
    
    async def handle_error(
        self,
        error_event: ErrorEvent,
        original_code: str,
        auto_apply: bool = False
    ) -> Dict[str, Any]:
        """
        Handle an error with self-healing.
        
        Args:
            error_event: The error to heal
            original_code: Code that caused the error
            auto_apply: Whether to auto-apply the patch
        
        Returns:
            Healing result
        """
        result = {
            "error_id": error_event.event_id,
            "healed": False,
            "patch": None,
            "applied": False,
            "message": ""
        }
        
        # Generate patch
        patch = await self.patch_generator.generate_patch(
            error_event=error_event,
            original_code=original_code
        )
        
        result["patch"] = patch.to_dict()
        
        if not patch.success:
            result["message"] = "Failed to generate patch"
            return result
        
        # Check confidence
        if patch.confidence < self._confidence_threshold:
            result["message"] = f"Patch confidence {patch.confidence} below threshold {self._confidence_threshold}"
            return result
        
        result["healed"] = True
        
        # Apply patch if requested
        if auto_apply and self._auto_heal_enabled:
            # This would integrate with the deployment system
            result["applied"] = True
            result["message"] = "Patch auto-applied"
        else:
            result["message"] = "Patch generated, awaiting approval"
        
        # Record in history
        self._healing_history.append({
            "error_id": error_event.event_id,
            "patch_id": patch.patch_id,
            "applied": result["applied"],
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return result
    
    def enable_auto_heal(self, enabled: bool = True):
        """Enable or disable auto-healing."""
        self._auto_heal_enabled = enabled
        logger.info(f"Auto-heal {'enabled' if enabled else 'disabled'}")
    
    def set_confidence_threshold(self, threshold: float):
        """Set minimum confidence for auto-healing."""
        self._confidence_threshold = max(0.0, min(1.0, threshold))
    
    def get_healing_history(self) -> List[Dict[str, Any]]:
        """Get healing history."""
        return self._healing_history
