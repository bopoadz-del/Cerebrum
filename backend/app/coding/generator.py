"""
Code Generation Service

OpenAI function calling for AI-powered code generation.
"""
import json
import os
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from openai import AsyncOpenAI
import logging

logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@dataclass
class GenerationResult:
    """Result of code generation."""
    success: bool
    code: Optional[str]
    language: str
    metadata: Dict[str, Any]
    errors: List[str]
    tokens_used: int


class CodeGenerator:
    """
    AI-powered code generator using OpenAI function calling.
    
    Supports:
    - FastAPI endpoint generation
    - React component generation
    - Database model generation
    - Migration generation
    """
    
    def __init__(self, model: str = "gpt-4-turbo-preview"):
        self.model = model
        self.client = openai_client
        
        # Define function schemas for structured generation
        self.generation_functions = [
            {
                "name": "generate_fastapi_endpoint",
                "description": "Generate a FastAPI endpoint with full CRUD operations",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "endpoint_path": {"type": "string", "description": "API path like /api/v1/items"},
                        "model_name": {"type": "string", "description": "Pydantic model name"},
                        "fields": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "type": {"type": "string"},
                                    "required": {"type": "boolean"},
                                    "description": {"type": "string"}
                                }
                            }
                        },
                        "operations": {
                            "type": "array",
                            "items": {"type": "string", "enum": ["create", "read", "update", "delete", "list"]}
                        }
                    },
                    "required": ["endpoint_path", "model_name", "fields"]
                }
            },
            {
                "name": "generate_react_component",
                "description": "Generate a React component with TypeScript",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "component_name": {"type": "string"},
                        "props": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "type": {"type": "string"},
                                    "required": {"type": "boolean"}
                                }
                            }
                        },
                        "state_fields": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "type": {"type": "string"},
                                    "initial_value": {"type": "string"}
                                }
                            }
                        },
                        "api_endpoints": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "styling": {"type": "string", "enum": ["tailwind", "css-modules", "styled-components", "inline"]}
                    },
                    "required": ["component_name"]
                }
            },
            {
                "name": "generate_database_model",
                "description": "Generate SQLAlchemy database model",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "table_name": {"type": "string"},
                        "model_name": {"type": "string"},
                        "columns": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "type": {"type": "string"},
                                    "primary_key": {"type": "boolean"},
                                    "nullable": {"type": "boolean"},
                                    "default": {"type": "string"},
                                    "index": {"type": "boolean"}
                                }
                            }
                        },
                        "relationships": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "target": {"type": "string"},
                                    "type": {"type": "string", "enum": ["one-to-many", "many-to-one", "many-to-many"]}
                                }
                            }
                        }
                    },
                    "required": ["table_name", "model_name", "columns"]
                }
            },
            {
                "name": "generate_alembic_migration",
                "description": "Generate Alembic database migration",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "revision_name": {"type": "string"},
                        "operations": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "type": {"type": "string", "enum": ["create_table", "drop_table", "add_column", "drop_column", "create_index", "drop_index"]},
                                    "table_name": {"type": "string"},
                                    "columns": {"type": "array"}
                                }
                            }
                        }
                    },
                    "required": ["revision_name", "operations"]
                }
            }
        ]
    
    async def generate_from_request(
        self,
        request: str,
        context: Optional[Dict[str, Any]] = None
    ) -> GenerationResult:
        """
        Generate code from a natural language request.
        
        Example: "Add a drywall quantity calculator"
        """
        try:
            # Build system prompt
            system_prompt = """You are an expert software engineer specializing in full-stack development.
Your task is to generate production-ready code based on user requests.

Guidelines:
- Generate clean, well-documented code
- Follow best practices for the target framework
- Include proper error handling
- Add type hints where appropriate
- Follow security best practices
- Generate complete, runnable code

Available generation types:
- FastAPI endpoints (Python)
- React components (TypeScript)
- Database models (SQLAlchemy)
- Database migrations (Alembic)

Analyze the request and determine the appropriate code to generate."""
            
            # Build user message with context
            user_message = f"Request: {request}\n\n"
            if context:
                user_message += f"Context: {json.dumps(context, indent=2)}\n\n"
            user_message += "Generate the appropriate code for this request."
            
            # Call OpenAI with function calling
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                functions=self.generation_functions,
                function_call="auto",
                temperature=0.2,
                max_tokens=4000
            )
            
            message = response.choices[0].message
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            # Check if function was called
            if message.function_call:
                function_name = message.function_call.name
                function_args = json.loads(message.function_call.arguments)
                
                # Generate code based on function
                return await self._generate_from_function(
                    function_name, function_args, tokens_used
                )
            else:
                # Direct code generation
                return GenerationResult(
                    success=True,
                    code=message.content,
                    language="python",
                    metadata={"type": "direct"},
                    errors=[],
                    tokens_used=tokens_used
                )
        
        except Exception as e:
            logger.error(f"Code generation error: {e}")
            return GenerationResult(
                success=False,
                code=None,
                language="",
                metadata={},
                errors=[str(e)],
                tokens_used=0
            )
    
    async def _generate_from_function(
        self,
        function_name: str,
        args: Dict[str, Any],
        tokens_used: int
    ) -> GenerationResult:
        """Generate code from a function call specification."""
        
        # Map function names to generators
        generators: Dict[str, Callable] = {
            "generate_fastapi_endpoint": self._generate_fastapi_code,
            "generate_react_component": self._generate_react_code,
            "generate_database_model": self._generate_model_code,
            "generate_alembic_migration": self._generate_migration_code
        }
        
        generator = generators.get(function_name)
        if not generator:
            return GenerationResult(
                success=False,
                code=None,
                language="",
                metadata={},
                errors=[f"Unknown generator: {function_name}"],
                tokens_used=tokens_used
            )
        
        code, language, metadata = await generator(args)
        
        return GenerationResult(
            success=code is not None,
            code=code,
            language=language,
            metadata=metadata,
            errors=[] if code else ["Generation failed"],
            tokens_used=tokens_used
        )
    
    async def _generate_fastapi_code(self, args: Dict) -> tuple:
        """Generate FastAPI endpoint code."""
        from .templates import TemplateEngine
        
        template_engine = TemplateEngine()
        code = template_engine.render_fastapi_router(
            endpoint_path=args["endpoint_path"],
            model_name=args["model_name"],
            fields=args.get("fields", []),
            operations=args.get("operations", ["create", "read", "update", "delete", "list"])
        )
        
        return code, "python", {"type": "fastapi_endpoint"}
    
    async def _generate_react_code(self, args: Dict) -> tuple:
        """Generate React component code."""
        from .templates import TemplateEngine
        
        template_engine = TemplateEngine()
        code = template_engine.render_react_component(
            component_name=args["component_name"],
            props=args.get("props", []),
            state_fields=args.get("state_fields", []),
            api_endpoints=args.get("api_endpoints", []),
            styling=args.get("styling", "tailwind")
        )
        
        return code, "typescript", {"type": "react_component"}
    
    async def _generate_model_code(self, args: Dict) -> tuple:
        """Generate SQLAlchemy model code."""
        from .templates import TemplateEngine
        
        template_engine = TemplateEngine()
        code = template_engine.render_sqlalchemy_model(
            table_name=args["table_name"],
            model_name=args["model_name"],
            columns=args["columns"],
            relationships=args.get("relationships", [])
        )
        
        return code, "python", {"type": "database_model"}
    
    async def _generate_migration_code(self, args: Dict) -> tuple:
        """Generate Alembic migration code."""
        from .templates import TemplateEngine
        
        template_engine = TemplateEngine()
        code = template_engine.render_alembic_migration(
            revision_name=args["revision_name"],
            operations=args["operations"]
        )
        
        return code, "python", {"type": "alembic_migration"}
    
    async def generate_custom(
        self,
        prompt: str,
        language: str = "python",
        max_tokens: int = 4000
    ) -> GenerationResult:
        """Generate custom code from a detailed prompt."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"You are an expert {language} developer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=max_tokens
            )
            
            code = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            # Strip markdown code blocks if present
            if code.startswith("```"):
                lines = code.split("\n")
                code = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
            
            return GenerationResult(
                success=True,
                code=code,
                language=language,
                metadata={"type": "custom"},
                errors=[],
                tokens_used=tokens_used
            )
        
        except Exception as e:
            logger.error(f"Custom generation error: {e}")
            return GenerationResult(
                success=False,
                code=None,
                language=language,
                metadata={},
                errors=[str(e)],
                tokens_used=0
            )


# Singleton instance
code_generator = CodeGenerator()
