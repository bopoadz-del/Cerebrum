"""
Docker Sandbox Execution

Isolated code execution environment with 5-minute timeout.
"""
import os
import uuid
import tempfile
import subprocess
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import docker
from docker.errors import ContainerError, ImageNotFound

logger = logging.getLogger(__name__)


@dataclass
class SandboxResult:
    """Result of sandbox execution."""
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    execution_time_ms: float
    timeout_reached: bool
    security_violations: List[str]


class DockerSandbox:
    """
    Docker-based sandbox for isolated code execution.
    
    Security features:
    - Network isolation (no outbound connections)
    - Resource limits (CPU, memory)
    - Read-only filesystem
    - 5-minute timeout
    - No privilege escalation
    """
    
    # Security limits
    MAX_EXECUTION_TIME = 300  # 5 minutes
    MEMORY_LIMIT = "512m"
    CPU_LIMIT = 1.0
    
    # Blocked imports/patterns
    BLOCKED_MODULES = [
        "os.system", "subprocess", "eval", "exec",
        "__import__", "compile", "open", "file",
        "socket", "urllib", "http", "ftplib",
        "pickle", "yaml.load", "json.load"
    ]
    
    def __init__(self):
        self.docker_client = docker.from_env()
        self.image_name = "cerebrum-sandbox:latest"
        self._ensure_image()
    
    def _ensure_image(self):
        """Ensure sandbox Docker image exists."""
        try:
            self.docker_client.images.get(self.image_name)
        except ImageNotFound:
            logger.info("Building sandbox image...")
            self._build_sandbox_image()
    
    def _build_sandbox_image(self):
        """Build the sandbox Docker image."""
        dockerfile = '''
FROM python:3.11-slim

# Create non-root user
RUN useradd -m -u 1000 sandbox

# Install security tools
RUN pip install --no-cache-dir bandit safety

# Set up workspace
WORKDIR /workspace
RUN chown sandbox:sandbox /workspace

# Switch to non-root user
USER sandbox

# Default command
CMD ["python", "-c", "print('Sandbox ready')"]
'''
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "Dockerfile"), "w") as f:
                f.write(dockerfile)
            
            self.docker_client.images.build(
                path=tmpdir,
                tag=self.image_name,
                rm=True
            )
    
    def execute_python(
        self,
        code: str,
        timeout: int = MAX_EXECUTION_TIME,
        allowed_imports: Optional[List[str]] = None
    ) -> SandboxResult:
        """
        Execute Python code in sandbox.
        
        Args:
            code: Python code to execute
            timeout: Maximum execution time in seconds
            allowed_imports: List of allowed imports (None = check all)
        
        Returns:
            SandboxResult with execution results
        """
        start_time = datetime.utcnow()
        
        # Pre-execution security scan
        security_violations = self._scan_code(code, allowed_imports)
        if security_violations:
            return SandboxResult(
                success=False,
                stdout="",
                stderr="",
                exit_code=-1,
                execution_time_ms=0,
                timeout_reached=False,
                security_violations=security_violations
            )
        
        # Create temporary file with code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            # Wrap code in try-except for better error handling
            wrapped_code = f'''
import sys
import traceback

try:
{chr(10).join("    " + line for line in code.split(chr(10)))}
except Exception as e:
    print(f"ERROR: {{e}}", file=sys.stderr)
    traceback.print_exc()
    sys.exit(1)
'''
            f.write(wrapped_code)
            code_file = f.name
        
        try:
            # Run in Docker container
            container = self.docker_client.containers.run(
                self.image_name,
                command=f"python /workspace/code.py",
                volumes={code_file: {"bind": "/workspace/code.py", "mode": "ro"}},
                network_mode="none",  # No network access
                mem_limit=self.MEMORY_LIMIT,
                cpu_quota=int(self.CPU_LIMIT * 100000),
                read_only=True,
                user="sandbox",
                detach=True,
                working_dir="/workspace"
            )
            
            # Wait for completion with timeout
            try:
                result = container.wait(timeout=timeout)
                logs = container.logs().decode('utf-8')
                
                # Parse stdout/stderr
                stdout_lines = []
                stderr_lines = []
                for line in logs.split('\n'):
                    if line.startswith('ERROR:'):
                        stderr_lines.append(line)
                    else:
                        stdout_lines.append(line)
                
                exit_code = result['StatusCode']
                
            except Exception as e:
                # Timeout or other error
                container.kill()
                exit_code = -1
                stdout_lines = []
                stderr_lines = [str(e)]
            
            finally:
                # Cleanup
                try:
                    container.remove(force=True)
                except:
                    pass
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return SandboxResult(
                success=exit_code == 0,
                stdout='\n'.join(stdout_lines),
                stderr='\n'.join(stderr_lines),
                exit_code=exit_code,
                execution_time_ms=execution_time,
                timeout_reached=execution_time >= timeout * 1000,
                security_violations=[]
            )
        
        finally:
            # Cleanup temp file
            try:
                os.unlink(code_file)
            except:
                pass
    
    def execute_tests(
        self,
        code: str,
        test_code: str,
        timeout: int = MAX_EXECUTION_TIME
    ) -> SandboxResult:
        """
        Execute code with pytest tests.
        
        Args:
            code: Main code to test
            test_code: Pytest test code
            timeout: Maximum execution time
        
        Returns:
            SandboxResult with test results
        """
        # Combine code and tests
        full_code = f'''
{code}

# Tests
{test_code}

# Run pytest
if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
'''
        
        return self.execute_python(full_code, timeout)
    
    def _scan_code(
        self,
        code: str,
        allowed_imports: Optional[List[str]] = None
    ) -> List[str]:
        """
        Scan code for security violations.
        
        Returns:
            List of security violations found
        """
        violations = []
        
        # Check for blocked patterns
        for pattern in self.BLOCKED_MODULES:
            if pattern in code:
                violations.append(f"Blocked pattern detected: {pattern}")
        
        # Check imports
        if allowed_imports is not None:
            import re
            import_statements = re.findall(r'(?:from|import)\s+(\w+)', code)
            for imp in import_statements:
                if imp not in allowed_imports:
                    violations.append(f"Unauthorized import: {imp}")
        
        return violations
    
    def validate_syntax(self, code: str, language: str = "python") -> List[str]:
        """Validate code syntax without execution."""
        errors = []
        
        if language == "python":
            import ast
            try:
                ast.parse(code)
            except SyntaxError as e:
                errors.append(f"Syntax error at line {e.lineno}: {e.msg}")
        
        return errors


class SandboxManager:
    """Manages multiple sandbox instances and execution queue."""
    
    def __init__(self, max_concurrent: int = 5):
        self.sandbox = DockerSandbox()
        self.max_concurrent = max_concurrent
        self.execution_queue: List[Dict[str, Any]] = []
        self.results: Dict[str, SandboxResult] = {}
    
    async def submit(
        self,
        code: str,
        language: str = "python",
        timeout: int = 300
    ) -> str:
        """Submit code for execution and return job ID."""
        job_id = str(uuid.uuid4())
        
        self.execution_queue.append({
            "job_id": job_id,
            "code": code,
            "language": language,
            "timeout": timeout,
            "submitted_at": datetime.utcnow()
        })
        
        return job_id
    
    def get_result(self, job_id: str) -> Optional[SandboxResult]:
        """Get execution result for a job."""
        return self.results.get(job_id)
    
    def cleanup_old_results(self, max_age_minutes: int = 60):
        """Clean up old execution results."""
        cutoff = datetime.utcnow() - timedelta(minutes=max_age_minutes)
        to_remove = [
            job_id for job_id, result in self.results.items()
            if result and datetime.utcnow() - timedelta(minutes=max_age_minutes) > cutoff
        ]
        for job_id in to_remove:
            del self.results[job_id]
