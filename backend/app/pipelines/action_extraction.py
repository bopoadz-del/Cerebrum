"""
Action Item Extraction Pipeline using GPT-4
Extracts action items, deadlines, and responsibilities from documents.
"""

import json
import re
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class ActionStatus(Enum):
    """Status of an action item."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class ActionPriority(Enum):
    """Priority of an action item."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ActionItem:
    """An extracted action item."""
    id: str
    description: str
    assignee: Optional[str] = None
    deadline: Optional[str] = None
    priority: ActionPriority = ActionPriority.MEDIUM
    status: ActionStatus = ActionStatus.PENDING
    source_text: str = ""
    context: str = ""
    related_entities: List[str] = field(default_factory=list)
    extracted_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "assignee": self.assignee,
            "deadline": self.deadline,
            "priority": self.priority.value,
            "status": self.status.value,
            "source_text": self.source_text,
            "context": self.context,
            "related_entities": self.related_entities,
            "extracted_at": self.extracted_at.isoformat()
        }


@dataclass
class ActionExtractionResult:
    """Result of action item extraction."""
    actions: List[ActionItem]
    total_found: int
    with_deadline: int
    with_assignee: int
    processing_time: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "actions": [a.to_dict() for a in self.actions],
            "total_found": self.total_found,
            "with_deadline": self.with_deadline,
            "with_assignee": self.with_assignee,
            "processing_time": self.processing_time
        }


class GPT4ActionExtractor:
    """
    Action item extractor using GPT-4.
    Identifies tasks, deadlines, and responsibilities from text.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        if OPENAI_AVAILABLE:
            openai.api_key = self.api_key
    
    async def extract_actions(
        self,
        text: str,
        document_type: str = "meeting_minutes",
        context: Optional[str] = None
    ) -> ActionExtractionResult:
        """
        Extract action items from text using GPT-4.
        
        Args:
            text: Input text
            document_type: Type of document (meeting_minutes, email, report, etc.)
            context: Additional context about the document
        
        Returns:
            ActionExtractionResult with all action items
        """
        import time
        start_time = time.time()
        
        try:
            # Prepare prompt
            prompt = self._build_prompt(text, document_type, context)
            
            # Call GPT-4
            response = await openai.ChatCompletion.acreate(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at extracting action items, tasks, and deadlines from documents. Extract all actionable items with their assignees and deadlines."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            # Parse response
            content = response.choices[0].message.content
            actions = self._parse_actions(content, text)
            
            processing_time = time.time() - start_time
            
            return ActionExtractionResult(
                actions=actions,
                total_found=len(actions),
                with_deadline=sum(1 for a in actions if a.deadline),
                with_assignee=sum(1 for a in actions if a.assignee),
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"GPT-4 action extraction failed: {e}")
            # Fallback to rule-based
            return await self._rule_based_extraction(text)
    
    def _build_prompt(
        self,
        text: str,
        document_type: str,
        context: Optional[str]
    ) -> str:
        """Build extraction prompt."""
        prompt_parts = [
            f"Document Type: {document_type}",
        ]
        
        if context:
            prompt_parts.append(f"Context: {context}")
        
        prompt_parts.extend([
            "",
            "Extract all action items from the following text. For each action item, identify:",
            "1. Description of the task/action",
            "2. Person assigned (if mentioned)",
            "3. Deadline or due date (if mentioned)",
            "4. Priority level (low/medium/high/critical)",
            "",
            "Respond in JSON format as an array of action items:",
            "[",
            '  {',
            '    "description": "action description",',
            '    "assignee": "person name or null",',
            '    "deadline": "date or null",',
            '    "priority": "low/medium/high/critical",',
            '    "source_text": "original text segment"',
            '  }',
            "]",
            "",
            "Text:",
            text
        ])
        
        return "\n".join(prompt_parts)
    
    def _parse_actions(self, content: str, source_text: str) -> List[ActionItem]:
        """Parse GPT-4 response into ActionItem objects."""
        actions = []
        
        try:
            # Extract JSON from response
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
            else:
                data = json.loads(content)
            
            for i, item in enumerate(data):
                action = ActionItem(
                    id=f"action_{i+1}",
                    description=item.get('description', ''),
                    assignee=item.get('assignee'),
                    deadline=item.get('deadline'),
                    priority=ActionPriority(item.get('priority', 'medium')),
                    source_text=item.get('source_text', ''),
                    context=self._extract_context(item.get('source_text', ''), source_text)
                )
                actions.append(action)
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GPT-4 response: {e}")
            # Try to extract actions manually
            actions = self._manual_extraction(content, source_text)
        
        return actions
    
    def _extract_context(self, source_text: str, full_text: str, window: int = 100) -> str:
        """Extract context around source text."""
        if not source_text:
            return ""
        
        idx = full_text.find(source_text)
        if idx == -1:
            return ""
        
        start = max(0, idx - window)
        end = min(len(full_text), idx + len(source_text) + window)
        
        return full_text[start:end]
    
    def _manual_extraction(self, content: str, source_text: str) -> List[ActionItem]:
        """Manual extraction fallback."""
        actions = []
        
        # Look for action patterns
        action_patterns = [
            r'(?:action item|todo|task|follow[- ]?up)[\s:]*(.+?)(?:\n|$)',
            r'(?:\d+\.)\s*(.+?)(?:\n|$)',
        ]
        
        for pattern in action_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for i, match in enumerate(matches):
                action = ActionItem(
                    id=f"action_{i+1}",
                    description=match.group(1).strip(),
                    source_text=match.group(0),
                    context=self._extract_context(match.group(0), source_text)
                )
                actions.append(action)
        
        return actions
    
    async def _rule_based_extraction(self, text: str) -> ActionExtractionResult:
        """Fallback rule-based extraction."""
        import time
        start_time = time.time()
        
        actions = []
        
        # Pattern-based extraction
        patterns = {
            'action_item': r'(?:action item|action|todo)[\s#]*(\d*)[\s:]*(.+?)(?=\n\n|\n[A-Z]|$)',
            'assigned_task': r'((\w+)\s+(?:will|to|is|are)\s+(?:\w+\s+){0,5}(?:review|prepare|submit|provide|complete|send|follow up|coordinate))',
            'deadline_task': r'(.+?)(?:by|before|due|on)\s+((?:\d{1,2}[/-])?(?:\d{1,2}[/-])?\d{2,4})',
        }
        
        for pattern_name, pattern in patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
            
            for i, match in enumerate(matches):
                description = match.group(0).strip()
                
                # Extract assignee
                assignee = None
                assignee_match = re.search(r'(?:assigned to|@|responsibility of)\s*(\w+)', description, re.IGNORECASE)
                if assignee_match:
                    assignee = assignee_match.group(1)
                
                # Extract deadline
                deadline = None
                deadline_match = re.search(r'(?:by|before|due|on)\s+((?:\d{1,2}[/-])?(?:\d{1,2}[/-])?\d{2,4}|(?:next |this )?(?:Monday|Tuesday|Wednesday|Thursday|Friday|week|month))', description, re.IGNORECASE)
                if deadline_match:
                    deadline = deadline_match.group(1)
                
                action = ActionItem(
                    id=f"action_{pattern_name}_{i+1}",
                    description=description[:200],
                    assignee=assignee,
                    deadline=deadline,
                    source_text=match.group(0),
                    context=self._extract_context(match.group(0), text)
                )
                actions.append(action)
        
        # Remove duplicates
        seen = set()
        unique_actions = []
        for action in actions:
            key = action.description.lower()[:50]
            if key not in seen:
                seen.add(key)
                unique_actions.append(action)
        
        processing_time = time.time() - start_time
        
        return ActionExtractionResult(
            actions=unique_actions,
            total_found=len(unique_actions),
            with_deadline=sum(1 for a in unique_actions if a.deadline),
            with_assignee=sum(1 for a in unique_actions if a.assignee),
            processing_time=processing_time
        )


class ActionItemManager:
    """Manager for action items with tracking and updates."""
    
    def __init__(self):
        self.actions: Dict[str, ActionItem] = {}
    
    def add_actions(self, actions: List[ActionItem]) -> None:
        """Add action items to manager."""
        for action in actions:
            self.actions[action.id] = action
    
    def update_status(self, action_id: str, status: ActionStatus) -> bool:
        """Update action item status."""
        if action_id in self.actions:
            self.actions[action_id].status = status
            return True
        return False
    
    def update_assignee(self, action_id: str, assignee: str) -> bool:
        """Update action item assignee."""
        if action_id in self.actions:
            self.actions[action_id].assignee = assignee
            return True
        return False
    
    def update_deadline(self, action_id: str, deadline: str) -> bool:
        """Update action item deadline."""
        if action_id in self.actions:
            self.actions[action_id].deadline = deadline
            return True
        return False
    
    def get_overdue_actions(self) -> List[ActionItem]:
        """Get all overdue action items."""
        overdue = []
        today = datetime.utcnow().date()
        
        for action in self.actions.values():
            if action.deadline and action.status != ActionStatus.COMPLETED:
                try:
                    deadline_date = datetime.fromisoformat(action.deadline).date()
                    if deadline_date < today:
                        action.status = ActionStatus.OVERDUE
                        overdue.append(action)
                except ValueError:
                    pass
        
        return overdue
    
    def get_actions_by_assignee(self, assignee: str) -> List[ActionItem]:
        """Get action items by assignee."""
        return [a for a in self.actions.values() if a.assignee == assignee]
    
    def get_actions_by_status(self, status: ActionStatus) -> List[ActionItem]:
        """Get action items by status."""
        return [a for a in self.actions.values() if a.status == status]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "actions": [a.to_dict() for a in self.actions.values()],
            "total": len(self.actions),
            "by_status": {
                status.value: len(self.get_actions_by_status(status))
                for status in ActionStatus
            }
        }


class ActionExtractionPipeline:
    """Pipeline for action item extraction."""
    
    def __init__(self, use_gpt4: bool = True):
        self.use_gpt4 = use_gpt4
        if use_gpt4:
            self.extractor = GPT4ActionExtractor()
        else:
            self.extractor = GPT4ActionExtractor()  # Will use fallback
    
    async def process_document(
        self,
        text: str,
        document_type: str = "meeting_minutes",
        context: Optional[str] = None
    ) -> ActionExtractionResult:
        """
        Process document and extract action items.
        
        Args:
            text: Document text
            document_type: Type of document
            context: Additional context
        
        Returns:
            ActionExtractionResult
        """
        return await self.extractor.extract_actions(text, document_type, context)
    
    async def batch_process(
        self,
        documents: List[Tuple[str, str, str]],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, ActionExtractionResult]:
        """
        Process multiple documents.
        
        Args:
            documents: List of (doc_id, text, doc_type) tuples
            progress_callback: Optional progress callback
        
        Returns:
            Dictionary mapping doc_id to results
        """
        results = {}
        
        for i, (doc_id, text, doc_type) in enumerate(documents):
            result = await self.process_document(text, doc_type)
            results[doc_id] = result
            
            if progress_callback:
                progress_callback(i + 1, len(documents))
        
        return results


# Convenience function
async def extract_action_items(
    text: str,
    document_type: str = "meeting_minutes",
    use_gpt4: bool = True
) -> ActionExtractionResult:
    """
    Extract action items from text.
    
    Args:
        text: Input text
        document_type: Type of document
        use_gpt4: Whether to use GPT-4
    
    Returns:
        ActionExtractionResult
    """
    pipeline = ActionExtractionPipeline(use_gpt4=use_gpt4)
    return await pipeline.process_document(text, document_type)
