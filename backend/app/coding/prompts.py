"""
Code Generation Prompts

Few-shot examples and prompt templates for code generation.
"""
from typing import Dict, List, Any


class PromptLibrary:
    """Library of prompts for code generation with few-shot examples."""
    
    # ============ System Prompts ============
    
    FASTAPI_SYSTEM_PROMPT = """You are an expert Python developer specializing in FastAPI.
Generate production-ready FastAPI code following these guidelines:

1. Use type hints throughout
2. Include proper error handling with HTTPException
3. Use Pydantic models for request/response validation
4. Follow RESTful conventions
5. Include docstrings for all endpoints
6. Use dependency injection for database sessions
7. Include pagination for list endpoints
8. Return appropriate HTTP status codes

Security best practices:
- Validate all inputs
- Use parameterized queries (SQLAlchemy handles this)
- Return minimal error details to clients
- Never expose internal implementation details"""

    REACT_SYSTEM_PROMPT = """You are an expert React/TypeScript developer.
Generate production-ready React components following these guidelines:

1. Use TypeScript with proper type definitions
2. Use functional components with hooks
3. Include proper error handling
4. Implement loading states
5. Use proper prop typing
6. Follow React best practices (memo, callback where appropriate)
7. Include accessibility attributes
8. Use consistent styling approach

Security best practices:
- Sanitize any user input before rendering
- Validate API responses
- Handle errors gracefully
- Never store sensitive data in component state"""

    DATABASE_SYSTEM_PROMPT = """You are an expert database designer.
Generate SQLAlchemy models following these guidelines:

1. Use appropriate column types
2. Include indexes for frequently queried fields
3. Define proper relationships
4. Include timestamp columns (created_at, updated_at)
5. Use UUID for primary keys
6. Include __repr__ and to_dict methods
7. Add appropriate constraints

Security best practices:
- Never store passwords in plain text
- Use appropriate field lengths
- Include proper nullable constraints
- Consider data retention requirements"""

    # ============ Few-Shot Examples ============
    
    FASTAPI_EXAMPLES = [
        {
            "request": "Create an API for managing construction projects",
            "function_call": {
                "name": "generate_fastapi_endpoint",
                "arguments": {
                    "endpoint_path": "/api/v1/projects",
                    "model_name": "ConstructionProject",
                    "fields": [
                        {"name": "name", "type": "string", "required": True, "description": "Project name"},
                        {"name": "address", "type": "string", "required": True, "description": "Project address"},
                        {"name": "budget", "type": "float", "required": True, "description": "Project budget"},
                        {"name": "start_date", "type": "string", "required": False, "description": "Project start date"},
                        {"name": "status", "type": "string", "required": True, "description": "Project status"}
                    ],
                    "operations": ["create", "read", "update", "delete", "list"]
                }
            }
        },
        {
            "request": "Add a drywall quantity calculator",
            "function_call": {
                "name": "generate_fastapi_endpoint",
                "arguments": {
                    "endpoint_path": "/api/v1/calculators/drywall",
                    "model_name": "DrywallCalculation",
                    "fields": [
                        {"name": "room_length", "type": "float", "required": True, "description": "Room length in feet"},
                        {"name": "room_width", "type": "float", "required": True, "description": "Room width in feet"},
                        {"name": "ceiling_height", "type": "float", "required": True, "description": "Ceiling height in feet"},
                        {"name": "sheet_size", "type": "string", "required": True, "description": "Drywall sheet size (4x8, 4x10, 4x12)"},
                        {"name": "waste_factor", "type": "float", "required": False, "description": "Waste factor percentage"}
                    ],
                    "operations": ["create", "read", "list"]
                }
            }
        }
    ]
    
    REACT_EXAMPLES = [
        {
            "request": "Create a project list component",
            "function_call": {
                "name": "generate_react_component",
                "arguments": {
                    "component_name": "ProjectList",
                    "props": [
                        {"name": "projects", "type": "Project[]", "required": True},
                        {"name": "onSelect", "type": "(project: Project) => void", "required": False},
                        {"name": "loading", "type": "boolean", "required": False}
                    ],
                    "state_fields": [
                        {"name": "selectedId", "type": "string | null", "initial_value": "null"},
                        {"name": "searchQuery", "type": "string", "initial_value": "''"}
                    ],
                    "api_endpoints": ["/api/v1/projects"],
                    "styling": "tailwind"
                }
            }
        },
        {
            "request": "Create a drywall calculator form",
            "function_call": {
                "name": "generate_react_component",
                "arguments": {
                    "component_name": "DrywallCalculator",
                    "props": [
                        {"name": "onCalculate", "type": "(result: CalculationResult) => void", "required": True},
                        {"name": "initialValues", "type": "Partial<CalculationInput>", "required": False}
                    ],
                    "state_fields": [
                        {"name": "length", "type": "number", "initial_value": "0"},
                        {"name": "width", "type": "number", "initial_value": "0"},
                        {"name": "height", "type": "number", "initial_value": "8"},
                        {"name": "result", "type": "CalculationResult | null", "initial_value": "null"}
                    ],
                    "api_endpoints": ["/api/v1/calculators/drywall"],
                    "styling": "tailwind"
                }
            }
        }
    ]
    
    DATABASE_EXAMPLES = [
        {
            "request": "Create a projects table",
            "function_call": {
                "name": "generate_database_model",
                "arguments": {
                    "table_name": "projects",
                    "model_name": "Project",
                    "columns": [
                        {"name": "id", "type": "string", "primary_key": True},
                        {"name": "name", "type": "string", "nullable": False, "index": True},
                        {"name": "description", "type": "string", "nullable": True},
                        {"name": "budget", "type": "float", "nullable": False},
                        {"name": "status", "type": "string", "nullable": False, "index": True},
                        {"name": "owner_id", "type": "string", "nullable": False, "index": True}
                    ],
                    "relationships": [
                        {"name": "tasks", "target": "Task", "type": "one-to-many"},
                        {"name": "owner", "target": "User", "type": "many-to-one"}
                    ]
                }
            }
        }
    ]
    
    # ============ Prompt Templates ============
    
    CODE_GENERATION_TEMPLATE = """Request: {request}

{context}

Generate the appropriate code for this request. Follow the examples provided and best practices for the target framework.

Requirements:
- Production-ready code
- Proper error handling
- Type safety
- Security considerations
- Documentation/comments"""

    REFINEMENT_TEMPLATE = """Original request: {original_request}

Generated code:
```
{generated_code}
```

Feedback: {feedback}

Please refine the code based on the feedback provided."""

    EXPLANATION_TEMPLATE = """Explain the following code:

```
{code}
```

Provide:
1. High-level purpose
2. Key components/functions
3. Data flow
4. Security considerations
5. Potential improvements"""

    @classmethod
    def get_few_shot_prompt(
        cls,
        request: str,
        generation_type: str,
        context: Dict[str, Any] = None
    ) -> List[Dict[str, str]]:
        """Build a few-shot prompt with examples."""
        messages = []
        
        # Add system prompt
        if generation_type == "fastapi":
            messages.append({"role": "system", "content": cls.FASTAPI_SYSTEM_PROMPT})
            examples = cls.FASTAPI_EXAMPLES
        elif generation_type == "react":
            messages.append({"role": "system", "content": cls.REACT_SYSTEM_PROMPT})
            examples = cls.REACT_EXAMPLES
        elif generation_type == "database":
            messages.append({"role": "system", "content": cls.DATABASE_SYSTEM_PROMPT})
            examples = cls.DATABASE_EXAMPLES
        else:
            examples = []
        
        # Add few-shot examples
        for example in examples:
            messages.append({"role": "user", "content": example["request"]})
            messages.append({
                "role": "assistant", 
                "content": f"Function call: {example['function_call']['name']}\nArguments: {example['function_call']['arguments']}"
            })
        
        # Add actual request
        context_str = f"\nContext: {context}" if context else ""
        messages.append({
            "role": "user", 
            "content": cls.CODE_GENERATION_TEMPLATE.format(
                request=request,
                context=context_str
            )
        })
        
        return messages
    
    @classmethod
    def get_refinement_prompt(
        cls,
        original_request: str,
        generated_code: str,
        feedback: str
    ) -> str:
        """Get prompt for code refinement."""
        return cls.REFINEMENT_TEMPLATE.format(
            original_request=original_request,
            generated_code=generated_code,
            feedback=feedback
        )
    
    @classmethod
    def get_explanation_prompt(cls, code: str) -> str:
        """Get prompt for code explanation."""
        return cls.EXPLANATION_TEMPLATE.format(code=code)


class PromptRegistry:
    """Registry for managing and versioning prompts."""
    
    def __init__(self):
        self._prompts: Dict[str, Dict[str, Any]] = {}
        self._versions: Dict[str, List[int]] = {}
    
    def register(
        self,
        name: str,
        prompt: str,
        metadata: Dict[str, Any] = None
    ) -> int:
        """Register a new prompt version."""
        version = 1
        if name in self._versions:
            version = max(self._versions[name]) + 1
            self._versions[name].append(version)
        else:
            self._versions[name] = [version]
        
        self._prompts[f"{name}:v{version}"] = {
            "prompt": prompt,
            "metadata": metadata or {},
            "version": version,
            "created_at": "now"
        }
        
        return version
    
    def get(self, name: str, version: int = None) -> Dict[str, Any]:
        """Get a prompt by name and version."""
        if version:
            key = f"{name}:v{version}"
        else:
            # Get latest version
            versions = self._versions.get(name, [])
            if not versions:
                return None
            key = f"{name}:v{max(versions)}"
        
        return self._prompts.get(key)
    
    def list_versions(self, name: str) -> List[int]:
        """List all versions of a prompt."""
        return self._versions.get(name, [])
