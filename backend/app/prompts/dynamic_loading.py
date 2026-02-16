"""
Runtime Prompt Loading

Fetches prompts from database at runtime with caching and TTL.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.prompts.models import PromptDB, PromptStatus

logger = logging.getLogger(__name__)


@dataclass
class CachedPrompt:
    """Cached prompt with metadata."""
    prompt: PromptDB
    cached_at: datetime
    ttl_seconds: int
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        elapsed = (datetime.utcnow() - self.cached_at).total_seconds()
        return elapsed > self.ttl_seconds


class PromptLoader:
    """
    Dynamic prompt loader with caching.
    
    Loads prompts from database at runtime with:
    - In-memory caching
    - Configurable TTL
    - Cache invalidation
    - Fallback to default prompts
    """
    
    DEFAULT_TTL_SECONDS = 300  # 5 minutes
    
    def __init__(self, default_ttl_seconds: int = DEFAULT_TTL_SECONDS):
        """
        Initialize the prompt loader.
        
        Args:
            default_ttl_seconds: Default cache TTL
        """
        self.default_ttl_seconds = default_ttl_seconds
        self._cache: Dict[str, CachedPrompt] = {}  # name:version -> cached
        self._id_cache: Dict[UUID, CachedPrompt] = {}  # id -> cached
        self._default_prompts: Dict[str, Dict[str, Any]] = {}
    
    async def get_prompt(
        self,
        name: str,
        version: Optional[str] = None,
        db_session: Optional[AsyncSession] = None,
    ) -> Optional[PromptDB]:
        """
        Get a prompt by name and optional version.
        
        Args:
            name: Prompt name
            version: Specific version (latest active if None)
            db_session: Database session
            
        Returns:
            Prompt or None
        """
        cache_key = f"{name}:{version or 'latest'}"
        
        # Check cache
        cached = self._cache.get(cache_key)
        if cached and not cached.is_expired():
            logger.debug(f"Cache hit for prompt: {cache_key}")
            return cached.prompt
        
        # Load from database
        if db_session:
            prompt = await self._load_from_db(name, version, db_session)
            
            if prompt:
                # Cache the result
                self._cache[cache_key] = CachedPrompt(
                    prompt=prompt,
                    cached_at=datetime.utcnow(),
                    ttl_seconds=self.default_ttl_seconds,
                )
                self._id_cache[prompt.id] = self._cache[cache_key]
                
                return prompt
        
        # Fall back to default
        return self._get_default_prompt(name)
    
    async def get_prompt_by_id(
        self,
        prompt_id: UUID,
        db_session: Optional[AsyncSession] = None,
    ) -> Optional[PromptDB]:
        """
        Get a prompt by ID.
        
        Args:
            prompt_id: Prompt ID
            db_session: Database session
            
        Returns:
            Prompt or None
        """
        # Check cache
        cached = self._id_cache.get(prompt_id)
        if cached and not cached.is_expired():
            return cached.prompt
        
        # Load from database
        if db_session:
            result = await db_session.execute(
                select(PromptDB).where(PromptDB.id == prompt_id)
            )
            prompt = result.scalar_one_or_none()
            
            if prompt:
                # Cache the result
                cache_key = f"{prompt.name}:{prompt.version}"
                self._cache[cache_key] = CachedPrompt(
                    prompt=prompt,
                    cached_at=datetime.utcnow(),
                    ttl_seconds=self.default_ttl_seconds,
                )
                self._id_cache[prompt_id] = self._cache[cache_key]
                
                return prompt
        
        return None
    
    async def get_active_prompt(
        self,
        name: str,
        db_session: Optional[AsyncSession] = None,
    ) -> Optional[PromptDB]:
        """
        Get the active prompt for a name.
        
        Args:
            name: Prompt name
            db_session: Database session
            
        Returns:
            Active prompt or None
        """
        return await self.get_prompt(name, version=None, db_session=db_session)
    
    async def _load_from_db(
        self,
        name: str,
        version: Optional[str],
        db_session: AsyncSession,
    ) -> Optional[PromptDB]:
        """Load prompt from database."""
        if version:
            # Get specific version
            result = await db_session.execute(
                select(PromptDB)
                .where(PromptDB.name == name)
                .where(PromptDB.version == version)
            )
        else:
            # Get latest active version
            result = await db_session.execute(
                select(PromptDB)
                .where(PromptDB.name == name)
                .where(PromptDB.status.in_([PromptStatus.ACTIVE.value, PromptStatus.IN_TEST.value]))
                .order_by(PromptDB.created_at.desc())
                .limit(1)
            )
        
        return result.scalar_one_or_none()
    
    def _get_default_prompt(self, name: str) -> Optional[PromptDB]:
        """Get a default prompt."""
        default = self._default_prompts.get(name)
        if default:
            # Create a temporary PromptDB
            return PromptDB(
                id=UUID(int=0),
                name=name,
                version="default",
                status=PromptStatus.ACTIVE.value,
                system_prompt=default.get("system_prompt", ""),
                model_name=default.get("model", "gpt-4"),
                temperature=default.get("temperature", 0.7),
            )
        return None
    
    def register_default_prompt(
        self,
        name: str,
        system_prompt: str,
        model: str = "gpt-4",
        temperature: float = 0.7,
    ) -> None:
        """
        Register a default prompt for fallback.
        
        Args:
            name: Prompt name
            system_prompt: System prompt content
            model: Model name
            temperature: Temperature
        """
        self._default_prompts[name] = {
            "system_prompt": system_prompt,
            "model": model,
            "temperature": temperature,
        }
        
        logger.info(f"Registered default prompt: {name}")
    
    def invalidate_cache(
        self,
        name: Optional[str] = None,
        version: Optional[str] = None,
    ) -> int:
        """
        Invalidate cached prompts.
        
        Args:
            name: Specific prompt name (all if None)
            version: Specific version (all if None)
            
        Returns:
            Number of entries invalidated
        """
        if name is None:
            # Clear all cache
            count = len(self._cache)
            self._cache.clear()
            self._id_cache.clear()
            logger.info(f"Invalidated all {count} cached prompts")
            return count
        
        if version:
            # Clear specific version
            cache_key = f"{name}:{version}"
            if cache_key in self._cache:
                cached = self._cache[cache_key]
                del self._cache[cache_key]
                if cached.prompt.id in self._id_cache:
                    del self._id_cache[cached.prompt.id]
                logger.info(f"Invalidated prompt: {cache_key}")
                return 1
            return 0
        
        # Clear all versions of a name
        to_remove = [
            key for key in self._cache.keys()
            if key.startswith(f"{name}:")
        ]
        
        for key in to_remove:
            cached = self._cache[key]
            del self._cache[key]
            if cached.prompt.id in self._id_cache:
                del self._id_cache[cached.prompt.id]
        
        logger.info(f"Invalidated {len(to_remove)} versions of prompt: {name}")
        return len(to_remove)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = len(self._cache)
        expired = sum(1 for c in self._cache.values() if c.is_expired())
        
        return {
            "total_cached": total,
            "expired": expired,
            "valid": total - expired,
            "cache_size_bytes": 0,  # Would calculate in production
        }
    
    def cleanup_expired(self) -> int:
        """Remove expired cache entries."""
        to_remove = [
            key for key, cached in self._cache.items()
            if cached.is_expired()
        ]
        
        for key in to_remove:
            cached = self._cache[key]
            del self._cache[key]
            if cached.prompt.id in self._id_cache:
                del self._id_cache[cached.prompt.id]
        
        logger.debug(f"Cleaned up {len(to_remove)} expired cache entries")
        return len(to_remove)


class PromptTemplateEngine:
    """
    Template engine for prompt rendering.
    
    Renders prompt templates with variable substitution.
    """
    
    def __init__(self):
        """Initialize the template engine."""
        self._partials: Dict[str, str] = {}
    
    def render(
        self,
        template: str,
        variables: Dict[str, Any],
    ) -> str:
        """
        Render a template with variables.
        
        Args:
            template: Template string
            variables: Variables to substitute
            
        Returns:
            Rendered string
        """
        result = template
        
        # Simple variable substitution
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value))
        
        return result
    
    def register_partial(self, name: str, content: str) -> None:
        """
        Register a partial template.
        
        Args:
            name: Partial name
            content: Partial content
        """
        self._partials[name] = content
    
    def render_with_partials(self, template: str, variables: Dict[str, Any]) -> str:
        """Render template with partial substitution."""
        result = template
        
        # Substitute partials
        for name, content in self._partials.items():
            placeholder = f"{{{{>{name}}}}}"
            result = result.replace(placeholder, content)
        
        # Substitute variables
        return self.render(result, variables)


# Singleton instances
loader_instance: Optional[PromptLoader] = None
template_engine_instance: Optional[PromptTemplateEngine] = None


def get_prompt_loader(default_ttl_seconds: int = 300) -> PromptLoader:
    """Get or create the singleton prompt loader instance."""
    global loader_instance
    if loader_instance is None:
        loader_instance = PromptLoader(default_ttl_seconds)
    return loader_instance


def get_template_engine() -> PromptTemplateEngine:
    """Get or create the singleton template engine instance."""
    global template_engine_instance
    if template_engine_instance is None:
        template_engine_instance = PromptTemplateEngine()
    return template_engine_instance
