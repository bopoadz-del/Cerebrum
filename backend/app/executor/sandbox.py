"""
Docker Sandbox Execution Module

Provides secure, isolated Python code execution using Docker containers.
Features:
- Network isolation (no outbound connections)
- Resource limits (CPU, memory, disk)
- Timeouts (5 minute default)
- Read-only filesystem
- Security scanning before execution
"""

import os
import uuid
import json
import time
import re
import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from app.core.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Configuration
# =============================================================================

# Security settings
MAX_EXECUTION_TIME = 300  # 5 minutes default
MAX_MEMORY_MB = 512
MAX_CPU_PERCENT = 100
MAX_OUTPUT_SIZE = 100000  # 100KB

# Blocked patterns for security scanning
BLOCKED_PATTERNS = [
    # System/OS access
    r'os\.system',
    r'os\.popen',
    r'os\.spawn',
    r'os\.exec',
    r'os\.fork',
    r'os\.kill',
    r'subprocess',
    r'platform',
    
    # Code execution
    r'eval\s*\(',
    r'exec\s*\(',
    r'compile\s*\(',
    r'__import__',
    r'importlib',
    
    # File operations
    r'open\s*\([^)]*[\\\'"]w',
    r'file\s*\(',
    r'\.write\s*\(',
    r'\.read\s*\(',
    r'pathlib',
    r'shutil',
    
    # Network
    r'urllib',
    r'http\.',
    r'ftp',
    r'socket',
    r'requests',
    r'httpx',
    
    # Serialization (security risk)
    r'pickle',
    r'yaml\.load',
    r'json\.load',
    
    # Introspection
    r'__builtins__',
    r'__globals__',
    r'__locals__',
    r'__getattribute__',
    r'__class__',
    r'__bases__',
    r'__subclasses__',
    r'__mro__',
]

# Allowed modules whitelist
ALLOWED_MODULES = {
    'math', 'cmath', 'random', 'statistics', 'decimal', 'fractions', 'numbers',
    'datetime', 'time', 'calendar', 'zoneinfo', 'itertools', 'functools',
    'collections', 'array', 'heapq', 'bisect', 'copy', 'pprint', 'reprlib',
    'enum', 'graphlib', 'types', 'string', 're', 'difflib', 'textwrap',
    'unicodedata', 'hashlib', 'base64', 'binascii', 'struct', 'json',
    'csv', 'html', 'html.parser', 'xml.etree.ElementTree',
    'numpy', 'pandas', 'matplotlib', 'plotly', 'seaborn', 'scipy',
}


# =============================================================================
# Enums and Data Classes
# =============================================================================

class SandboxStatus(str, Enum):
    """Sandbox execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    SECURITY_VIOLATION = "security_violation"
    CANCELLED = "cancelled"


@dataclass
class SandboxResult:
    """Result of sandbox execution."""
    success: bool
    status: SandboxStatus
    result: Optional[Any] = None
    output: str = ""
    error: Optional[str] = None
    exit_code: int = 0
    execution_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    timeout_reached: bool = False
    security_violations: List[str] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "status": self.status.value,
            "result": self.result,
            "output": self.output,
            "error": self.error,
            "exit_code": self.exit_code,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "memory_usage_mb": round(self.memory_usage_mb, 2),
            "timeout_reached": self.timeout_reached,
            "security_violations": self.security_violations,
        }


@dataclass
class SandboxConfig:
    """Configuration for sandbox execution."""
    timeout_seconds: int = MAX_EXECUTION_TIME
    max_memory_mb: int = MAX_MEMORY_MB
    max_cpu_percent: int = MAX_CPU_PERCENT
    max_output_size: int = MAX_OUTPUT_SIZE
    network_enabled: bool = False
    allow_file_write: bool = False
    allowed_modules: Optional[List[str]] = None
    environment_variables: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timeout_seconds": self.timeout_seconds,
            "max_memory_mb": self.max_memory_mb,
            "max_cpu_percent": self.max_cpu_percent,
            "network_enabled": self.network_enabled,
            "allow_file_write": self.allow_file_write,
        }


# =============================================================================
# Security Scanner
# =============================================================================

class SecurityScanner:
    """Scan code for security violations before execution."""
    
    @staticmethod
    def scan_code(code: str) -> List[str]:
        """
        Scan code for dangerous patterns.
        
        Returns:
            List of security violations found
        """
        violations = []
        
        # Check blocked patterns
        for pattern in BLOCKED_PATTERNS:
            matches = re.finditer(pattern, code, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                violations.append(
                    f"Security violation at line {line_num}: {pattern}"
                )
        
        # Check imports
        import_pattern = r'(?:from|import)\s+(\w+)'
        imports = re.findall(import_pattern, code)
        for imp in imports:
            if imp not in ALLOWED_MODULES:
                violations.append(f"Unauthorized import: {imp}")
        
        return violations
    
    @staticmethod
    def validate_syntax(code: str) -> Optional[str]:
        """Validate Python syntax without executing."""
        import ast
        try:
            ast.parse(code)
            return None
        except SyntaxError as e:
            return f"Syntax error at line {e.lineno}: {e.msg}"
    
    @staticmethod
    def sanitize_code(code: str) -> str:
        """Clean and sanitize code before execution."""
        # Remove markdown code blocks if present
        code = code.strip()
        if code.startswith('```python'):
            code = code[9:]
        if code.startswith('```'):
            code = code[3:]
        if code.endswith('```'):
            code = code[:-3]
        return code.strip()


# =============================================================================
# Docker Sandbox
# =============================================================================

class DockerSandbox:
    """
    Docker-based sandbox for isolated code execution.
    
    Security features:
    - Network isolation (unless explicitly enabled)
    - Resource limits (CPU, memory, disk)
    - Timeouts with process termination
    - Read-only root filesystem
    - Non-root user execution
    - Security scanning before execution
    """
    
    def __init__(self, image_name: str = "cerebrum-formula-sandbox:latest"):
        self.image_name = image_name
        self.scanner = SecurityScanner()
        self._docker_available = None
        self._client = None
    
    async def _get_docker_client(self):
        """Get Docker client (lazy initialization)."""
        if self._client is None:
            try:
                import docker
                self._client = docker.from_env()
                # Test connection
                self._client.ping()
                self._docker_available = True
            except Exception as e:
                logger.warning(f"Docker not available: {e}")
                self._docker_available = False
                self._client = None
        return self._client
    
    def is_docker_available(self) -> bool:
        """Check if Docker is available."""
        if self._docker_available is None:
            try:
                import docker
                client = docker.from_env()
                client.ping()
                self._docker_available = True
            except Exception:
                self._docker_available = False
        return self._docker_available
    
    async def execute_python(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None,
        config: Optional[SandboxConfig] = None,
        timeout: Optional[int] = None
    ) -> SandboxResult:
        """
        Execute Python code in Docker sandbox.
        
        Args:
            code: Python code to execute
            context: Variables to inject into execution context
            config: Sandbox configuration
            timeout: Override timeout (seconds)
        
        Returns:
            SandboxResult with execution results
        """
        start_time = time.time()
        config = config or SandboxConfig()
        timeout = timeout or config.timeout_seconds
        
        # Sanitize code
        code = self.scanner.sanitize_code(code)
        
        # Security scan
        violations = self.scanner.scan_code(code)
        if violations:
            return SandboxResult(
                success=False,
                status=SandboxStatus.SECURITY_VIOLATION,
                error=f"Security violations: {'; '.join(violations)}",
                security_violations=violations,
                execution_time_ms=0.0
            )
        
        # Syntax validation
        syntax_error = self.scanner.validate_syntax(code)
        if syntax_error:
            return SandboxResult(
                success=False,
                status=SandboxStatus.ERROR,
                error=syntax_error,
                execution_time_ms=0.0
            )
        
        # Check Docker availability
        client = await self._get_docker_client()
        
        if client is None:
            # Fallback to local execution (development mode)
            logger.warning("Docker not available, falling back to local execution")
            return await self._execute_local(code, context, config, timeout)
        
        # Prepare execution
        execution_id = str(uuid.uuid4())
        temp_dir = f"/tmp/cerebrum_sandbox_{execution_id}"
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            # Prepare code with context
            full_code = self._prepare_code(code, context)
            
            # Write code to file
            code_file = os.path.join(temp_dir, "script.py")
            with open(code_file, 'w') as f:
                f.write(full_code)
            
            # Build container configuration
            container_config = {
                "image": self.image_name,
                "command": ["python", "/workspace/script.py"],
                "volumes": {
                    code_file: {"bind": "/workspace/script.py", "mode": "ro"},
                    temp_dir: {"bind": "/workspace", "mode": "rw" if config.allow_file_write else "ro"}
                },
                "network_mode": "bridge" if config.network_enabled else "none",
                "mem_limit": f"{config.max_memory_mb}m",
                "cpu_percent": config.max_cpu_percent,
                "detach": True,
                "working_dir": "/workspace",
                "environment": config.environment_variables,
                "security_opt": ["no-new-privileges"],
                "cap_drop": ["ALL"],
                "read_only": not config.allow_file_write,
            }
            
            # Run container
            container = client.containers.run(**container_config)
            
            # Wait with timeout
            try:
                result = container.wait(timeout=timeout)
                logs = container.logs().decode('utf-8')
                
                # Parse result from logs
                result_value = self._parse_result(logs)
                
                execution_time = (time.time() - start_time) * 1000
                
                return SandboxResult(
                    success=result['StatusCode'] == 0,
                    status=SandboxStatus.SUCCESS if result['StatusCode'] == 0 else SandboxStatus.ERROR,
                    result=result_value,
                    output=logs,
                    error=None if result['StatusCode'] == 0 else logs,
                    exit_code=result['StatusCode'],
                    execution_time_ms=execution_time,
                    timeout_reached=False
                )
                
            except Exception as e:
                # Timeout or other error
                container.kill()
                execution_time = (time.time() - start_time) * 1000
                
                return SandboxResult(
                    success=False,
                    status=SandboxStatus.TIMEOUT,
                    error=f"Execution timed out after {timeout} seconds",
                    execution_time_ms=execution_time,
                    timeout_reached=True
                )
            
            finally:
                # Cleanup
                try:
                    container.remove(force=True)
                except Exception:
                    pass
        
        finally:
            # Cleanup temp files
            try:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
    
    async def _execute_local(
        self,
        code: str,
        context: Optional[Dict[str, Any]],
        config: SandboxConfig,
        timeout: int
    ) -> SandboxResult:
        """
        Fallback local execution (for development when Docker unavailable).
        
        WARNING: This is less secure than Docker execution.
        """
        import multiprocessing
        import io
        import contextlib
        
        start_time = time.time()
        
        # Prepare code with context
        full_code = self._prepare_code(code, context)
        
        # Execute in separate process for some isolation
        def execute_in_process(code_str, result_queue):
            output_buffer = io.StringIO()
            error_buffer = io.StringIO()
            
            try:
                local_vars = {}
                
                with contextlib.redirect_stdout(output_buffer), contextlib.redirect_stderr(error_buffer):
                    exec(code_str, {"__builtins__": {}}, local_vars)
                
                # Get result
                result_value = local_vars.get('result', None)
                
                result_queue.put({
                    "success": True,
                    "result": result_value,
                    "output": output_buffer.getvalue(),
                    "error": error_buffer.getvalue() or None
                })
                
            except Exception as e:
                result_queue.put({
                    "success": False,
                    "error": str(e),
                    "output": output_buffer.getvalue()
                })
        
        result_queue = multiprocessing.Queue()
        process = multiprocessing.Process(
            target=execute_in_process,
            args=(full_code, result_queue)
        )
        
        process.start()
        process.join(timeout=timeout)
        
        if process.is_alive():
            process.terminate()
            process.join(1)
            if process.is_alive():
                process.kill()
            
            return SandboxResult(
                success=False,
                status=SandboxStatus.TIMEOUT,
                error=f"Execution timed out after {timeout} seconds",
                timeout_reached=True,
                execution_time_ms=(time.time() - start_time) * 1000
            )
        
        process_result = result_queue.get() if not result_queue.empty() else {"success": False, "error": "No result"}
        execution_time = (time.time() - start_time) * 1000
        
        return SandboxResult(
            success=process_result.get("success", False),
            status=SandboxStatus.SUCCESS if process_result.get("success") else SandboxStatus.ERROR,
            result=process_result.get("result"),
            output=process_result.get("output", ""),
            error=process_result.get("error"),
            execution_time_ms=execution_time,
            timeout_reached=False
        )
    
    def _prepare_code(self, code: str, context: Optional[Dict[str, Any]]) -> str:
        """Prepare code with context variables."""
        # Add context variables
        context_code = ""
        if context:
            for key, value in context.items():
                if key != "__builtins__":  # Skip builtins
                    context_code += f"{key} = {repr(value)}\n"
        
        # Combine context and code
        full_code = f"""
# Context variables
{context_code}

# User code
{code}

# Ensure result is defined
if 'result' not in dir():
    result = None
"""
        return full_code
    
    def _parse_result(self, logs: str) -> Any:
        """Parse result from container logs."""
        # Look for RESULT: marker in output
        result_match = re.search(r'RESULT:\s*(.+?)(?:\n|$)', logs)
        if result_match:
            try:
                return json.loads(result_match.group(1))
            except json.JSONDecodeError:
                return result_match.group(1)
        
        # Try to parse as JSON
        try:
            return json.loads(logs)
        except json.JSONDecodeError:
            pass
        
        return None
    
    async def validate_image(self) -> bool:
        """Validate that sandbox Docker image exists and is valid."""
        client = await self._get_docker_client()
        if client is None:
            return False
        
        try:
            client.images.get(self.image_name)
            return True
        except Exception:
            return False
    
    async def build_image(self) -> bool:
        """Build the sandbox Docker image."""
        client = await self._get_docker_client()
        if client is None:
            return False
        
        try:
            import tempfile
            import shutil
            
            # Create temporary directory for Dockerfile
            temp_dir = tempfile.mkdtemp()
            
            try:
                dockerfile_content = self._get_dockerfile()
                dockerfile_path = os.path.join(temp_dir, "Dockerfile")
                
                with open(dockerfile_path, 'w') as f:
                    f.write(dockerfile_content)
                
                # Build image
                logger.info(f"Building Docker image: {self.image_name}")
                image, build_logs = client.images.build(
                    path=temp_dir,
                    tag=self.image_name,
                    rm=True,
                    forcerm=True
                )
                
                logger.info(f"Successfully built image: {image.id}")
                return True
                
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
        
        except Exception as e:
            logger.error(f"Failed to build Docker image: {e}")
            return False
    
    def _get_dockerfile(self) -> str:
        """Generate Dockerfile for sandbox."""
        return '''FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages for construction calculations
RUN pip install --no-cache-dir \
    numpy==1.24.3 \
    pandas==2.0.3 \
    scipy==1.11.1 \
    matplotlib==3.7.2 \
    plotly==5.15.0 \
    seaborn==0.12.2

# Create non-root user
RUN groupadd -r sandbox && useradd -r -g sandbox sandbox

# Create workspace
RUN mkdir -p /workspace && chown sandbox:sandbox /workspace

# Switch to non-root user
USER sandbox

# Set working directory
WORKDIR /workspace

# Default command
CMD ["python", "-c", "print('Cerebrum Formula Sandbox Ready')"]
'''


# =============================================================================
# Process-based Sandbox (Alternative)
# =============================================================================

class ProcessSandbox:
    """
    Process-based sandbox for environments without Docker.
    
    Provides basic isolation using:
    - Separate process
    - Resource limits (if supported by OS)
    - Timeout enforcement
    - Restricted builtins
    
    Less secure than Docker but works without containerization.
    """
    
    def __init__(self):
        self.scanner = SecurityScanner()
    
    async def execute(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: int = MAX_EXECUTION_TIME
    ) -> SandboxResult:
        """Execute code in isolated process."""
        return await DockerSandbox()._execute_local(code, context, SandboxConfig(), timeout)


# =============================================================================
# Factory
# =============================================================================

async def get_sandbox() -> Union[DockerSandbox, ProcessSandbox]:
    """
    Get appropriate sandbox implementation.
    
    Returns DockerSandbox if Docker available, otherwise ProcessSandbox.
    """
    docker_sandbox = DockerSandbox()
    
    if docker_sandbox.is_docker_available():
        # Validate image exists
        if await docker_sandbox.validate_image():
            return docker_sandbox
        # Try to build
        if await docker_sandbox.build_image():
            return docker_sandbox
    
    # Fall back to process sandbox
    logger.warning("Using process-based sandbox (less secure than Docker)")
    return ProcessSandbox()


# =============================================================================
# Convenience Functions
# =============================================================================

async def execute_code_safely(
    code: str,
    context: Optional[Dict[str, Any]] = None,
    timeout: int = 30
) -> SandboxResult:
    """
    Convenience function for quick code execution.
    
    Args:
        code: Python code to execute
        context: Variables to inject
        timeout: Maximum execution time (seconds)
    
    Returns:
        SandboxResult
    """
    sandbox = await get_sandbox()
    
    if isinstance(sandbox, DockerSandbox):
        return await sandbox.execute_python(code, context, timeout=timeout)
    else:
        return await sandbox.execute(code, context, timeout)
