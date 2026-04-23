"""
Intent Router for Smart Orchestrator

Maps user messages to 39 Construction Container actions using:
1. Context Check: current file/session, last outcome, package
2. Intent Matching Priority:
   - Keyword + Pattern match
   - Schema match (PDF + "check specs")
   - Action name/synonym
   - Goal chaining ("Do full QTO")
   - Fallback → Self-Coding Agent
"""

import re
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from app.orchestrator.action_map import ACTION_MAP, ACTION_SYNONYMS, ActionCategory
from app.orchestrator.session_memory import SessionMemory
from app.containers import ConstructionBlock


class MatchPriority(Enum):
    """Priority levels for intent matching."""
    EXACT = 5  # Exact action name or synonym
    PATTERN = 4  # Keyword + pattern match
    SCHEMA = 3  # File type + keyword match
    SEMANTIC = 2  # Semantic similarity (LLM-based)
    CHAINING = 1  # Goal chaining detected
    NONE = 0  # No match - fallback


@dataclass
class IntentMatch:
    """Result of intent matching."""
    action_name: str
    priority: MatchPriority
    confidence: float
    extracted_params: Dict[str, Any]
    reasoning: str


class IntentRouter:
    """
    Intent router that maps user messages to construction actions.
    
    Key logic from Vietnam Doc:
    1. Context Check: current file/session, last outcome, package
    2. Intent Matching Priority:
       - Keyword + Pattern match ("extract quantities" → extract_quantities)
       - Schema match (PDF + "check specs" → process_specification_full)
       - Action name/synonym ("generate RFI" → rfi_generator)
       - Goal chaining ("Do full QTO" → intelligent_workflow)
       - Fallback → Self-Coding Agent
    """
    
    def __init__(self, session_memory: Optional[SessionMemory] = None):
        self.session_memory = session_memory or SessionMemory()
        self.construction_block = ConstructionBlock()
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for faster matching."""
        self._compiled_patterns = {}
        for action_name, definition in ACTION_MAP.items():
            self._compiled_patterns[action_name] = [
                re.compile(pattern, re.IGNORECASE) for pattern in definition.patterns
            ]
    
    async def route(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> IntentMatch:
        """
        Route user message to the appropriate action.
        
        Args:
            user_message: The user's input message
            context: Optional context dict with file_path, session_id, etc.
        
        Returns:
            IntentMatch with action_name, priority, confidence, and params
        """
        context = context or {}
        matches = []
        
        # 1. Context Check: Check for current file/session context
        self._update_context(user_message, context)
        
        # 2. Intent Matching - Priority Order
        
        # 2a. Exact match (action name or synonym)
        exact_match = self._check_exact_match(user_message)
        if exact_match:
            matches.append(exact_match)
        
        # 2b. Keyword + Pattern match
        pattern_matches = self._check_pattern_match(user_message)
        matches.extend(pattern_matches)
        
        # 2c. Schema match (file type + keywords)
        schema_match = self._check_schema_match(user_message, context)
        if schema_match:
            matches.append(schema_match)
        
        # 2d. Goal chaining detection
        chaining_match = self._check_goal_chaining(user_message)
        if chaining_match:
            matches.append(chaining_match)
        
        # 3. Select best match
        if matches:
            best_match = self._select_best_match(matches)
            
            # Extract parameters for the matched action
            params = self._extract_params(user_message, context, best_match.action_name)
            best_match.extracted_params.update(params)
            
            # Update session memory
            self.session_memory.update(
                action=best_match.action_name,
                params=best_match.extracted_params,
                outcome="routed"
            )
            
            return best_match
        
        # 4. Fallback → Self-Coding Agent
        return self._fallback_to_agent(user_message, context)
    
    def _update_context(self, user_message: str, context: Dict[str, Any]):
        """Update context with current file/session info."""
        # Check for file references in message
        file_patterns = [
            r'(?:file|document|drawing)\s+(?:at|path|is)?\s*[\'"]?([^\'"\s]+\.(?:pdf|dwg|xer|xml|xlsx|csv|ifc))',
            r'uploaded\s+(?:the\s+)?file\s+[\'"]?([^\'"\s]+)',
            r'(?:process|analyze)\s+[\'"]?([^\'"\s]+\.(?:pdf|dwg|xer|xml))',
        ]
        for pattern in file_patterns:
            match = re.search(pattern, user_message, re.IGNORECASE)
            if match:
                context["file_path"] = match.group(1)
                break
        
        # Update session memory with context
        if context.get("session_id"):
            self.session_memory.set_session(context["session_id"])
        if context.get("file_path"):
            self.session_memory.set_current_file(context["file_path"])
    
    def _check_exact_match(self, user_message: str) -> Optional[IntentMatch]:
        """Check for exact action name or synonym match."""
        message_lower = user_message.lower()
        
        # Check action names
        for action_name in ACTION_MAP.keys():
            # Match full action name
            if re.search(rf'\b{re.escape(action_name)}\b', message_lower):
                return IntentMatch(
                    action_name=action_name,
                    priority=MatchPriority.EXACT,
                    confidence=0.95,
                    extracted_params={},
                    reasoning=f"Exact action name match: {action_name}"
                )
            
            # Match action name without underscores
            display_name = action_name.replace("_", " ")
            if re.search(rf'\b{re.escape(display_name)}\b', message_lower):
                return IntentMatch(
                    action_name=action_name,
                    priority=MatchPriority.EXACT,
                    confidence=0.92,
                    extracted_params={},
                    reasoning=f"Action name match (spaced): {display_name}"
                )
        
        # Check synonyms
        for synonym, action_name in ACTION_SYNONYMS.items():
            if re.search(rf'\b{re.escape(synonym)}\b', message_lower):
                return IntentMatch(
                    action_name=action_name,
                    priority=MatchPriority.EXACT,
                    confidence=0.90,
                    extracted_params={},
                    reasoning=f"Synonym match: {synonym} → {action_name}"
                )
        
        return None
    
    def _check_pattern_match(self, user_message: str) -> List[IntentMatch]:
        """Check for keyword + pattern matches."""
        matches = []
        message_lower = user_message.lower()
        
        for action_name, definition in ACTION_MAP.items():
            score = 0
            matched_keywords = []
            
            # Check keywords
            for keyword in definition.keywords:
                if keyword in message_lower:
                    score += 1
                    matched_keywords.append(keyword)
            
            # Check regex patterns
            for compiled_pattern in self._compiled_patterns.get(action_name, []):
                if compiled_pattern.search(user_message):
                    score += 2  # Patterns weighted higher
            
            # Check synonym matches
            for synonym in definition.synonym_matches:
                if synonym in message_lower:
                    score += 1.5
            
            if score > 0:
                confidence = min(0.85, 0.4 + (score * 0.1))
                matches.append(IntentMatch(
                    action_name=action_name,
                    priority=MatchPriority.PATTERN,
                    confidence=confidence,
                    extracted_params={"matched_keywords": matched_keywords},
                    reasoning=f"Pattern match: {matched_keywords} (score: {score:.1f})"
                ))
        
        # Sort by confidence
        matches.sort(key=lambda m: m.confidence, reverse=True)
        return matches[:3]  # Return top 3
    
    def _check_schema_match(
        self,
        user_message: str,
        context: Dict[str, Any]
    ) -> Optional[IntentMatch]:
        """
        Check for schema match: file type + keywords.
        
        Example: PDF + "check specs" → process_specification_full
        """
        file_path = context.get("file_path") or self._extract_file_path(user_message)
        if not file_path:
            return None
        
        # Get file extension
        ext = file_path.lower().split('.')[-1] if '.' in file_path else ''
        ext_map = {
            'pdf': '.pdf',
            'dwg': '.dwg',
            'xer': '.xer',
            'xml': '.xml',
            'xlsx': '.xlsx',
            'csv': '.csv',
            'ifc': '.ifc',
        }
        file_ext = ext_map.get(ext, f'.{ext}')
        
        message_lower = user_message.lower()
        best_match = None
        best_score = 0
        
        for action_name, definition in ACTION_MAP.items():
            # Check if file type triggers this action
            if file_ext in definition.schema_triggers:
                # Score based on keyword matches
                score = sum(1 for kw in definition.keywords if kw in message_lower)
                
                if score > best_score:
                    best_score = score
                    best_match = IntentMatch(
                        action_name=action_name,
                        priority=MatchPriority.SCHEMA,
                        confidence=min(0.80, 0.5 + score * 0.1),
                        extracted_params={"file_path": file_path},
                        reasoning=f"Schema match: {file_ext} + keywords"
                    )
        
        return best_match
    
    def _check_goal_chaining(self, user_message: str) -> Optional[IntentMatch]:
        """
        Check for goal chaining patterns.
        
        Example: "Do full QTO" → intelligent_workflow
        """
        message_lower = user_message.lower()
        
        # Goal chaining patterns
        chaining_patterns = [
            (r'(?:do|perform|run)\s+(?:a\s+)?full\s+(?:qto|analysis|report)', "intelligent_workflow"),
            (r'(?:complete|full)\s+(?:project|document)\s+analysis', "intelligent_workflow"),
            (r'(?:analyze|process)\s+all\s+(?:documents|files|drawings)', "intelligent_workflow"),
            (r'(?:run|execute)\s+(?:the\s+)?(?:complete|full)\s+workflow', "intelligent_workflow"),
            (r'(?:extract|get)\s+quantities\s+(?:and|&)?\s*(?:costs?|carbon)?', "intelligent_workflow"),
            (r'(?:chain|sequence)\s+(?:multiple\s+)?(?:actions|steps)', "intelligent_workflow"),
        ]
        
        for pattern, action_name in chaining_patterns:
            if re.search(pattern, message_lower):
                return IntentMatch(
                    action_name=action_name,
                    priority=MatchPriority.CHAINING,
                    confidence=0.85,
                    extracted_params={"user_goal": user_message},
                    reasoning=f"Goal chaining detected: {pattern}"
                )
        
        return None
    
    def _select_best_match(self, matches: List[IntentMatch]) -> IntentMatch:
        """Select the best match based on priority and confidence."""
        # Sort by priority first, then confidence
        sorted_matches = sorted(
            matches,
            key=lambda m: (m.priority.value, m.confidence),
            reverse=True
        )
        return sorted_matches[0]
    
    def _extract_params(
        self,
        user_message: str,
        context: Dict[str, Any],
        action_name: str
    ) -> Dict[str, Any]:
        """Extract parameters relevant to the matched action."""
        params = {}
        
        # Add context file if available
        if context.get("file_path"):
            params["file_path"] = context["file_path"]
        
        # Extract file path from message if not in context
        if "file_path" not in params:
            file_path = self._extract_file_path(user_message)
            if file_path:
                params["file_path"] = file_path
        
        # Extract URLs
        url_match = re.search(r'https?://[^\s<>"{}|\\^`\[\]]+', user_message)
        if url_match:
            params["url"] = url_match.group(0)
        
        # Action-specific parameter extraction
        definition = ACTION_MAP.get(action_name)
        if definition:
            # Extract priority
            if "urgent" in user_message.lower():
                params["priority"] = "urgent"
            elif "high" in user_message.lower():
                params["priority"] = "high"
            
            # Extract trade/discipline
            trades = ["concrete", "steel", "electrical", "plumbing", "hvac", "masonry", "finishes"]
            for trade in trades:
                if trade in user_message.lower():
                    params["trade"] = trade
                    break
            
            # Extract numeric values
            value_match = re.search(r'(?:value|cost|amount)\s+(?:of\s+)?[$€£]?\s*([\d,]+(?:\.\d+)?)', user_message, re.IGNORECASE)
            if value_match:
                params["value"] = float(value_match.group(1).replace(',', ''))
        
        return params
    
    def _extract_file_path(self, message: str) -> Optional[str]:
        """Extract file path from message."""
        patterns = [
            r'["\']([^"\']+\.(?:pdf|dwg|xer|xml|xlsx|csv|ifc|doc|docx))["\']',
            r'\b(/[^\s]+\.(?:pdf|dwg|xer|xml|xlsx|csv|ifc|doc|docx))\b',
            r'(?:file|document)\s+(?:at|path)?\s*[:=]?\s*([^\s]+\.(?:pdf|dwg|xer|xml))',
        ]
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _fallback_to_agent(
        self,
        user_message: str,
        context: Dict[str, Any]
    ) -> IntentMatch:
        """
        Fallback to Self-Coding Agent when no match found.
        
        This returns a special action that triggers the agent to
        self-code a solution for the unrecognized intent.
        """
        return IntentMatch(
            action_name="self_coding_agent",
            priority=MatchPriority.NONE,
            confidence=0.3,
            extracted_params={
                "original_message": user_message,
                "context": context,
                "fallback_reason": "No matching construction action found"
            },
            reasoning="Fallback to Self-Coding Agent - no matching intent patterns found"
        )
    
    async def route_multi(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None,
        min_confidence: float = 0.45,
        max_actions: int = 3,
    ) -> List["IntentMatch"]:
        """
        Return up to max_actions distinct high-confidence matches sorted by
        (priority, confidence) descending.

        Used when a request could plausibly trigger multiple independent
        analyses. Guarantees at least one result — falls back to
        self_coding_agent when nothing qualifies.

        The best match is enriched with extracted params (same as route());
        secondary matches carry their raw scores so callers can read
        action_name, confidence, and reasoning.
        """
        context = context or {}
        self._update_context(user_message, context)

        candidates: List[IntentMatch] = []

        exact = self._check_exact_match(user_message)
        if exact:
            candidates.append(exact)

        candidates.extend(self._check_pattern_match(user_message))

        schema = self._check_schema_match(user_message, context)
        if schema:
            candidates.append(schema)

        chaining = self._check_goal_chaining(user_message)
        if chaining:
            candidates.append(chaining)

        # Deduplicate: keep highest-confidence entry per action_name
        seen: Dict[str, IntentMatch] = {}
        for m in candidates:
            if m.action_name not in seen or m.confidence > seen[m.action_name].confidence:
                seen[m.action_name] = m

        # Filter and sort by (priority value, confidence) descending
        qualified = sorted(
            (m for m in seen.values() if m.confidence >= min_confidence),
            key=lambda m: (m.priority.value, m.confidence),
            reverse=True,
        )

        if not qualified:
            return [self._fallback_to_agent(user_message, context)]

        # Enrich the best match with extracted params
        best = qualified[0]
        params = self._extract_params(user_message, context, best.action_name)
        best.extracted_params.update(params)
        self.session_memory.update(
            action=best.action_name,
            params=best.extracted_params,
            outcome="routed",
        )

        return qualified[:max_actions]

    def get_action_info(self, action_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific action."""
        definition = ACTION_MAP.get(action_name)
        if not definition:
            return None
        
        return {
            "name": definition.name,
            "category": definition.category.value,
            "description": definition.description,
            "keywords": definition.keywords,
            "required_input": definition.required_input,
            "optional_input": definition.optional_input,
            "schema_triggers": definition.schema_triggers,
        }
    
    def list_actions(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available actions, optionally filtered by category."""
        actions = []
        for action_name, definition in ACTION_MAP.items():
            if category and definition.category.value != category:
                continue
            actions.append({
                "name": action_name,
                "category": definition.category.value,
                "description": definition.description,
            })
        return actions
