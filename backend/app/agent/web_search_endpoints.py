"""
Web Search Endpoints for Agent
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.agent.web_search import get_web_search_tool, WebSearchResponse
from app.core.config import settings

router = APIRouter(prefix="/web-search", tags=["web-search"])


class WebSearchRequest(BaseModel):
    query: str
    count: int = 5
    country: str = "US"
    freshness: Optional[str] = None  # pd, pw, pm, py


class WebSearchResultItem(BaseModel):
    title: str
    url: str
    description: str
    source: str
    published_date: Optional[str] = None


class WebSearchResponseModel(BaseModel):
    query: str
    results: list[WebSearchResultItem]
    total_results: int
    search_time_ms: float
    success: bool
    error: Optional[str] = None


@router.post("/search", response_model=WebSearchResponseModel)
async def web_search(request: WebSearchRequest):
    """
    Perform web search using DuckDuckGo (FREE).
    
    No API key required!
    Only the search query is sent to DuckDuckGo.
    No file contents or conversation data is transmitted.
    
    Cost: $0 (DuckDuckGo) + ~$0.0001 DeepSeek analysis
    vs Brave: $3 per 1,000 searches
    """
    tool = get_web_search_tool()
    
    result = await tool.search(
        query=request.query,
        count=request.count,
        country=request.country,
        freshness=request.freshness
    )
    
    return WebSearchResponseModel(
        query=result.query,
        results=[
            WebSearchResultItem(
                title=r.title,
                url=r.url,
                description=r.description,
                source=r.source,
                published_date=r.published_date
            )
            for r in result.results
        ],
        total_results=result.total_results,
        search_time_ms=result.search_time_ms,
        success=result.success,
        error=result.error
    )


@router.get("/status")
async def web_search_status():
    """Check if web search is enabled and configured."""
    web_search_enabled = getattr(settings, 'WEB_SEARCH_ENABLED', True)
    return {
        "enabled": web_search_enabled,
        "configured": True,  # DuckDuckGo doesn't need API key
        "provider": "DuckDuckGo (FREE)",
        "cost": "$0 - No API key required"
    }
