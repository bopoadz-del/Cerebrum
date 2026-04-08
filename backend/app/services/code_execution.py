"""
Safe Code Execution Service for Cerebrum AI

Provides sandboxed Python code execution with security restrictions.
Similar to Kimi chat's code execution capabilities.
"""

import ast
import builtins
import contextlib
import io
import logging
import multiprocessing
import os
import re
import signal
import sys
import tempfile
import traceback
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from concurrent.futures import ProcessPoolExecutor, TimeoutError
import resource

logger = logging.getLogger(__name__)

# Security: Restricted built-ins
ALLOWED_BUILTINS = {
    'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'bytearray', 'bytes',
    'chr', 'complex', 'dict', 'divmod', 'enumerate', 'filter', 'float',
    'format', 'frozenset', 'hasattr', 'hash', 'hex', 'id', 'int',
    'isinstance', 'issubclass', 'iter', 'len', 'list', 'map', 'max',
    'memoryview', 'min', 'next', 'oct', 'ord', 'pow', 'print', 'property',
    'range', 'repr', 'reversed', 'round', 'set', 'slice', 'sorted',
    'staticmethod', 'str', 'sum', 'super', 'tuple', 'type', 'vars',
    'zip', '__import__', 'True', 'False', 'None'
}

# Security: Allowed modules
ALLOWED_MODULES = {
    'math', 'random', 'statistics', 'decimal', 'fractions', 'numbers',
    'datetime', 'time', 'calendar', 'itertools', 'functools', 'collections',
    'heapq', 'bisect', 'copy', 'pprint', 'reprlib', 'enum', 'types',
    'string', 're', 'difflib', 'textwrap', 'unicodedata', 'hashlib',
    'base64', 'binascii', 'struct', 'json', 'csv', 'html',
    'numpy', 'pandas', 'matplotlib', 'plotly', 'seaborn'
}

# Security: Dangerous patterns to block
DANGEROUS_PATTERNS = [
    r'__import__\s*\(',
    r'import\s+os\s*',
    r'import\s+sys\s*',
    r'import\s+subprocess',
    r'import\s+socket',
    r'from\s+os\s+import',
    r'from\s+sys\s+import',
    r'from\s+subprocess\s+import',
    r'subprocess\.',
    r'os\.system',
    r'os\.popen',
    r'os\.spawn',
    r'os\.exec',
    r'os\.fork',
    r'os\.kill',
    r'sys\.exit',
    r'eval\s*\(',
    r'exec\s*\(',
    r'compile\s*\(',
    r'open\s*\(',
    r'file\s*\(',
    r'\.read\s*\(',
    r'\.write\s*\(',
    r'input\s*\(',
    r'raw_input\s*\(',
    r'__builtins__',
    r'__class__',
    r'__base__',
    r'__subclasses__',
    r'__globals__',
    r'__code__',
    r'__func__',
    r'__closure__',
]


@dataclass
class ExecutionResult:
    """Result of code execution."""
    success: bool
    output: str
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    figures: List[str] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "memory_usage_mb": self.memory_usage_mb,
            "figures": self.figures,
            "variables": {k: str(v) for k, v in self.variables.items()}
        }


class CodeSecurityChecker(ast.NodeVisitor):
    """AST-based security checker for Python code."""
    
    def __init__(self):
        self.violations: List[str] = []
        self.imported_modules: Set[str] = set()
        
    def check_code(self, code: str) -> tuple[bool, List[str]]:
        """Check if code is safe to execute."""
        try:
            tree = ast.parse(code)
            self.visit(tree)
            
            # Check dangerous patterns
            for pattern in DANGEROUS_PATTERNS:
                if re.search(pattern, code, re.IGNORECASE):
                    self.violations.append(f"Dangerous pattern detected: {pattern}")
            
            return len(self.violations) == 0, self.violations
        except SyntaxError as e:
            return False, [f"Syntax error: {str(e)}"]
        except Exception as e:
            return False, [f"Parse error: {str(e)}"]
    
    def visit_Import(self, node):
        for alias in node.names:
            module = alias.name.split('.')[0]
            if module not in ALLOWED_MODULES:
                self.violations.append(f"Import of '{module}' is not allowed")
            self.imported_modules.add(module)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        if node.module:
            module = node.module.split('.')[0]
            if module not in ALLOWED_MODULES:
                self.violations.append(f"Import from '{module}' is not allowed")
            self.imported_modules.add(module)
        self.generic_visit(node)
    
    def visit_Call(self, node):
        # Check for dangerous function calls
        if isinstance(node.func, ast.Name):
            if node.func.id in ['eval', 'exec', 'compile']:
                self.violations.append(f"Use of '{node.func.id}' is not allowed")
            if node.func.id == '__import__':
                self.violations.append("Use of '__import__' is not allowed")
        self.generic_visit(node)
    
    def visit_Attribute(self, node):
        # Check for dangerous attribute access
        if isinstance(node.value, ast.Name):
            if node.value.id == 'os' and node.attr in ['system', 'popen', 'spawn', 'exec', 'fork', 'kill']:
                self.violations.append(f"Use of 'os.{node.attr}' is not allowed")
            if node.value.id == 'subprocess':
                self.violations.append(f"Use of 'subprocess.{node.attr}' is not allowed")
        self.generic_visit(node)


def _execute_code_worker(code: str, timeout: int, max_memory_mb: int) -> ExecutionResult:
    """
    Worker function for executing code in a separate process.
    This runs with resource limits for safety.
    """
    import time
    start_time = time.time()
    
    # Set resource limits
    try:
        # Limit CPU time
        resource.setrlimit(resource.RLIMIT_CPU, (timeout, timeout + 1))
        # Limit memory
        max_memory_bytes = max_memory_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (max_memory_bytes, max_memory_bytes))
        # Limit file size
        resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024))
    except Exception as e:
        logger.warning(f"Could not set resource limits: {e}")
    
    output_buffer = io.StringIO()
    error_buffer = io.StringIO()
    figures = []
    
    # Create restricted globals
    restricted_globals = {
        '__builtins__': {k: v for k, v in builtins.__dict__.items() if k in ALLOWED_BUILTINS},
        '__name__': '__main__',
        '__doc__': None,
    }
    
    # Add allowed modules
    for module_name in ALLOWED_MODULES:
        try:
            module = __import__(module_name, fromlist=[''])
            restricted_globals[module_name] = module
        except ImportError:
            pass
    
    # Add matplotlib configuration for capturing plots
    try:
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        import matplotlib.pyplot as plt
        
        # Override show to capture figures
        original_show = plt.show
        def capture_show(*args, **kwargs):
            import base64
            from io import BytesIO
            buf = BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight')
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            figures.append(f"data:image/png;base64,{img_base64}")
            plt.close()
        plt.show = capture_show
        restricted_globals['plt'] = plt
    except ImportError:
        pass
    
    try:
        # Redirect stdout/stderr
        with contextlib.redirect_stdout(output_buffer), contextlib.redirect_stderr(error_buffer):
            exec(code, restricted_globals)
        
        execution_time = (time.time() - start_time) * 1000
        
        # Extract relevant variables
        variables = {}
        for name, value in restricted_globals.items():
            if not name.startswith('_') and name not in ALLOWED_MODULES and name not in ['plt']:
                try:
                    variables[name] = value
                except:
                    variables[name] = str(value)
        
        return ExecutionResult(
            success=True,
            output=output_buffer.getvalue(),
            error=error_buffer.getvalue() or None,
            execution_time_ms=execution_time,
            figures=figures,
            variables=variables
        )
        
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        return ExecutionResult(
            success=False,
            output=output_buffer.getvalue(),
            error=error_msg,
            execution_time_ms=execution_time,
            figures=figures
        )


class CodeExecutionService:
    """
    Safe code execution service with sandboxing.
    
    Features:
    - AST-based security analysis
    - Process isolation
    - Resource limits (CPU time, memory)
    - Restricted built-ins
    - Module whitelist
    - Timeout enforcement
    """
    
    def __init__(
        self,
        default_timeout: int = 30,
        max_memory_mb: int = 256,
        max_output_size: int = 100000
    ):
        self.default_timeout = default_timeout
        self.max_memory_mb = max_memory_mb
        self.max_output_size = max_output_size
        self.security_checker = CodeSecurityChecker()
        
    async def execute(
        self,
        code: str,
        timeout: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """
        Execute Python code safely in a sandboxed environment.
        
        Args:
            code: Python code to execute
            timeout: Maximum execution time in seconds (default: 30)
            context: Optional context variables to inject
            
        Returns:
            ExecutionResult with output, errors, and metadata
        """
        timeout = timeout or self.default_timeout
        
        # Pre-process code
        code = code.strip()
        if code.startswith('```python'):
            code = code[9:]
        if code.startswith('```'):
            code = code[3:]
        if code.endswith('```'):
            code = code[:-3]
        code = code.strip()
        
        # Security check
        is_safe, violations = self.security_checker.check_code(code)
        if not is_safe:
            logger.warning(f"Code security violations: {violations}")
            return ExecutionResult(
                success=False,
                output="",
                error=f"Security violation: {'; '.join(violations)}",
                execution_time_ms=0
            )
        
        # Add context variables if provided
        if context:
            context_code = "\n".join([f"{k} = {repr(v)}" for k, v in context.items()])
            code = context_code + "\n\n" + code
        
        try:
            # Execute in separate process for isolation
            with ProcessPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    _execute_code_worker,
                    code,
                    timeout,
                    self.max_memory_mb
                )
                
                try:
                    result = future.result(timeout=timeout + 5)  # Add buffer for process startup
                    
                    # Truncate output if too large
                    if len(result.output) > self.max_output_size:
                        result.output = result.output[:self.max_output_size] + "\n... (output truncated)"
                    
                    return result
                    
                except TimeoutError:
                    logger.warning(f"Code execution timed out after {timeout}s")
                    return ExecutionResult(
                        success=False,
                        output="",
                        error=f"Execution timed out after {timeout} seconds",
                        execution_time_ms=timeout * 1000
                    )
                    
        except Exception as e:
            logger.error(f"Code execution error: {e}")
            return ExecutionResult(
                success=False,
                output="",
                error=f"Execution error: {str(e)}",
                execution_time_ms=0
            )
    
    def analyze_code(self, code: str) -> Dict[str, Any]:
        """
        Analyze code without executing it.
        
        Returns analysis including:
        - Security check results
        - Detected imports
        - Estimated complexity
        - Suggestions
        """
        is_safe, violations = self.security_checker.check_code(code)
        
        # Count lines and estimate complexity
        lines = code.split('\n')
        non_empty_lines = [l for l in lines if l.strip()]
        
        # Simple complexity metric
        complexity = 0
        for line in non_empty_lines:
            if any(kw in line for kw in ['for ', 'while ', 'if ', 'elif ', 'else:', 'try:', 'except']):
                complexity += 1
        
        # Detect data science patterns
        patterns = {
            'data_analysis': any(kw in code for kw in ['pandas', 'DataFrame', 'read_csv']),
            'visualization': any(kw in code for kw in ['matplotlib', 'plotly', 'seaborn', 'plt.', 'px.']),
            'statistics': any(kw in code for kw in ['numpy', 'statistics', 'mean', 'std', 'median']),
            'machine_learning': any(kw in code for kw in ['sklearn', 'train_test_split', 'fit', 'predict']),
        }
        
        return {
            "safe": is_safe,
            "violations": violations,
            "line_count": len(non_empty_lines),
            "estimated_complexity": complexity,
            "detected_patterns": {k: v for k, v in patterns.items() if v},
            "suggestions": self._generate_suggestions(code, patterns)
        }
    
    def _generate_suggestions(self, code: str, patterns: Dict[str, bool]) -> List[str]:
        """Generate helpful suggestions based on code analysis."""
        suggestions = []
        
        if patterns.get('data_analysis') and not patterns.get('visualization'):
            suggestions.append("Consider adding visualizations to better understand your data")
        
        if 'pandas' in code and 'head()' not in code:
            suggestions.append("Use df.head() to preview your data")
        
        if 'matplotlib' in code or 'plt' in code:
            if 'plt.show()' not in code:
                suggestions.append("Add plt.show() to display your plots")
        
        if len(code.split('\n')) > 50 and 'def ' not in code:
            suggestions.append("Consider breaking your code into functions for better organization")
        
        return suggestions


# Singleton instance
_code_execution_service: Optional[CodeExecutionService] = None


def get_code_execution_service() -> CodeExecutionService:
    """Get or create code execution service instance."""
    global _code_execution_service
    if _code_execution_service is None:
        _code_execution_service = CodeExecutionService()
    return _code_execution_service
