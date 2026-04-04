"""
Root Cause Analysis using AI

Analyzes errors and stack traces using GPT-4 to identify root causes
and generate fix hypotheses with confidence scoring.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from uuid import UUID

from openai import AsyncOpenAI

from app.healing.error_detection import ErrorIncident, StackTraceFrame

logger = logging.getLogger(__name__)


@dataclass
class RootCauseHypothesis:
    """A hypothesis about the root cause of an error."""
    description: str
    confidence: float  # 0.0 to 1.0
    affected_files: List[str]
    suggested_fix_type: str
    supporting_evidence: List[str]


@dataclass
class RootCauseAnalysis:
    """Result of root cause analysis."""
    incident_id: UUID
    hypotheses: List[RootCauseHypothesis]
    primary_hypothesis: Optional[RootCauseHypothesis]
    analysis_summary: str
    relevant_code_snippets: List[Dict[str, str]]
    suggested_tests: List[str]
    ai_analysis_time_ms: float


class RootCauseAnalyzer:
    """
    Analyzes errors using AI to identify root causes.
    
    Uses GPT-4 to:
    - Analyze stack traces
    - Identify problematic code patterns
    - Generate fix hypotheses
    - Score confidence of each hypothesis
    """
    
    SYSTEM_PROMPT = """You are an expert software engineer specializing in debugging and root cause analysis.

Your task is to analyze error incidents and identify the root cause. For each incident:

1. Analyze the stack trace to understand the error flow
2. Identify the specific code that caused the error
3. Consider common patterns that lead to this type of error
4. Generate hypotheses about the root cause
5. Assign confidence scores to each hypothesis

Output your analysis in JSON format with:
- hypotheses: List of root cause hypotheses with confidence scores
- primary_hypothesis: The most likely root cause
- relevant_files: Files that need to be examined
- suggested_fix_type: Type of fix needed (e.g., "null_check", "type_conversion", "error_handling")
- analysis_summary: Brief summary of your analysis

Be thorough but concise. Focus on actionable insights."""
    
    def __init__(self, openai_client: Optional[AsyncOpenAI] = None):
        """
        Initialize the root cause analyzer.
        
        Args:
            openai_client: OpenAI client instance
        """
        self.client = openai_client or AsyncOpenAI()
    
    async def analyze(
        self,
        incident: ErrorIncident,
        code_context: Optional[Dict[str, str]] = None,
    ) -> RootCauseAnalysis:
        """
        Analyze an incident to identify root cause.
        
        Args:
            incident: Error incident to analyze
            code_context: Optional code context (file_path -> code)
            
        Returns:
            RootCauseAnalysis with hypotheses
        """
        import time
        start_time = time.time()
        
        # Build analysis prompt
        prompt = self._build_analysis_prompt(incident, code_context)
        
        try:
            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=2000,
            )
            
            # Parse response
            analysis_text = response.choices[0].message.content
            analysis_data = json.loads(analysis_text)
            
            # Build hypotheses
            hypotheses = []
            for h_data in analysis_data.get("hypotheses", []):
                hypothesis = RootCauseHypothesis(
                    description=h_data.get("description", ""),
                    confidence=h_data.get("confidence", 0.5),
                    affected_files=h_data.get("affected_files", []),
                    suggested_fix_type=h_data.get("suggested_fix_type", "unknown"),
                    supporting_evidence=h_data.get("supporting_evidence", []),
                )
                hypotheses.append(hypothesis)
            
            # Sort by confidence
            hypotheses.sort(key=lambda h: h.confidence, reverse=True)
            
            # Get primary hypothesis
            primary = None
            if hypotheses:
                primary = hypotheses[0]
            
            analysis_time = (time.time() - start_time) * 1000
            
            return RootCauseAnalysis(
                incident_id=incident.id,
                hypotheses=hypotheses,
                primary_hypothesis=primary,
                analysis_summary=analysis_data.get("analysis_summary", ""),
                relevant_code_snippets=analysis_data.get("relevant_code_snippets", []),
                suggested_tests=analysis_data.get("suggested_tests", []),
                ai_analysis_time_ms=analysis_time,
            )
            
        except Exception as e:
            logger.error(f"Root cause analysis failed: {e}")
            
            return RootCauseAnalysis(
                incident_id=incident.id,
                hypotheses=[],
                primary_hypothesis=None,
                analysis_summary=f"Analysis failed: {e}",
                relevant_code_snippets=[],
                suggested_tests=[],
                ai_analysis_time_ms=(time.time() - start_time) * 1000,
            )
    
    def _build_analysis_prompt(
        self,
        incident: ErrorIncident,
        code_context: Optional[Dict[str, str]],
    ) -> str:
        """Build the analysis prompt for the AI."""
        parts = [
            "Analyze the following error incident and identify the root cause.",
            "",
            "=== ERROR DETAILS ===",
            f"Error Type: {incident.error_type}",
            f"Error Message: {incident.error_message}",
            f"Severity: {incident.severity.value}",
            f"Source: {incident.source.value}",
            f"Occurrences: {incident.occurrence_count}",
            "",
        ]
        
        # Add stack trace
        if incident.stack_trace:
            parts.extend([
                "=== STACK TRACE ===",
            ])
            for i, frame in enumerate(incident.stack_trace[:10]):  # Limit to 10 frames
                parts.extend([
                    f"Frame {i}:",
                    f"  File: {frame.filename}",
                    f"  Function: {frame.function}",
                    f"  Line: {frame.lineno}",
                ])
            parts.append("")
        
        # Add code context
        if code_context:
            parts.extend([
                "=== RELEVANT CODE ===",
            ])
            for filename, code in code_context.items():
                parts.extend([
                    f"File: {filename}",
                    "```python",
                    code[:2000],  # Limit code length
                    "```",
                    "",
                ])
        
        # Add context info
        if incident.endpoint:
            parts.append(f"Endpoint: {incident.endpoint}")
        if incident.capability_id:
            parts.append(f"Capability ID: {incident.capability_id}")
        parts.append("")
        
        parts.append("Provide your analysis in JSON format.")
        
        return "\n".join(parts)
    
    async def quick_analyze(
        self,
        error_type: str,
        error_message: str,
        stack_trace_summary: str,
    ) -> Dict[str, Any]:
        """
        Quick analysis without full incident object.
        
        Args:
            error_type: Type of error
            error_message: Error message
            stack_trace_summary: Summary of stack trace
            
        Returns:
            Quick analysis results
        """
        prompt = f"""Quickly analyze this error:

Error Type: {error_type}
Error Message: {error_message}
Stack Trace Summary: {stack_trace_summary}

What is the most likely cause? Suggest a fix in 1-2 sentences."""
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a debugging expert. Be concise."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=200,
            )
            
            return {
                "analysis": response.choices[0].message.content,
                "confidence": 0.7,  # Estimated
            }
            
        except Exception as e:
            logger.error(f"Quick analysis failed: {e}")
            return {
                "analysis": f"Analysis failed: {e}",
                "confidence": 0.0,
            }


# Singleton instance
analyzer_instance: Optional[RootCauseAnalyzer] = None


def get_root_cause_analyzer(openai_client: Optional[AsyncOpenAI] = None) -> RootCauseAnalyzer:
    """Get or create the singleton root cause analyzer instance."""
    global analyzer_instance
    if analyzer_instance is None:
        analyzer_instance = RootCauseAnalyzer(openai_client)
    return analyzer_instance
