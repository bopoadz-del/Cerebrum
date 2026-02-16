"""
Code Generation Service Module

AI-powered code generation using OpenAI function calling and Jinja2 templates.
"""
from .generator import CodeGenerator, GenerationResult, code_generator
from .templates import TemplateEngine
from .prompts import PromptLibrary, PromptRegistry
from .endpoints import router

__all__ = [
    # Generator
    "CodeGenerator",
    "GenerationResult",
    "code_generator",
    # Templates
    "TemplateEngine",
    # Prompts
    "PromptLibrary",
    "PromptRegistry",
    # Endpoints
    "router"
]
