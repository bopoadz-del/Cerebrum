"""
Redis State API Endpoints

API for task progress, caching, and state management.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_user, User
from app.services.redis_state_store import get_redis_store

router = APIRouter(prefix="/state", tags=["State Store"])


@router.get("/task/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get Celery task progress/status from Redis.
    
    Returns real-time progress for background tasks like:
    - File hydration
    - Bulk reindexing
    - BIM analysis
    """
    store = await get_redis_store()
    progress = await store.get_task_progress(task_id)
    
    if progress is None:
        raise HTTPException(status_code=404, detail="Task not found or expired")
    
    return progress


@router.get("/cache/search")
async def get_cached_search_status(
    query: str = Query(..., description="Search query"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Check if search results are cached.
    
    Returns cached results if available, otherwise indicates cache miss.
    """
    store = await get_redis_store()
    cached = await store.get_cached_search(query, str(current_user.id))
    
    if cached:
        return {
            "cached": True,
            "query": cached["query"],
            "count": cached["count"],
            "cached_at": cached["cached_at"],
            "results": cached["results"]
        }
    
    return {"cached": False, "query": query}


@router.delete("/cache/search")
async def invalidate_search_cache(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Invalidate all search cache for current user.
    
    Call this after uploading new documents to ensure fresh search results.
    """
    store = await get_redis_store()
    success = await store.invalidate_search_cache(str(current_user.id))
    
    return {
        "success": success,
        "message": "Search cache invalidated"
    }


@router.get("/rate-limit/{action}")
async def check_rate_limit(
    action: str,  # e.g., "upload", "search", "api"
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Check current rate limit status.
    
    Actions:
    - upload: File uploads (10/minute)
    - search: Document searches (60/minute)
    - api: General API calls (100/minute)
    """
    store = await get_redis_store()
    
    # Define limits
    limits = {
        "upload": (10, 60),      # 10 per minute
        "search": (60, 60),      # 60 per minute
        "api": (100, 60),        # 100 per minute
    }
    
    max_requests, window = limits.get(action, (100, 60))
    key = f"rate_limit:{action}:{current_user.id}"
    
    result = await store.check_rate_limit(key, max_requests, window)
    
    return {
        "action": action,
        "allowed": result["allowed"],
        "remaining": result["remaining"],
        "limit": max_requests,
        "window_seconds": window,
        "reset_at": result["reset_at"]
    }


@router.get("/session/{session_id}")
async def get_session_data(
    session_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get session data from Redis."""
    store = await get_redis_store()
    data = await store.get_session_data(session_id)
    
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    return {"session_id": session_id, "data": data}


@router.post("/session/{session_id}")
async def set_session_data(
    session_id: str,
    data: Dict[str, Any],
    ttl_seconds: int = 3600,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Store session data in Redis."""
    store = await get_redis_store()
    success = await store.set_session_data(session_id, data, ttl_seconds)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to store session data")
    
    return {
        "success": True,
        "session_id": session_id,
        "ttl_seconds": ttl_seconds
    }


@router.get("/feature/{flag_name}")
async def check_feature_flag(
    flag_name: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Check if a feature flag is enabled.
    
    Feature flags allow enabling/disabling features without deploys.
    """
    store = await get_redis_store()
    enabled = await store.get_feature_flag(flag_name, default=False)
    
    return {
        "flag": flag_name,
        "enabled": enabled
    }


@router.get("/health")
async def redis_health() -> Dict[str, Any]:
    """Redis state store health check."""
    store = await get_redis_store()
    stats = await store.get_stats()
    
    return {
        "service": "redis_state_store",
        **stats
    }
