"""
Jupyter notebook integration for ML experimentation.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import uuid
import json


class NotebookStatus(Enum):
    """Status of a notebook session."""
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    COMPLETED = "completed"


class KernelStatus(Enum):
    """Status of a Jupyter kernel."""
    UNKNOWN = "unknown"
    STARTING = "starting"
    IDLE = "idle"
    BUSY = "busy"
    TERMINATED = "terminated"


@dataclass
class NotebookSession:
    """Jupyter notebook session."""
    session_id: str
    notebook_path: str
    kernel_id: str
    kernel_name: str
    user_id: str
    status: NotebookStatus
    kernel_status: KernelStatus
    cell_outputs: List[Dict[str, Any]] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)


@dataclass
class NotebookTemplate:
    """Template for creating notebooks."""
    template_id: str
    name: str
    description: str
    category: str
    cells: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)


class JupyterIntegration:
    """Integration with Jupyter notebooks."""
    
    def __init__(self, jupyter_url: str = "http://localhost:8888"):
        self.jupyter_url = jupyter_url
        self.sessions: Dict[str, NotebookSession] = {}
        self.templates: Dict[str, NotebookTemplate] = {}
        self._kernels: Dict[str, Dict[str, Any]] = {}
    
    async def create_session(
        self,
        notebook_path: str,
        user_id: str,
        kernel_name: str = "python3"
    ) -> NotebookSession:
        """Create a new notebook session."""
        
        session_id = str(uuid.uuid4())
        kernel_id = await self._start_kernel(kernel_name)
        
        session = NotebookSession(
            session_id=session_id,
            notebook_path=notebook_path,
            kernel_id=kernel_id,
            kernel_name=kernel_name,
            user_id=user_id,
            status=NotebookStatus.IDLE,
            kernel_status=KernelStatus.IDLE
        )
        
        self.sessions[session_id] = session
        
        return session
    
    async def _start_kernel(self, kernel_name: str) -> str:
        """Start a new Jupyter kernel."""
        # Placeholder - in production, use Jupyter API
        kernel_id = str(uuid.uuid4())
        
        self._kernels[kernel_id] = {
            "kernel_name": kernel_name,
            "status": KernelStatus.STARTING,
            "started_at": datetime.utcnow()
        }
        
        return kernel_id
    
    async def execute_cell(
        self,
        session_id: str,
        code: str,
        cell_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a code cell in a session."""
        
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        session.status = NotebookStatus.RUNNING
        session.kernel_status = KernelStatus.BUSY
        session.last_activity = datetime.utcnow()
        
        try:
            # Placeholder - in production, use Jupyter kernel API
            output = await self._execute_code(session.kernel_id, code)
            
            cell_output = {
                "cell_id": cell_id or str(uuid.uuid4()),
                "code": code,
                "output": output,
                "execution_count": len(session.cell_outputs) + 1,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "success"
            }
            
            session.cell_outputs.append(cell_output)
            session.status = NotebookStatus.COMPLETED
            session.kernel_status = KernelStatus.IDLE
            
            return cell_output
            
        except Exception as e:
            session.status = NotebookStatus.ERROR
            session.kernel_status = KernelStatus.IDLE
            
            return {
                "cell_id": cell_id or str(uuid.uuid4()),
                "code": code,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error"
            }
    
    async def _execute_code(self, kernel_id: str, code: str) -> Dict[str, Any]:
        """Execute code in a kernel."""
        # Placeholder - in production, use Jupyter kernel client
        return {
            "text/plain": "Output placeholder",
            "execution_time_ms": 100
        }
    
    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get status of a notebook session."""
        
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        return {
            "session_id": session_id,
            "notebook_path": session.notebook_path,
            "kernel_id": session.kernel_id,
            "kernel_name": session.kernel_name,
            "status": session.status.value,
            "kernel_status": session.kernel_status.value,
            "cell_count": len(session.cell_outputs),
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "idle_seconds": (
                datetime.utcnow() - session.last_activity
            ).total_seconds()
        }
    
    async def interrupt_kernel(self, session_id: str) -> bool:
        """Interrupt the kernel in a session."""
        
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        # Placeholder - in production, send interrupt signal
        session.kernel_status = KernelStatus.IDLE
        session.status = NotebookStatus.IDLE
        
        return True
    
    async def restart_kernel(self, session_id: str) -> bool:
        """Restart the kernel in a session."""
        
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        # Stop old kernel
        await self._stop_kernel(session.kernel_id)
        
        # Start new kernel
        session.kernel_id = await self._start_kernel(session.kernel_name)
        session.kernel_status = KernelStatus.IDLE
        session.status = NotebookStatus.IDLE
        session.cell_outputs = []
        session.variables = {}
        
        return True
    
    async def _stop_kernel(self, kernel_id: str):
        """Stop a Jupyter kernel."""
        if kernel_id in self._kernels:
            self._kernels[kernel_id]["status"] = KernelStatus.TERMINATED
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a notebook session."""
        
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        # Stop kernel
        await self._stop_kernel(session.kernel_id)
        
        del self.sessions[session_id]
        
        return True
    
    async def create_template(
        self,
        name: str,
        description: str,
        category: str,
        cells: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        created_by: str = ""
    ) -> NotebookTemplate:
        """Create a notebook template."""
        
        template = NotebookTemplate(
            template_id=str(uuid.uuid4()),
            name=name,
            description=description,
            category=category,
            cells=cells,
            metadata=metadata or {},
            tags=tags or [],
            created_by=created_by
        )
        
        self.templates[template.template_id] = template
        
        return template
    
    async def list_templates(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """List available notebook templates."""
        
        templates = list(self.templates.values())
        
        if category:
            templates = [t for t in templates if t.category == category]
        
        if tags:
            templates = [
                t for t in templates
                if any(tag in t.tags for tag in tags)
            ]
        
        return [
            {
                "template_id": t.template_id,
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "cell_count": len(t.cells),
                "tags": t.tags,
                "created_by": t.created_by,
                "created_at": t.created_at.isoformat()
            }
            for t in templates
        ]
    
    async def create_notebook_from_template(
        self,
        template_id: str,
        notebook_path: str,
        user_id: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> NotebookSession:
        """Create a notebook from a template."""
        
        template = self.templates.get(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        # Create notebook file from template
        notebook_content = self._generate_notebook_content(
            template, parameters
        )
        
        # Save notebook (placeholder)
        await self._save_notebook(notebook_path, notebook_content)
        
        # Create session
        return await self.create_session(notebook_path, user_id)
    
    def _generate_notebook_content(
        self,
        template: NotebookTemplate,
        parameters: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate notebook content from template."""
        
        cells = []
        for cell in template.cells:
            source = cell["source"]
            
            # Replace parameters
            if parameters:
                for key, value in parameters.items():
                    source = source.replace(f"{{{{{key}}}}}", str(value))
            
            cells.append({
                "cell_type": cell.get("cell_type", "code"),
                "source": source,
                "metadata": cell.get("metadata", {})
            })
        
        return {
            "cells": cells,
            "metadata": template.metadata,
            "nbformat": 4,
            "nbformat_minor": 4
        }
    
    async def _save_notebook(self, path: str, content: Dict[str, Any]):
        """Save notebook to storage."""
        # Placeholder - in production, write to file system
        pass
    
    async def get_variables(self, session_id: str) -> Dict[str, Any]:
        """Get variables from a session."""
        
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Query kernel for variables (placeholder)
        return session.variables
    
    async def export_notebook(
        self,
        session_id: str,
        format: str = "ipynb"
    ) -> Dict[str, Any]:
        """Export notebook in various formats."""
        
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if format == "ipynb":
            return await self._export_ipynb(session)
        elif format == "html":
            return await self._export_html(session)
        elif format == "pdf":
            return await self._export_pdf(session)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    async def _export_ipynb(self, session: NotebookSession) -> Dict[str, Any]:
        """Export as Jupyter notebook format."""
        
        cells = []
        for output in session.cell_outputs:
            cells.append({
                "cell_type": "code",
                "source": output["code"],
                "outputs": [output.get("output", {})],
                "execution_count": output.get("execution_count"),
                "metadata": {}
            })
        
        return {
            "format": "ipynb",
            "content": {
                "cells": cells,
                "metadata": {},
                "nbformat": 4,
                "nbformat_minor": 4
            }
        }
    
    async def _export_html(self, session: NotebookSession) -> Dict[str, Any]:
        """Export as HTML."""
        # Placeholder - convert to HTML
        return {"format": "html", "content": "<html>...</html>"}
    
    async def _export_pdf(self, session: NotebookSession) -> Dict[str, Any]:
        """Export as PDF."""
        # Placeholder - convert to PDF
        return {"format": "pdf", "content": b"..."}
