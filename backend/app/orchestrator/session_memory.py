"""
Session Memory for Smart Orchestrator

Cross-turn context tracking for maintaining state across
multiple user interactions and action executions.
"""

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SessionContext:
    """Context for a single session."""
    session_id: str
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    
    # Current state
    current_file: Optional[str] = None
    current_package: Optional[str] = None
    last_action: Optional[str] = None
    last_outcome: Optional[str] = None
    
    # History
    action_history: List[Dict[str, Any]] = field(default_factory=list)
    file_history: List[str] = field(default_factory=list)
    
    # Accumulated results
    accumulated_results: Dict[str, Any] = field(default_factory=dict)
    
    # Workflow state
    workflow_state: Optional[str] = None
    workflow_chain: List[str] = field(default_factory=list)
    workflow_data: Dict[str, Any] = field(default_factory=dict)


class SessionMemory:
    """
    Cross-turn context tracking for the Smart Orchestrator.
    
    Key capabilities:
    - Track current file/session context
    - Remember last outcomes
    - Accumulate results across actions
    - Manage workflow state
    """
    
    def __init__(self, max_sessions: int = 100, ttl_seconds: int = 3600):
        self._sessions: Dict[str, SessionContext] = {}
        self._max_sessions = max_sessions
        self._ttl_seconds = ttl_seconds
    
    def set_session(self, session_id: str) -> SessionContext:
        """Set or create a session context."""
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionContext(session_id=session_id)
            # Clean up old sessions if limit reached
            self._cleanup_old_sessions()
        else:
            self._sessions[session_id].last_activity = time.time()
        return self._sessions[session_id]
    
    def get_session(self, session_id: str) -> Optional[SessionContext]:
        """Get a session context if it exists and is not expired."""
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        # Check TTL
        if time.time() - session.last_activity > self._ttl_seconds:
            del self._sessions[session_id]
            return None
        
        session.last_activity = time.time()
        return session
    
    def set_current_file(self, file_path: str, session_id: Optional[str] = None):
        """Set the current file for a session."""
        if session_id:
            session = self.set_session(session_id)
            session.current_file = file_path
            if file_path not in session.file_history:
                session.file_history.append(file_path)
    
    def get_current_file(self, session_id: Optional[str] = None) -> Optional[str]:
        """Get the current file for a session."""
        if not session_id:
            return None
        session = self.get_session(session_id)
        return session.current_file if session else None
    
    def set_package(self, package: str, session_id: str):
        """Set the current package/container for a session."""
        session = self.set_session(session_id)
        session.current_package = package
    
    def get_package(self, session_id: str) -> Optional[str]:
        """Get the current package for a session."""
        session = self.get_session(session_id)
        return session.current_package if session else None
    
    def update(
        self,
        action: str,
        params: Dict[str, Any],
        outcome: str = "pending",
        result: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ):
        """Update session memory with action execution info."""
        if not session_id:
            return
        
        session = self.set_session(session_id)
        
        # Update state
        session.last_action = action
        session.last_outcome = outcome
        
        # Add to history
        session.action_history.append({
            "action": action,
            "params": params,
            "outcome": outcome,
            "result": result,
            "timestamp": time.time(),
        })
        
        # Accumulate results
        if result:
            for key, value in result.items():
                if key not in session.accumulated_results:
                    session.accumulated_results[key] = []
                session.accumulated_results[key].append({
                    "action": action,
                    "value": value,
                    "timestamp": time.time(),
                })
    
    def get_last_action(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the last action executed in a session."""
        session = self.get_session(session_id)
        if not session or not session.action_history:
            return None
        return session.action_history[-1]
    
    def get_last_outcome(self, session_id: str) -> Optional[str]:
        """Get the outcome of the last action."""
        session = self.get_session(session_id)
        return session.last_outcome if session else None
    
    def get_action_history(
        self,
        session_id: str,
        action_name: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get action history for a session."""
        session = self.get_session(session_id)
        if not session:
            return []
        
        history = session.action_history
        if action_name:
            history = [h for h in history if h["action"] == action_name]
        
        return history[-limit:]
    
    def get_accumulated_results(
        self,
        session_id: str,
        key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get accumulated results for a session."""
        session = self.get_session(session_id)
        if not session:
            return {}
        
        if key:
            return session.accumulated_results.get(key, [])
        return session.accumulated_results
    
    def set_workflow_state(
        self,
        session_id: str,
        state: str,
        chain: Optional[List[str]] = None,
        data: Optional[Dict[str, Any]] = None
    ):
        """Set the workflow state for a session."""
        session = self.set_session(session_id)
        session.workflow_state = state
        if chain:
            session.workflow_chain = chain
        if data:
            session.workflow_data.update(data)
    
    def get_workflow_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the workflow state for a session."""
        session = self.get_session(session_id)
        if not session:
            return None
        
        return {
            "state": session.workflow_state,
            "chain": session.workflow_chain,
            "data": session.workflow_data,
        }
    
    def add_to_workflow_chain(
        self,
        session_id: str,
        action: str,
        result: Optional[Dict[str, Any]] = None
    ):
        """Add an action to the workflow chain."""
        session = self.set_session(session_id)
        session.workflow_chain.append(action)
        if result:
            session.workflow_data[action] = result
    
    def clear_workflow(self, session_id: str):
        """Clear the workflow state for a session."""
        session = self.get_session(session_id)
        if session:
            session.workflow_state = None
            session.workflow_chain = []
            session.workflow_data = {}
    
    def get_context_summary(self, session_id: str) -> Dict[str, Any]:
        """Get a summary of the current context for a session."""
        session = self.get_session(session_id)
        if not session:
            return {}
        
        return {
            "session_id": session.session_id,
            "current_file": session.current_file,
            "current_package": session.current_package,
            "last_action": session.last_action,
            "last_outcome": session.last_outcome,
            "action_count": len(session.action_history),
            "file_count": len(session.file_history),
            "files": session.file_history[-5:],  # Last 5 files
            "workflow_active": session.workflow_state is not None,
            "workflow_state": session.workflow_state,
            "workflow_chain": session.workflow_chain,
        }
    
    def _cleanup_old_sessions(self):
        """Clean up old sessions to maintain max_sessions limit."""
        if len(self._sessions) <= self._max_sessions:
            return
        
        # Sort by last activity
        sorted_sessions = sorted(
            self._sessions.items(),
            key=lambda x: x[1].last_activity
        )
        
        # Remove oldest sessions
        to_remove = len(self._sessions) - self._max_sessions
        for session_id, _ in sorted_sessions[:to_remove]:
            del self._sessions[session_id]
    
    def clear_expired_sessions(self):
        """Clear all expired sessions based on TTL."""
        current_time = time.time()
        expired = [
            sid for sid, session in self._sessions.items()
            if current_time - session.last_activity > self._ttl_seconds
        ]
        for sid in expired:
            del self._sessions[sid]
    
    def get_all_sessions(self) -> List[str]:
        """Get list of all active session IDs."""
        self.clear_expired_sessions()
        return list(self._sessions.keys())
