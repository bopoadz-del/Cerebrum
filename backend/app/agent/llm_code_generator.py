"""
LLM-Powered Code Generator for Self-Modification
Phase 4.3: Intelligent code generation using local LLM
"""

import json
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

logger = logging.getLogger(__name__)


class LLMCodeGenerator:
    """
    Generate code using local LLM (Ollama).
    """
    
    OLLAMA_API_URL = "http://localhost:11434/api/generate"
    
    # Prompt templates for different generation tasks
    LAYER_GENERATION_PROMPT = """You are a Python expert developing FastAPI endpoints for a construction management system.

Create a complete FastAPI router file for this layer:

Layer Name: {layer_name}
Description: {description}
Purpose: {purpose}

Required Tools:
{tools}

Requirements:
1. Use FastAPI APIRouter
2. Include proper type hints
3. Add docstrings to all endpoints
4. Include error handling
5. Use async functions
6. Add logging
7. Include input validation using Pydantic models

Generate ONLY the Python code, no explanations.

Code:
"""

    CODE_MODIFICATION_PROMPT = """Modify the following Python code according to the instructions.

Original Code:
```python
{original_code}
```

Modification Instructions:
{instructions}

Requirements:
1. Preserve imports and existing functionality
2. Add only the requested changes
3. Maintain code style
4. Include proper error handling
5. Add comments explaining changes

Generate ONLY the modified Python code, no explanations.

Modified Code:
```python
"""

    TOOL_GENERATION_PROMPT = """Create a Python tool function for a construction management AI agent.

Tool Name: {tool_name}
Description: {description}
Parameters:
{params}

Requirements:
1. Async function
2. Type hints for all parameters and return value
3. Comprehensive docstring
4. Error handling with try/except
5. Return Dict with success status
6. Include logging
7. Follow this template:

async def {tool_name}(...) -> Dict[str, Any]:
    \"\"\"
    Description...
    \"\"\"
    try:
        # Implementation
        return {{"success": True, "result": ...}}
    except Exception as e:
        logger.error(f"... failed: {{e}}")
        return {{"success": False, "error": str(e)}}

Generate ONLY the function code, no explanations.
"""

    REFACTORING_PROMPT = """Refactor the following code to improve quality.

Code to Refactor:
```python
{code}
```

Refactoring Goals:
{goals}

Specific improvements to make:
1. Add type hints where missing
2. Improve error handling
3. Add docstrings
4. Reduce complexity if needed
5. Follow PEP 8 style guidelines
6. Make code more maintainable

Generate ONLY the refactored Python code, no explanations.

Refactored Code:
```python
"""

    def __init__(self, model: str = "gemma3:270m"):
        self.model = model
    
    async def _call_llm(self, prompt: str, temperature: float = 0.2) -> str:
        """Call local LLM via Ollama API."""
        if not AIOHTTP_AVAILABLE:
            raise ImportError("aiohttp required for LLM code generation")
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": temperature,
                    "system": "You are an expert Python developer specializing in FastAPI and async code. Generate clean, well-documented, production-ready code."
                }
                
                async with session.post(self.OLLAMA_API_URL, json=payload) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result.get("response", "")
                    else:
                        logger.error(f"Ollama API error: {resp.status}")
                        return ""
                        
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return ""
    
    def _extract_code(self, response: str) -> str:
        """Extract code from LLM response, handling markdown blocks."""
        # Try to extract from markdown code block
        code_block_pattern = r'```python\s*\n(.*?)\n```'
        match = re.search(code_block_pattern, response, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Try generic code block
        generic_block_pattern = r'```\s*\n(.*?)\n```'
        match = re.search(generic_block_pattern, response, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Return as-is if no code blocks found
        return response.strip()
    
    async def generate_layer(
        self,
        layer_name: str,
        description: str,
        purpose: str,
        tools: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a complete layer file using LLM.
        
        Args:
            layer_name: Name of the layer
            description: Layer description
            purpose: Purpose of the layer
            tools: List of tool specifications
        
        Returns:
            Generated Python code
        """
        tools_str = json.dumps(tools, indent=2)
        
        prompt = self.LAYER_GENERATION_PROMPT.format(
            layer_name=layer_name,
            description=description,
            purpose=purpose,
            tools=tools_str
        )
        
        response = await self._call_llm(prompt, temperature=0.3)
        return self._extract_code(response)
    
    async def modify_code(
        self,
        original_code: str,
        instructions: str
    ) -> str:
        """
        Modify existing code using LLM.
        
        Args:
            original_code: Original code to modify
            instructions: Modification instructions
        
        Returns:
            Modified code
        """
        prompt = self.CODE_MODIFICATION_PROMPT.format(
            original_code=original_code,
            instructions=instructions
        )
        
        response = await self._call_llm(prompt, temperature=0.2)
        return self._extract_code(response)
    
    async def generate_tool(
        self,
        tool_name: str,
        description: str,
        params: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a tool function using LLM.
        
        Args:
            tool_name: Name of the tool
            description: Tool description
            params: List of parameter specifications
        
        Returns:
            Generated function code
        """
        params_str = json.dumps(params, indent=2)
        
        prompt = self.TOOL_GENERATION_PROMPT.format(
            tool_name=tool_name,
            description=description,
            params=params_str
        )
        
        response = await self._call_llm(prompt, temperature=0.2)
        return self._extract_code(response)
    
    async def refactor_code(
        self,
        code: str,
        goals: str
    ) -> str:
        """
        Refactor code using LLM.
        
        Args:
            code: Code to refactor
            goals: Refactoring goals
        
        Returns:
            Refactored code
        """
        prompt = self.REFACTORING_PROMPT.format(
            code=code,
            goals=goals
        )
        
        response = await self._call_llm(prompt, temperature=0.2)
        return self._extract_code(response)
    
    async def generate_test(
        self,
        function_name: str,
        function_code: str,
        test_cases: List[Dict[str, Any]]
    ) -> str:
        """
        Generate pytest test cases for a function.
        
        Args:
            function_name: Name of the function to test
            function_code: Source code of the function
            test_cases: List of test case specifications
        
        Returns:
            Generated test code
        """
        test_cases_str = json.dumps(test_cases, indent=2)
        
        prompt = f"""Generate pytest test cases for this function:

Function Code:
```python
{function_code}
```

Test Cases to Cover:
{test_cases_str}

Requirements:
1. Use pytest
2. Use pytest-asyncio for async functions
3. Include fixtures if needed
4. Test both success and error cases
5. Use descriptive test names
6. Add docstrings to test functions

Generate ONLY the test code, no explanations.

Test Code:
```python
"""
        
        response = await self._call_llm(prompt, temperature=0.2)
        return self._extract_code(response)


class SmartCodeValidator:
    """
    Validate generated code using multiple checks.
    """
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate_syntax(self, code: str) -> bool:
        """Check Python syntax."""
        import ast
        try:
            ast.parse(code)
            return True
        except SyntaxError as e:
            self.errors.append(f"Syntax error: {e}")
            return False
    
    def validate_imports(self, code: str) -> List[str]:
        """Check imports are valid."""
        import ast
        invalid_imports = []
        
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        try:
                            __import__(alias.name)
                        except ImportError:
                            invalid_imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    try:
                        if node.module:
                            __import__(node.module)
                    except ImportError:
                        invalid_imports.append(node.module)
        except:
            pass
        
        return invalid_imports
    
    def check_security(self, code: str) -> Tuple[bool, List[str]]:
        """Check for security issues."""
        dangerous_patterns = [
            (r'os\.system\s*\(', "Dangerous: os.system()"),
            (r'subprocess\.call\s*\([^)]*shell\s*=\s*True', "Dangerous: shell=True"),
            (r'eval\s*\(', "Dangerous: eval()"),
            (r'exec\s*\(', "Dangerous: exec()"),
            (r'__import__\s*\(', "Suspicious: dynamic import"),
            (r'rm\s+-rf', "Dangerous: rm -rf"),
            (r'shutil\.rmtree', "Caution: directory deletion"),
        ]
        
        issues = []
        for pattern, message in dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                issues.append(message)
        
        is_safe = not any("Dangerous" in i for i in issues)
        return is_safe, issues
    
    def validate(self, code: str) -> Dict[str, Any]:
        """Run all validations."""
        self.errors = []
        self.warnings = []
        
        # Syntax check
        syntax_ok = self.validate_syntax(code)
        
        # Security check
        is_safe, security_issues = self.check_security(code)
        if not is_safe:
            self.errors.extend(security_issues)
        else:
            self.warnings.extend(security_issues)
        
        # Import check
        invalid_imports = self.validate_imports(code)
        if invalid_imports:
            self.warnings.append(f"Potentially invalid imports: {', '.join(invalid_imports)}")
        
        return {
            "valid": syntax_ok and is_safe and len(self.errors) == 0,
            "syntax_ok": syntax_ok,
            "is_safe": is_safe,
            "errors": self.errors,
            "warnings": self.warnings,
            "invalid_imports": invalid_imports
        }


class SelfCodingEngine:
    """
    Enhanced self-coding engine with LLM integration.
    """
    
    def __init__(self, model: str = "gemma3:270m"):
        self.generator = LLMCodeGenerator(model)
        self.validator = SmartCodeValidator()
    
    async def create_layer_with_llm(
        self,
        layer_name: str,
        description: str,
        purpose: str,
        tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create a new layer using LLM generation.
        
        Args:
            layer_name: Layer name
            description: Layer description
            purpose: Layer purpose
            tools: Tool specifications
        
        Returns:
            Result with generated code and validation status
        """
        try:
            # Generate code
            code = await self.generator.generate_layer(
                layer_name, description, purpose, tools
            )
            
            if not code:
                return {"success": False, "error": "LLM generated empty code"}
            
            # Validate
            validation = self.validator.validate(code)
            
            return {
                "success": validation["valid"],
                "code": code,
                "validation": validation,
                "layer_name": layer_name,
                "tool_count": len(tools)
            }
            
        except Exception as e:
            logger.error(f"Layer creation failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def modify_code_with_llm(
        self,
        original_code: str,
        instructions: str
    ) -> Dict[str, Any]:
        """
        Modify code using LLM.
        
        Args:
            original_code: Original code
            instructions: Modification instructions
        
        Returns:
            Result with modified code
        """
        try:
            # Generate modification
            modified_code = await self.generator.modify_code(
                original_code, instructions
            )
            
            if not modified_code:
                return {"success": False, "error": "LLM generated empty code"}
            
            # Validate
            validation = self.validator.validate(modified_code)
            
            return {
                "success": validation["valid"],
                "original_code": original_code,
                "modified_code": modified_code,
                "validation": validation
            }
            
        except Exception as e:
            logger.error(f"Code modification failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def refactor_with_llm(
        self,
        code: str,
        goals: str
    ) -> Dict[str, Any]:
        """
        Refactor code using LLM.
        
        Args:
            code: Code to refactor
            goals: Refactoring goals
        
        Returns:
            Result with refactored code
        """
        try:
            refactored = await self.generator.refactor_code(code, goals)
            
            if not refactored:
                return {"success": False, "error": "LLM generated empty code"}
            
            validation = self.validator.validate(refactored)
            
            return {
                "success": validation["valid"],
                "original_code": code,
                "refactored_code": refactored,
                "validation": validation
            }
            
        except Exception as e:
            logger.error(f"Refactoring failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def generate_tool_with_llm(
        self,
        tool_name: str,
        description: str,
        params: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate a tool function using LLM.
        
        Args:
            tool_name: Tool name
            description: Tool description
            params: Parameter specifications
        
        Returns:
            Result with generated function
        """
        try:
            code = await self.generator.generate_tool(
                tool_name, description, params
            )
            
            if not code:
                return {"success": False, "error": "LLM generated empty code"}
            
            validation = self.validator.validate(code)
            
            return {
                "success": validation["valid"],
                "code": code,
                "tool_name": tool_name,
                "validation": validation
            }
            
        except Exception as e:
            logger.error(f"Tool generation failed: {e}")
            return {"success": False, "error": str(e)}


# Convenience functions
async def generate_layer(
    layer_name: str,
    description: str,
    purpose: str,
    tools: List[Dict[str, Any]],
    model: str = "gemma3:270m"
) -> Dict[str, Any]:
    """Generate a layer using LLM."""
    engine = SelfCodingEngine(model)
    return await engine.create_layer_with_llm(layer_name, description, purpose, tools)


async def modify_code(
    original_code: str,
    instructions: str,
    model: str = "gemma3:270m"
) -> Dict[str, Any]:
    """Modify code using LLM."""
    engine = SelfCodingEngine(model)
    return await engine.modify_code_with_llm(original_code, instructions)


async def refactor_code(
    code: str,
    goals: str,
    model: str = "gemma3:270m"
) -> Dict[str, Any]:
    """Refactor code using LLM."""
    engine = SelfCodingEngine(model)
    return await engine.refactor_with_llm(code, goals)
