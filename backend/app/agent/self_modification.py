"""
Self-Modification Engine for Cerebrum Agent

Enables the agent to:
- Generate new layers and tools
- Modify existing code safely
- Register capabilities dynamically
- Track all changes with git

SAFETY FIRST: All modifications go through approval gates and git tracking.
"""

import os
import re
import ast
import subprocess
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ModificationType(Enum):
    CREATE_LAYER = "create_layer"
    CREATE_TOOL = "create_tool"
    MODIFY_CODE = "modify_code"
    REFACTOR = "refactor"
    DELETE = "delete"


class ModificationStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class CodeChange:
    """Represents a single code change."""
    file_path: str
    original_content: Optional[str]
    new_content: str
    change_type: str  # "create", "modify", "delete"
    description: str
    line_numbers: Optional[Tuple[int, int]] = None


@dataclass
class ModificationRequest:
    """A request to modify the codebase."""
    id: str
    timestamp: str
    type: ModificationType
    description: str
    changes: List[CodeChange]
    status: ModificationStatus = ModificationStatus.PENDING
    approved_by: Optional[str] = None
    applied_at: Optional[str] = None
    rollback_commit: Optional[str] = None
    test_results: Optional[Dict] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GeneratedLayer:
    """Specification for a generated layer."""
    name: str
    description: str
    purpose: str
    tools: List[Dict[str, Any]]
    dependencies: List[str]
    file_content: str


@dataclass
class RollbackPoint:
    """Git rollback point for safety."""
    commit_hash: str
    branch: str
    timestamp: str
    description: str


class GitManager:
    """Manages git operations for self-modification."""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.modifications_branch = "agent-modifications"
        
    def _run_git(self, args: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """Run a git command."""
        result = subprocess.run(
            ["git"] + args,
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )
        if check and result.returncode != 0:
            raise RuntimeError(f"Git command failed: {result.stderr}")
        return result
    
    def ensure_clean_state(self) -> bool:
        """Check if working directory is clean."""
        result = self._run_git(["status", "--porcelain"], check=False)
        return result.stdout.strip() == ""
    
    def create_checkpoint(self, description: str) -> RollbackPoint:
        """Create a git checkpoint before modifications."""
        timestamp = datetime.now().isoformat()
        
        # Stage all changes
        self._run_git(["add", "."])
        
        # Commit with checkpoint message
        commit_msg = f"[AGENT-CHECKPOINT] {description}\n\nTimestamp: {timestamp}"
        self._run_git(["commit", "-m", commit_msg], check=False)
        
        # Get commit hash
        result = self._run_git(["rev-parse", "HEAD"])
        commit_hash = result.stdout.strip()
        
        # Get current branch
        result = self._run_git(["rev-parse", "--abbrev-ref", "HEAD"])
        branch = result.stdout.strip()
        
        return RollbackPoint(
            commit_hash=commit_hash,
            branch=branch,
            timestamp=timestamp,
            description=description
        )
    
    def rollback_to(self, rollback_point: RollbackPoint) -> bool:
        """Rollback to a previous checkpoint."""
        try:
            # Hard reset to the checkpoint commit
            self._run_git(["reset", "--hard", rollback_point.commit_hash])
            logger.info(f"Rolled back to {rollback_point.commit_hash}")
            return True
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False
    
    def commit_changes(self, message: str, author: str = "Cerebrum Agent") -> str:
        """Commit current changes."""
        self._run_git(["add", "."])
        
        # Set author for this commit
        env = os.environ.copy()
        env["GIT_AUTHOR_NAME"] = author
        env["GIT_AUTHOR_EMAIL"] = "agent@cerebrum.local"
        
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            env=env
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Commit failed: {result.stderr}")
        
        # Get new commit hash
        result = self._run_git(["rev-parse", "HEAD"])
        return result.stdout.strip()
    
    def get_diff(self) -> str:
        """Get diff of current changes."""
        result = self._run_git(["diff", "--cached"], check=False)
        return result.stdout
    
    def log_modifications(self) -> List[Dict]:
        """Get log of agent modifications."""
        result = self._run_git(
            ["log", "--grep=\[AGENT-", "--pretty=format:%H|%ai|%s"],
            check=False
        )
        
        modifications = []
        for line in result.stdout.strip().split("\n"):
            if "|" in line:
                parts = line.split("|", 2)
                if len(parts) == 3:
                    modifications.append({
                        "commit": parts[0],
                        "timestamp": parts[1],
                        "message": parts[2]
                    })
        
        return modifications


class CodeSafetyChecker:
    """Validates code safety before applying changes."""
    
    DANGEROUS_PATTERNS = [
        (r"os\.system\s*\(", "Dangerous: os.system() detected"),
        (r"subprocess\.call\s*\([^)]*shell\s*=\s*True", "Dangerous: shell=True in subprocess"),
        (r"eval\s*\(", "Dangerous: eval() detected"),
        (r"exec\s*\(", "Dangerous: exec() detected"),
        (r"__import__\s*\(", "Suspicious: dynamic import"),
        (r"open\s*\([^)]*['\"]w['\"]", "Caution: file write operation"),
        (r"rm\s+-rf", "Dangerous: rm -rf detected"),
        (r" shutil\.rmtree", "Caution: directory deletion"),
    ]
    
    def __init__(self):
        self.warnings: List[str] = []
        self.errors: List[str] = []
    
    def check_syntax(self, code: str) -> bool:
        """Check if Python code is syntactically valid."""
        try:
            ast.parse(code)
            return True
        except SyntaxError as e:
            self.errors.append(f"Syntax error: {e}")
            return False
    
    def check_safety(self, code: str) -> Tuple[bool, List[str], List[str]]:
        """
        Check code for dangerous patterns.
        Returns: (is_safe, warnings, errors)
        """
        self.warnings = []
        self.errors = []
        
        # Check syntax first
        if not self.check_syntax(code):
            return False, self.warnings, self.errors
        
        # Check for dangerous patterns
        for pattern, message in self.DANGEROUS_PATTERNS:
            if re.search(pattern, code):
                if "Dangerous" in message:
                    self.errors.append(message)
                else:
                    self.warnings.append(message)
        
        is_safe = len(self.errors) == 0
        return is_safe, self.warnings, self.errors
    
    def check_imports(self, code: str) -> List[str]:
        """Extract and validate imports from code."""
        imports = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module)
        except:
            pass
        return imports


class LayerGenerator:
    """Generates new layers for the Cerebrum architecture."""
    
    LAYER_TEMPLATE = '''"""
{layer_name} Layer - Auto-generated by Cerebrum Agent
Generated at: {timestamp}
Purpose: {purpose}
"""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Layer metadata
LAYER_NAME = "{layer_name}"
LAYER_DESCRIPTION = "{description}"
LAYER_DEPENDENCIES = {dependencies}

{tool_definitions}

# Tool registry for agent integration
TOOLS = {{
{tool_registry}
}}

def register_tools(agent):
    """Register all tools with the agent."""
    for name, func in TOOLS.items():
        agent.tools[name] = func
'''

    TOOL_TEMPLATE = '''
async def {tool_name}({params}) -> Dict[str, Any]:
    """
    {description}
    
    Args:
{args_doc}
    
    Returns:
        Dict with operation result
    """
    try:
        # TODO: Implement {tool_name} functionality
{implementation}
        
        return {{
            "success": True,
            "tool": "{tool_name}",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }}
    except Exception as e:
        logger.error(f"{tool_name} failed: {{e}}")
        return {{
            "success": False,
            "tool": "{tool_name}",
            "error": str(e)
        }}
'''

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.safety = CodeSafetyChecker()
    
    def generate_layer(self, spec: Dict[str, Any]) -> GeneratedLayer:
        """Generate a new layer from specification."""
        name = spec["name"]
        purpose = spec.get("purpose", "Auto-generated layer")
        description = spec.get("description", purpose)
        tools_spec = spec.get("tools", [])
        dependencies = spec.get("dependencies", [])
        
        # Generate tool code
        tool_definitions = []
        tool_registry_entries = []
        
        for tool in tools_spec:
            tool_code = self._generate_tool(tool)
            tool_definitions.append(tool_code)
            tool_registry_entries.append(f'    "{tool["name"]}": {tool["name"]}')
        
        # Build layer file
        layer_content = self.LAYER_TEMPLATE.format(
            layer_name=name.capitalize(),
            timestamp=datetime.now().isoformat(),
            purpose=purpose,
            description=description,
            dependencies=repr(dependencies),
            tool_definitions="\n".join(tool_definitions),
            tool_registry=",\n".join(tool_registry_entries)
        )
        
        # Validate generated code
        is_safe, warnings, errors = self.safety.check_safety(layer_content)
        if not is_safe:
            raise ValueError(f"Generated code has safety issues: {errors}")
        
        return GeneratedLayer(
            name=name,
            description=description,
            purpose=purpose,
            tools=tools_spec,
            dependencies=dependencies,
            file_content=layer_content
        )
    
    def _generate_tool(self, spec: Dict[str, Any]) -> str:
        """Generate a single tool function."""
        name = spec["name"]
        description = spec.get("description", f"Tool: {name}")
        params_spec = spec.get("params", [])
        
        # Build parameters
        params = ["**kwargs"]
        args_doc = []
        for param in params_spec:
            param_name = param["name"]
            param_type = param.get("type", "Any")
            param_default = param.get("default", "None")
            params.append(f'{param_name}: {param_type} = kwargs.get("{param_name}", {repr(param_default)})')
            args_doc.append(f'        {param_name} ({param_type}): {param.get("description", "")}')
        
        # Generate implementation stub
        implementation_lines = [
            '        result = {',
            '            "status": "stub",',
            '            "message": "Tool implementation pending"',
            '        }'
        ]
        
        return self.TOOL_TEMPLATE.format(
            tool_name=name,
            description=description,
            params=", ".join(params),
            args_doc="\n".join(args_doc) if args_doc else "        # No arguments",
            implementation="\n".join(implementation_lines)
        )


class SelfModificationEngine:
    """
    The core self-modification engine.
    
    This is the 'brain' that allows Cerebrum to extend itself.
    """
    
    def __init__(self, repo_path: str, require_approval: bool = True):
        self.repo_path = Path(repo_path)
        self.require_approval = require_approval
        self.git = GitManager(repo_path)
        self.safety = CodeSafetyChecker()
        self.layer_gen = LayerGenerator(repo_path)
        
        # Pending modifications queue
        self.pending_requests: Dict[str, ModificationRequest] = {}
        
        # Modification history
        self.history_file = self.repo_path / ".agent_modifications.json"
        self._load_history()
    
    def _load_history(self):
        """Load modification history."""
        if self.history_file.exists():
            with open(self.history_file) as f:
                self.history = json.load(f)
        else:
            self.history = []
    
    def _save_history(self):
        """Save modification history."""
        with open(self.history_file, "w") as f:
            json.dump(self.history, f, indent=2)
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_suffix = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:6]
        return f"mod_{timestamp}_{hash_suffix}"
    
    # ============ LAYER CREATION ============
    
    def request_create_layer(self, spec: Dict[str, Any]) -> ModificationRequest:
        """Request creation of a new layer."""
        # Generate the layer
        layer = self.layer_gen.generate_layer(spec)
        
        # Determine file path
        layer_file = self.repo_path / "backend" / "app" / "api" / "v1" / "endpoints" / f"{layer.name}.py"
        
        # Check if file already exists
        if layer_file.exists():
            raise FileExistsError(f"Layer file already exists: {layer_file}")
        
        # Create change
        change = CodeChange(
            file_path=str(layer_file.relative_to(self.repo_path)),
            original_content=None,
            new_content=layer.file_content,
            change_type="create",
            description=f"Create {layer.name} layer with {len(layer.tools)} tools"
        )
        
        # Create modification request
        request = ModificationRequest(
            id=self._generate_request_id(),
            timestamp=datetime.now().isoformat(),
            type=ModificationType.CREATE_LAYER,
            description=f"Create new layer: {layer.name}",
            changes=[change],
            metadata={
                "layer_name": layer.name,
                "tool_count": len(layer.tools),
                "dependencies": layer.dependencies
            }
        )
        
        self.pending_requests[request.id] = request
        
        if not self.require_approval:
            self.apply_modification(request.id)
        
        return request
    
    # ============ CODE MODIFICATION ============
    
    def request_modify_code(self, file_path: str, 
                           original_pattern: str,
                           replacement: str,
                           description: str) -> ModificationRequest:
        """Request modification of existing code."""
        full_path = self.repo_path / file_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Read original content
        with open(full_path) as f:
            original_content = f.read()
        
        # Apply replacement
        new_content = original_content.replace(original_pattern, replacement)
        
        if new_content == original_content:
            raise ValueError("Pattern not found in file")
        
        # Validate new code
        is_safe, warnings, errors = self.safety.check_safety(new_content)
        if not is_safe:
            raise ValueError(f"Modified code has safety issues: {errors}")
        
        # Create change
        change = CodeChange(
            file_path=file_path,
            original_content=original_content,
            new_content=new_content,
            change_type="modify",
            description=description
        )
        
        # Create request
        request = ModificationRequest(
            id=self._generate_request_id(),
            timestamp=datetime.now().isoformat(),
            type=ModificationType.MODIFY_CODE,
            description=description,
            changes=[change],
            metadata={
                "warnings": warnings
            }
        )
        
        self.pending_requests[request.id] = request
        
        if not self.require_approval:
            self.apply_modification(request.id)
        
        return request
    
    def request_refactor(self, file_path: str,
                        target: str,
                        improvement: str) -> ModificationRequest:
        """Request code refactoring."""
        # This is a higher-level modification that uses AI to refactor
        description = f"Refactor {target} in {file_path}: {improvement}"
        
        # For now, create a placeholder that documents the intent
        # In full implementation, this would call the LLM to do the refactoring
        request = ModificationRequest(
            id=self._generate_request_id(),
            timestamp=datetime.now().isoformat(),
            type=ModificationType.REFACTOR,
            description=description,
            changes=[],  # Would be populated by LLM
            metadata={
                "target": target,
                "improvement": improvement,
                "file_path": file_path
            }
        )
        
        self.pending_requests[request.id] = request
        return request
    
    # ============ APPROVAL & APPLICATION ============
    
    def get_pending_requests(self) -> List[ModificationRequest]:
        """Get all pending modification requests."""
        return [
            r for r in self.pending_requests.values()
            if r.status == ModificationStatus.PENDING
        ]
    
    def approve_request(self, request_id: str, approver: str) -> bool:
        """Approve a pending modification request."""
        if request_id not in self.pending_requests:
            return False
        
        request = self.pending_requests[request_id]
        request.status = ModificationStatus.APPROVED
        request.approved_by = approver
        
        return True
    
    def reject_request(self, request_id: str, reason: str) -> bool:
        """Reject a pending modification request."""
        if request_id not in self.pending_requests:
            return False
        
        request = self.pending_requests[request_id]
        request.status = ModificationStatus.REJECTED
        request.metadata["rejection_reason"] = reason
        
        return True
    
    def apply_modification(self, request_id: str) -> Dict[str, Any]:
        """
        Apply an approved modification.
        
        Steps:
        1. Create git checkpoint
        2. Apply changes
        3. Run tests
        4. Commit if successful
        5. Rollback if failed
        """
        if request_id not in self.pending_requests:
            return {"success": False, "error": "Request not found"}
        
        request = self.pending_requests[request_id]
        
        if request.status != ModificationStatus.APPROVED and self.require_approval:
            return {"success": False, "error": "Request not approved"}
        
        results = {
            "request_id": request_id,
            "steps": []
        }
        
        rollback_point = None
        
        try:
            # Step 1: Create checkpoint
            rollback_point = self.git.create_checkpoint(
                f"Pre-modification: {request.description}"
            )
            request.rollback_commit = rollback_point.commit_hash
            results["steps"].append({"step": "checkpoint", "commit": rollback_point.commit_hash})
            
            # Step 2: Apply changes
            for change in request.changes:
                file_path = self.repo_path / change.file_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(file_path, "w") as f:
                    f.write(change.new_content)
                
                results["steps"].append({"step": "write", "file": change.file_path})
            
            # Step 3: Run validation
            validation_result = self._validate_changes(request)
            request.test_results = validation_result
            results["steps"].append({"step": "validate", "result": validation_result})
            
            if not validation_result.get("success", False):
                raise RuntimeError(f"Validation failed: {validation_result.get('errors')}")
            
            # Step 4: Commit
            commit_hash = self.git.commit_changes(
                f"[AGENT-MOD] {request.description}\n\nRequest ID: {request_id}",
                author="Cerebrum Agent"
            )
            results["steps"].append({"step": "commit", "hash": commit_hash})
            
            # Step 5: Update status
            request.status = ModificationStatus.APPLIED
            request.applied_at = datetime.now().isoformat()
            
            # Save to history
            self.history.append(asdict(request))
            self._save_history()
            
            results["success"] = True
            
        except Exception as e:
            logger.error(f"Modification failed: {e}")
            
            # Rollback on failure
            if rollback_point:
                self.git.rollback_to(rollback_point)
                results["steps"].append({"step": "rollback", "commit": rollback_point.commit_hash})
            
            request.status = ModificationStatus.FAILED
            request.metadata["failure_reason"] = str(e)
            results["success"] = False
            results["error"] = str(e)
        
        return results
    
    def _validate_changes(self, request: ModificationRequest) -> Dict[str, Any]:
        """Validate applied changes."""
        errors = []
        warnings = []
        
        for change in request.changes:
            file_path = self.repo_path / change.file_path
            
            # Check file exists
            if not file_path.exists():
                errors.append(f"File not created: {change.file_path}")
                continue
            
            # Read and validate content
            with open(file_path) as f:
                content = f.read()
            
            # Python syntax check for .py files
            if file_path.suffix == ".py":
                is_safe, ws, errs = self.safety.check_safety(content)
                warnings.extend(ws)
                errors.extend(errs)
        
        return {
            "success": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def rollback_modification(self, request_id: str) -> bool:
        """Rollback a previously applied modification."""
        if request_id not in self.pending_requests:
            return False
        
        request = self.pending_requests[request_id]
        
        if request.status != ModificationStatus.APPLIED:
            return False
        
        if not request.rollback_commit:
            return False
        
        rollback_point = RollbackPoint(
            commit_hash=request.rollback_commit,
            branch="main",  # Assume main for now
            timestamp=request.timestamp,
            description=f"Rollback of {request_id}"
        )
        
        success = self.git.rollback_to(rollback_point)
        
        if success:
            request.status = ModificationStatus.ROLLED_BACK
            request.metadata["rolled_back_at"] = datetime.now().isoformat()
        
        return success
    
    # ============ DYNAMIC REGISTRATION ============
    
    def register_capability(self, layer_name: str, tool_name: str, 
                           handler: Callable) -> Dict[str, Any]:
        """
        Dynamically register a capability at runtime.
        
        This doesn't modify files — it registers with the running agent.
        """
        # This would integrate with the EnhancedCerebrumAgent
        return {
            "success": True,
            "layer": layer_name,
            "tool": tool_name,
            "registered_at": datetime.now().isoformat(),
            "note": "Runtime registration (not persisted to disk)"
        }
    
    # ============ STATUS & HISTORY ============
    
    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        return {
            "repo_path": str(self.repo_path),
            "require_approval": self.require_approval,
            "pending_count": len(self.get_pending_requests()),
            "history_count": len(self.history),
            "git_clean": self.git.ensure_clean_state(),
            "recent_modifications": self.history[-5:] if self.history else []
        }
    
    def get_request_details(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a specific request."""
        if request_id in self.pending_requests:
            return asdict(self.pending_requests[request_id])
        
        # Check history
        for entry in self.history:
            if entry.get("id") == request_id:
                return entry
        
        return None


# Singleton instance
_modification_engine: Optional[SelfModificationEngine] = None

def get_modification_engine(repo_path: Optional[str] = None,
                            require_approval: bool = True) -> SelfModificationEngine:
    """Get or create the modification engine singleton."""
    global _modification_engine
    if _modification_engine is None:
        if repo_path is None:
            repo_path = "/root/.openclaw/workspace/cerebrum-fix"
        _modification_engine = SelfModificationEngine(repo_path, require_approval)
    return _modification_engine
